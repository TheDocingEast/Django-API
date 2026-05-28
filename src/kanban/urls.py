from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import WorkspaceViewSet, UserViewSet, StatusViewSet, TaskViewSet, CommentViewSet


router = DefaultRouter()
router.register(r'workspaces', WorkspaceViewSet, basename='workspace')
router.register(r'users', UserViewSet, basename='user')
router.register(r'statuses', StatusViewSet, basename='status')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'comments', CommentViewSet, basename='comment')

urlpatterns = [
    path('', include(router.urls)),
]
