from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

class Workspace(models.Model):
    """Рабочее пространство / отдел (HR, QA, DevOps и т.д.)."""
    workspace_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True, verbose_name='Название отдела')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Дата создания')

    class Meta:
        db_table = 'workspaces'
        ordering = ['workspace_id']
        verbose_name = 'Рабочее пространство'
        verbose_name_plural = 'Рабочие пространства'

    def __str__(self):
        return self.name

class UserManager(BaseUserManager):
    """Менеджер для создания пользователей и суперпользователей."""

    def create_user(self, username, password, full_name, role, workspace=None, **extra_fields):
        if not username:
            raise ValueError('Логин обязателен')
        user = self.model(
            username=username,
            full_name=full_name,
            role=role,
            workspace=workspace,
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password, full_name='Admin', **extra_fields):
        extra_fields.setdefault('role', 'admin')
        return self.create_user(username, password, full_name, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Пользователь системы NaviTime Kanban.

    Хранит роль и привязку к рабочему пространству.
    is_active=0 означает блокировку (сценарий 12).
    """

    ROLE_CHOICES = [
        ('employee', 'Сотрудник'),
        ('manager', 'Начальник'),
        ('admin', 'Технический администратор'),
    ]

    user_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=50, unique=True, verbose_name='Логин')
    # Поле password наследуется от AbstractBaseUser (хэширование встроено)
    full_name = models.CharField(max_length=150, verbose_name='Полное имя')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name='Роль')
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name='Рабочее пространство',
    )
    last_active = models.DateTimeField(null=True, blank=True, verbose_name='Последняя активность')
    is_active = models.BooleanField(default=True, verbose_name='Учётная запись активна')
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['full_name', 'role']

    class Meta:
        db_table = 'users'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f'{self.full_name} ({self.role})'

class Status(models.Model):
    """Статус-колонка Kanban-доски (In Order, To Do, Done и т.д.)."""
    status_id = models.AutoField(primary_key=True)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='statuses',
        verbose_name='Рабочее пространство',
    )
    name = models.CharField(max_length=50, verbose_name='Название статуса')
    position = models.IntegerField(verbose_name='Порядковый номер колонки')
    color = models.CharField(max_length=7, null=True, blank=True, verbose_name='Цвет (#RRGGBB)')

    class Meta:
        db_table = 'statuses'
        ordering = ['position']
        verbose_name = 'Статус'
        verbose_name_plural = 'Статусы'

    def __str__(self):
        return f'{self.name} (ws={self.workspace_id})'

class Task(models.Model):
    """Задача на Kanban-доске. Поддерживает мягкое удаление через is_deleted."""

    PRIORITY_CHOICES = [
        (1, 'Низкий'),
        (2, 'Средний'),
        (3, 'Высокий'),
        (4, 'Критический'),
    ]

    task_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255, verbose_name='Заголовок')
    description = models.TextField(null=True, blank=True, verbose_name='Описание / цель')
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name='Рабочее пространство',
    )
    status = models.ForeignKey(
        Status,
        on_delete=models.RESTRICT,
        related_name='tasks',
        verbose_name='Статус',
    )
    assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        verbose_name='Исполнитель',
    )
    creator = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name='created_tasks',
        verbose_name='Создатель',
    )
    priority = models.SmallIntegerField(
        choices=PRIORITY_CHOICES,
        default=2,
        verbose_name='Приоритет',
    )
    deadline = models.DateTimeField(null=True, blank=True, verbose_name='Дедлайн')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата изменения')
    is_deleted = models.BooleanField(default=False, verbose_name='Удалена (мягко)')

    class Meta:
        ordering = ['workspace_id']
        db_table = 'tasks'
        verbose_name = 'Задача'
        verbose_name_plural = 'Задачи'

    def __str__(self):
        return self.title

class Comment(models.Model):
    """Комментарий к задаче. При удалении задачи удаляется каскадно."""
    comment_id = models.AutoField(primary_key=True)
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Задача',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name='comments',
        verbose_name='Автор',
    )
    body = models.TextField(verbose_name='Текст комментария')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='Дата создания')

    class Meta:
        db_table = 'comments'
        ordering = ['created_at']
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'

    def __str__(self):
        return f'Comment #{self.comment_id} on task #{self.task_id}'
