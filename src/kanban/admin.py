from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Workspace, User, Status, Task, Comment


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    """Управление рабочими пространствами (отделами)."""
    list_display = ['workspace_id', 'name', 'created_at']
    search_fields = ['name']


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Управление учётными записями пользователей."""
    list_display = ['user_id', 'username', 'full_name', 'role', 'workspace', 'is_active']
    list_filter = ['role', 'is_active', 'workspace']
    search_fields = ['username', 'full_name']
    ordering = ['username']
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Персональные данные', {'fields': ('full_name', 'role', 'workspace')}),
        ('Доступ', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Активность', {'fields': ('last_active',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'full_name', 'role', 'workspace'),
        }),
    )


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    """Управление статусами-колонками Kanban-доски."""
    list_display = ['status_id', 'name', 'workspace', 'position', 'color']
    list_filter = ['workspace']
    ordering = ['workspace', 'position']


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Управление задачами. is_deleted=True — мягко удалённые."""
    list_display = ['task_id', 'title', 'workspace', 'status', 'assignee', 'priority', 'deadline', 'is_deleted']
    list_filter = ['workspace', 'status', 'priority', 'is_deleted']
    search_fields = ['title', 'description']
    date_hierarchy = 'created_at'

    def deadline_preview(self, obj):
        """Подсвечивает дедлайн для горящих задач (сценарий 2)."""
        from django.utils import timezone
        if obj.deadline and obj.deadline < timezone.now():
            return f'⚠️ {obj.deadline}'
        return obj.deadline
    deadline_preview.short_description = 'Дедлайн'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """Управление комментариями."""
    list_display = ['comment_id', 'task', 'author', 'body_preview', 'created_at']
    search_fields = ['body']

    def body_preview(self, obj):
        """Обрезает текст до 60 символов."""
        return obj.body[:60] + ('...' if len(obj.body) > 60 else '')
    body_preview.short_description = 'Текст'
