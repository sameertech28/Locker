from django.urls import path
from django.views.decorators.cache import never_cache

from . import views

urlpatterns = [
    path("", views.landing, name="landing"),
    path("dashboard/", views.dashboard, name="dashboard"),

    # auth
    path("register/", views.register_view, name="register"),
    path("login/", views.LockerLoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),

    # files
    path("files/", views.file_explorer, name="file_explorer"),
    path("files/<int:pk>/download/", views.file_download, name="file_download"),
    path("files/<int:pk>/delete/", views.file_delete, name="file_delete"),
    path("files/<int:pk>/restore/", views.file_restore, name="file_restore"),
    path("files/<int:pk>/permanent-delete/", views.file_permanent_delete, name="file_permanent_delete"),
    path("files/<int:pk>/favorite/", views.toggle_favorite, name="toggle_favorite"),
    path("trash/", views.trash, name="trash"),

    # groups
    path("groups/", views.group_list, name="group_list"),
    path("groups/create/", views.group_create, name="group_create"),
    path("groups/join/", views.group_join_form, name="group_join_form"),
    path("groups/join/<str:code>/", views.group_join, name="group_join"),
    path("groups/<slug:slug>/", views.group_detail, name="group_detail"),
    path("groups/<slug:slug>/leave/", views.group_leave, name="group_leave"),
    path("groups/<slug:slug>/members/add/", views.group_add_member, name="group_add_member"),
    path("groups/<slug:slug>/members/<int:user_id>/remove/", views.group_remove_member, name="group_remove_member"),

    # notifications (API endpoints are rate-limited)
    path("notifications/", views.notification_list, name="notifications"),
    path("notifications/<int:pk>/read/", views.notification_read, name="notification_read"),
    path("notifications/read-all/", views.notification_read_all, name="notification_read_all"),
    path("notifications/poll/", views.notification_poll, name="notification_poll"),

    # profile
    path("profile/", views.profile_view, name="profile"),

    # health / keepalive
    path("health/", views.health_check, name="health_check"),
]

