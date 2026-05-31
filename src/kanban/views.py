from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_extensions.cache.decorators import cache_response

from .models import Workspace, User, Status, Task, Comment
from .serializers import (
    WorkspaceSerializer, UserSerializer,
    StatusSerializer, TaskSerializer, CommentSerializer,
)
from .permissions import IsAdmin, IsManagerOrAdmin, IsAuthenticatedReadOrManagerWrite


# ── WorkspaceViewSet ─────────────────────────────────────────────────────────
class WorkspaceViewSet(viewsets.ModelViewSet):
    """Управление рабочими пространствами (отделами).

    Сценарии 7 и 11:
    - GET /workspaces/ — список всех отделов (для Начальника: переключение контекста).
    - POST/DELETE /workspaces/ — только для Технического администратора.
    """

    serializer_class = WorkspaceSerializer
    queryset = Workspace.objects.all()

    def get_permissions(self):
        """Чтение — все авторизованные. Запись — только admin."""
        if self.action in ('list', 'retrieve'):
            return [permissions.IsAuthenticated()]
        return [IsAdmin()]

    @cache_response(60 * 15)
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


# ── UserViewSet ──────────────────────────────────────────────────────────────
class UserViewSet(viewsets.ModelViewSet):
    """Управление учётными записями пользователей.

    Сценарий 12:
    - GET — список пользователей (только admin).
    - POST — создание нового пользователя (пароль хэшируется автоматически).
    - PATCH /users/{id}/block/ — блокировка: is_active → False.
    Фильтрация по workspace_id и role через GET-параметры.
    """

    serializer_class = UserSerializer
    queryset = User.objects.select_related('workspace').all()
    permission_classes = [IsAdmin]

    def get_queryset(self):
        """Фильтрация пользователей по workspace_id и role."""
        qs = super().get_queryset()
        workspace_id = self.request.query_params.get('workspace_id')
        role = self.request.query_params.get('role')
        if workspace_id:
            qs = qs.filter(workspace_id=workspace_id)
        if role:
            qs = qs.filter(role=role)
        return qs

    @action(detail=True, methods=['patch'], url_path='block')
    def block(self, request, pk=None):
        """PATCH /api/v1/users/{id}/block/ — блокировка учётной записи (сценарий 12)."""
        user = self.get_object()
        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response({'detail': f'Пользователь {user.username} заблокирован.'})

    @action(detail=True, methods=['patch'], url_path='activate')
    def activate(self, request, pk=None):
        """PATCH /api/v1/users/{id}/activate/ — снятие блокировки."""
        user = self.get_object()
        user.is_active = True
        user.save(update_fields=['is_active'])
        return Response({'detail': f'Пользователь {user.username} активирован.'})


# ── StatusViewSet ────────────────────────────────────────────────────────────
class StatusViewSet(viewsets.ModelViewSet):
    """Управление статусами (колонками Kanban-доски).

    Сценарии 2 и 10:
    - GET /statuses/?workspace_id=1 — список колонок для доски (сценарий 2).
    - POST / PUT / PATCH / DELETE — кастомизация статусов (сценарий 10, только managers+).
    """

    serializer_class = StatusSerializer
    queryset = Status.objects.select_related('workspace').all()

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [permissions.IsAuthenticated()]
        return [IsManagerOrAdmin()]

    def get_queryset(self):
        """Фильтрация по workspace_id: каждый отдел видит только свои колонки."""
        qs = super().get_queryset()
        workspace_id = self.request.query_params.get('workspace_id')
        if workspace_id:
            qs = qs.filter(workspace_id=workspace_id)
        elif self.request.user.role == 'employee':
            # Сотрудник видит только колонки своего отдела
            qs = qs.filter(workspace_id=self.request.user.workspace_id)
        return qs

    @cache_response(60 * 15)
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)



class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    # Убираем фильтр отсюда — он должен быть только в get_queryset
    queryset = Task.objects.select_related(
        'workspace', 'status', 'assignee', 'creator'
    ).all()
    permission_classes = [IsAuthenticatedReadOrManagerWrite]

    def get_queryset(self):
        # Все запросы, включая retrieve/update/destroy, идут через этот метод
        qs = Task.objects.select_related(
            'workspace', 'status', 'assignee', 'creator'
        ).filter(is_deleted=False)

        user = self.request.user
        workspace_id = self.request.query_params.get('workspace_id')
        status_id    = self.request.query_params.get('status_id')
        assignee_id  = self.request.query_params.get('assignee_id')
        priority     = self.request.query_params.get('priority')
        creator_id   = self.request.query_params.get('creator_id')

        if self.action in ('retrieve', 'update', 'partial_update', 'destroy'):
            pass  # не фильтруем по workspace, объект ищется по pk
        elif workspace_id and user.role in ('manager', 'admin'):
            qs = qs.filter(workspace_id=workspace_id)
        else:
            qs = qs.filter(workspace_id=user.workspace_id)

        if status_id:
            qs = qs.filter(status_id=status_id)
        if assignee_id:
            qs = qs.filter(assignee_id=assignee_id)
        if priority:
            qs = qs.filter(priority=priority)
        if creator_id:
            qs = qs.filter(creator_id=creator_id)

        return qs

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

# ── CommentViewSet ───────────────────────────────────────────────────────────
class CommentViewSet(viewsets.ModelViewSet):
    """Управление комментариями к задачам.

    Сценарий 5: создание комментария.
    - POST — создаёт комментарий; author = текущий пользователь (из токена).
    - Пустой body блокируется сериализатором (NOT NULL).
    - Фильтрация по task_id.
    """

    serializer_class = CommentSerializer
    queryset = Comment.objects.select_related('task', 'author').all()
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Фильтрация комментариев по задаче."""
        qs = super().get_queryset()
        task_id = self.request.query_params.get('task_id')
        if task_id:
            qs = qs.filter(task_id=task_id)
        return qs

    def perform_create(self, serializer):
        """Сценарий 5: author = текущий пользователь из JWT-токена."""
        serializer.save(author=self.request.user)

    def create(self, request, *args, **kwargs):
        """POST — создание комментария. Пустой body не пройдёт валидацию."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """PUT — редактирование комментария (только автор)."""
        instance = self.get_object()
        if instance.author != request.user and request.user.role != 'admin':
            return Response(
                {'detail': 'Редактировать можно только свои комментарии.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """DELETE — удаление комментария (автор или admin)."""
        instance = self.get_object()
        if instance.author != request.user and request.user.role != 'admin':
            return Response(
                {'detail': 'Удалять можно только свои комментарии.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)
