from rest_framework import serializers
from .models import Workspace, User, Status, Task, Comment


class WorkspaceSerializer(serializers.ModelSerializer):
    """Сериализатор рабочего пространства.

    Сценарии 7, 11: отображение и управление отделами.
    """

    class Meta:
        model = Workspace
        fields = ['workspace_id', 'name', 'created_at']
        read_only_fields = ['workspace_id', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя.

    Сценарии 1, 12: авторизация, просмотр и управление учётными записями.
    Поле password — только запись (write_only), в ответах не отдаётся.
    """

    workspace = WorkspaceSerializer(read_only=True)
    workspace_id = serializers.PrimaryKeyRelatedField(
        queryset=Workspace.objects.all(), source='workspace', write_only=True,
        required=False, allow_null=True,
    )
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'user_id', 'username', 'password', 'full_name', 'role',
            'workspace', 'workspace_id', 'last_active', 'is_active',
        ]
        read_only_fields = ['user_id', 'last_active']

    def create(self, validated_data):
        """Создание пользователя с хэшированием пароля (сценарий 12)."""
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        """Обновление: пароль хэшируется только если передан явно."""
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        return super().update(instance, validated_data)


class StatusSerializer(serializers.ModelSerializer):
    """Сериализатор статуса-колонки.

    Сценарии 2, 10: отображение колонок доски, кастомизация статусов.
    """

    workspace = WorkspaceSerializer(read_only=True)
    workspace_id = serializers.PrimaryKeyRelatedField(
        queryset=Workspace.objects.all(), source='workspace', write_only=True,
    )

    class Meta:
        model = Status
        fields = ['status_id', 'workspace', 'workspace_id', 'name', 'position', 'color']
        read_only_fields = ['status_id']


class TaskSerializer(serializers.ModelSerializer):
    """Сериализатор задачи.

    Сценарии 2, 3, 4, 6, 8, 9.
    При чтении отдаёт вложенные объекты исполнителя и статуса.
    При записи принимает id через поля assignee_id, status_id, workspace_id.
    is_deleted скрыт от клиента при чтении — задачи с флагом фильтруются во ViewSet.
    """

    assignee = UserSerializer(read_only=True)
    assignee_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        source='assignee', write_only=True, required=False, allow_null=True,
    )
    creator = UserSerializer(read_only=True)
    status = StatusSerializer(read_only=True)
    status_id = serializers.PrimaryKeyRelatedField(
        queryset=Status.objects.all(), source='status', write_only=True,
    )
    workspace = WorkspaceSerializer(read_only=True)
    workspace_id = serializers.PrimaryKeyRelatedField(
        queryset=Workspace.objects.all(), source='workspace', write_only=True,
    )

    class Meta:
        model = Task
        fields = [
            'task_id', 'title', 'description',
            'workspace', 'workspace_id',
            'status', 'status_id',
            'assignee', 'assignee_id',
            'creator',
            'priority', 'deadline', 'created_at', 'updated_at',
        ]
        read_only_fields = ['task_id', 'creator', 'created_at', 'updated_at']

class CommentSerializer(serializers.ModelSerializer):
    """Сериализатор комментария.

    Сценарий 5: добавление комментария к задаче.
    author подставляется автоматически из токена во ViewSet.perform_create.
    """

    author = UserSerializer(read_only=True)
    task_id = serializers.PrimaryKeyRelatedField(
        queryset=Task.objects.filter(is_deleted=False), source='task', write_only=True,
    )
    task = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Comment
        fields = ['comment_id', 'task', 'task_id', 'author', 'body', 'created_at']
        read_only_fields = ['comment_id', 'author', 'created_at']
