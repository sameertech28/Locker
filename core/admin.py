from django.contrib import admin

from .models import ActivityLog, Group, GroupMembership, Notification, Profile, Tag, VaultFile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "storage_used", "storage_limit", "theme_preference")
    search_fields = ("user__username", "user__email")


@admin.register(VaultFile)
class VaultFileAdmin(admin.ModelAdmin):
    list_display = ("file_name", "uploaded_by", "group", "file_type", "file_size", "is_deleted", "uploaded_at")
    list_filter = ("file_type", "is_deleted", "group")
    search_fields = ("file_name", "description")


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "created_by", "member_count", "is_private", "group_code", "created_at")
    search_fields = ("name",)


@admin.register(GroupMembership)
class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ("group", "user", "is_admin", "joined_at")


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "file", "group", "timestamp")
    list_filter = ("action",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "is_read", "created_at")


admin.site.register(Tag)
