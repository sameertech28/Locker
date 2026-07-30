import hashlib
import os
import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


def user_avatar_path(instance, filename):
    ext = filename.split(".")[-1]
    return f"avatars/{instance.user.id}_{uuid.uuid4().hex[:8]}.{ext}"


def vault_file_path(instance, filename):
    return f"uploads/{instance.uploaded_by_id}/{uuid.uuid4().hex}_{filename}"


def group_cover_path(instance, filename):
    ext = filename.split(".")[-1]
    return f"group_covers/{instance.slug}.{ext}"


class Profile(models.Model):
    """Extends Django's built-in User with vault-specific fields."""

    THEME_CHOICES = [("dark", "Dark"), ("light", "Light"), ("neon", "Neon")]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    avatar = models.ImageField(upload_to=user_avatar_path, blank=True, null=True)
    storage_used = models.BigIntegerField(default=0)
    storage_limit = models.BigIntegerField(default=10 * 1024 * 1024 * 1024)  # 10GB
    theme_preference = models.CharField(max_length=10, choices=THEME_CHOICES, default="neon")
    last_activity = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile<{self.user.username}>"

    @property
    def storage_percent(self):
        if not self.storage_limit:
            return 0
        return min(100, round((self.storage_used / self.storage_limit) * 100, 1))


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=7, default="#00f0ff")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tags")

    def __str__(self):
        return self.name


class Group(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to=group_cover_path, blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_groups")
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through="GroupMembership", related_name="vault_groups")
    is_private = models.BooleanField(default=True)
    max_members = models.IntegerField(default=50)
    group_code = models.CharField(max_length=12, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
            while Group.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{slugify(self.name)}-{uuid.uuid4().hex[:4]}"
        if not self.group_code:
            self.group_code = uuid.uuid4().hex[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("group_detail", kwargs={"slug": self.slug})

    @property
    def member_count(self):
        return self.members.count()


class GroupMembership(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_admin = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("group", "user")

    def __str__(self):
        return f"{self.user} in {self.group}"


class VaultFile(models.Model):
    FILE_TYPES = [
        ("image", "Image"), ("video", "Video"), ("document", "Document"),
        ("archive", "Archive"), ("audio", "Audio"), ("other", "Other"),
    ]

    file = models.FileField(upload_to=vault_file_path)
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=20, choices=FILE_TYPES, default="other")
    file_size = models.BigIntegerField(default=0)
    file_hash = models.CharField(max_length=64, blank=True, db_index=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="files")
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True, related_name="files")
    is_favorite = models.BooleanField(default=False)
    tags = models.ManyToManyField(Tag, blank=True, related_name="files")
    description = models.TextField(blank=True)
    version_number = models.IntegerField(default=1)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    download_count = models.IntegerField(default=0)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="deleted_files"
    )

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.file_name

    @property
    def is_group_file(self):
        return self.group_id is not None

    @property
    def days_until_purge(self):
        if not self.deleted_at:
            return None
        elapsed = (timezone.now() - self.deleted_at).days
        return max(0, 30 - elapsed)

    @staticmethod
    def guess_type(filename):
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        types = {
            "image": {"jpg", "jpeg", "png", "gif", "webp", "svg", "bmp"},
            "video": {"mp4", "mov", "avi", "mkv", "webm"},
            "audio": {"mp3", "wav", "flac", "ogg"},
            "archive": {"zip", "rar", "7z", "tar", "gz"},
            "document": {"pdf", "doc", "docx", "txt", "xls", "xlsx", "ppt", "pptx", "md"}
        }
        return next((k for k, v in types.items() if ext in v), "other")

    @staticmethod
    def compute_hash(django_file):
        h = hashlib.sha256()
        for chunk in django_file.chunks():
            h.update(chunk)
        django_file.seek(0)
        return h.hexdigest()


class ActivityLog(models.Model):
    ACTIONS = [
        ("upload", "Upload"), ("download", "Download"), ("delete", "Delete"),
        ("restore", "Restore"), ("permanent_delete", "Permanent Delete"),
        ("join", "Join"), ("leave", "Leave"), ("create_group", "Create Group"),
        ("favorite", "Favorite"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activity_logs")
    action = models.CharField(max_length=20, choices=ACTIONS)
    file = models.ForeignKey(VaultFile, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs")
    group = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True, blank=True, related_name="activity_logs")
    description = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user} {self.action} @ {self.timestamp:%Y-%m-%d %H:%M}"


class Notification(models.Model):
    TYPES = [("upload", "Upload"), ("invite", "Invite"), ("delete", "Delete"), ("restore", "Restore")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    message = models.TextField()
    type = models.CharField(max_length=20, choices=TYPES, default="upload")
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notif -> {self.user}: {self.message[:30]}"
