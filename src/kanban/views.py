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


# ── TaskViewSet ──────────────────────────────────────────────────────────────
class TaskViewSet(viewsets.ModelViewSet):
    """Управление задачами Kanban-доски.

    Сценарии 2, 3, 4, 6, 8, 9:
    - GET /tasks/ — задачи текущего рабочего пространства (is_deleted=0).
    - GET /tasks/?workspace_id=X — мониторинг другого пространства (manager).
    - POST — создание задачи (creator_id = текущий пользователь).
    - PATCH — изменение статуса (Drag-and-Drop, сценарий 4).
    - DELETE — мягкое удаление is_deleted=1 (сценарий 9).
    - PATCH /tasks/{id}/mark_irrelevant/ — пометить как неактуальную (сценарий 6).
    Фильтрация: workspace_id, status_id, assignee_id, priority.
    """

    serializer_class = TaskSerializer
    queryset = Task.objects.select_related(
        'workspace', 'status', 'assignee', 'creator'
    ).filter(is_deleted=False)
    permission_classes = [IsAuthenticatedReadOrManagerWrite]

    def get_queryset(self):
        """Фильтрация задач. Сотрудник видит только свой отдел."""
        qs = super().get_queryset()
        user = self.request.user

        workspace_id = self.request.query_params.get('workspace_id')
        status_id = self.request.query_params.get('status_id')
        assignee_id = self.request.query_params.get('assignee_id')
        priority = self.request.query_params.get('priority')

        if workspace_id and user.role in ('manager', 'admin'):
            # Сценарий 7: Начальник переключает пространства
            qs = qs.filter(workspace_id=workspace_id)
        else:
            # Сценарий 2: Сотрудник видит только свой отдел
            qs = qs.filter(workspace_id=user.workspace_id)

        if status_id:
            qs = qs.filter(status_id=status_id)
        if assignee_id:
            qs = qs.filter(assignee_id=assignee_id)
        if priority:
            qs = qs.filter(priority=priority)

        return qs

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @cache_response(60 * 5)
    def retrieve(self, request, *args, **kwargs):
        """Сценарий 3: детальный просмотр карточки задачи (кешируем на 5 минут)."""
        return super().retrieve(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Сценарий 8: при создании задачи creator = текущий пользователь."""
        serializer.save(creator=self.request.user)

    def create(self, request, *args, **kwargs):
        """POST — создание одной или нескольких задач (сценарий 8)."""
        many = isinstance(request.data, list)
        serializer = self.get_serializer(data=request.data, many=many)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        """PUT — полное обновление задачи (включая смену статуса, сценарий 4)."""
        many = isinstance(request.data, list)
        if many:
            instances = [Task.objects.get(pk=item['task_id']) for item in request.data]
            serializer = self.get_serializer(instances, data=request.data, many=True)
        else:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """PATCH — частичное обновление (Drag-and-Drop: меняем только status_id, сценарий 4)."""
        many = isinstance(request.data, list)
        if many:
            instances = [Task.objects.get(pk=item['task_id']) for item in request.data]
            serializer = self.get_serializer(instances, data=request.data, partial=True, many=True)
        else:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """DELETE — мягкое удаление: is_deleted=1. Физически запись остаётся в БД (сценарий 9)."""
        ids = request.query_params.get('ids')
        if ids:
            # Массовое мягкое удаление через ?ids=1,2,3
            ids_list = [int(pk) for pk in ids.split(',')]
            Task.objects.filter(pk__in=ids_list).update(is_deleted=True)
            return Response(status=status.HTTP_204_NO_CONTENT)
        # Одиночное мягкое удаление
        instance = self.get_object()
        instance.is_deleted = True
        instance.save(update_fields=['is_deleted'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['patch'], url_path='mark_irrelevant')
    def mark_irrelevant(self, request, pk=None):
        """PATCH /api/v1/tasks/{id}/mark_irrelevant/ — пометить задачу как неактуальную.

        Сценарий 6: задача не удаляется физически, статус меняется на «неактуально».
        Начальник должен получить уведомление (здесь — заготовка, логику уведомлений
        расширить при необходимости).
        """
        task = self.get_object()
        # Ищем статус «неактуально» / «Irrelevant» в пространстве задачи
        irrelevant_status = Status.objects.filter(
            workspace_id=task.workspace_id,
            name__icontains='неактуал',
        ).first()

        if not irrelevant_status:
            return Response(
                {'detail': 'Статус «Неактуально» не найден в данном рабочем пространстве.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        task.status = irrelevant_status
        task.save(update_fields=['status', 'updated_at'])
        return Response(
            {'detail': 'Задача помечена как неактуальная.', 'task_id': task.pk}
        )


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
