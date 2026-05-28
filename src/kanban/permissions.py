from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """Только технические администраторы (role='admin').

    Сценарии 11, 12: управление рабочими пространствами и пользователями.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == 'admin'
        )


class IsManagerOrAdmin(permissions.BasePermission):
    """Начальники и администраторы.

    Сценарии 7, 8, 9, 10: мониторинг пространств, создание/удаление задач,
    кастомизация статусов.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ('manager', 'admin')
        )


class IsAuthenticatedReadOrManagerWrite(permissions.BasePermission):
    """Чтение — всем авторизованным. Запись — только начальникам и выше.

    Сценарии 2, 3 (просмотр задач — все), 8, 9, 4 (изменение — managers+).
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.role in ('manager', 'admin')


class IsOwnerWorkspace(permissions.BasePermission):
    """Пользователь видит только данные своего рабочего пространства.

    Применяется на уровне объекта (has_object_permission).
    Начальник и администратор видят все пространства.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.role in ('manager', 'admin'):
            return True
        # Для задач и статусов: проверяем workspace
        workspace_id = getattr(obj, 'workspace_id', None)
        return workspace_id == request.user.workspace_id
