from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .decorators import rate_limit
from .forms import CustomLoginForm, GroupForm, ProfileForm, RegisterForm, VaultFileEditForm, VaultFileUploadForm
from .models import ActivityLog, Group, GroupMembership, Notification, Profile, Tag, VaultFile


# ---------- helpers ----------

def log_activity(user, action, file=None, group=None, description="", request=None):
    ip = None
    if request is not None:
        ip = request.META.get("REMOTE_ADDR")
    ActivityLog.objects.create(
        user=user, action=action, file=file, group=group, description=description, ip_address=ip
    )


def notify(user, message, ntype="upload", link=""):
    Notification.objects.create(user=user, message=message, type=ntype, link=link)


def notify_group_members(group, actor, message, ntype="upload", link=""):
    for member in group.members.exclude(id=actor.id):
        notify(member, message, ntype=ntype, link=link)


# ---------- landing / auth ----------

def landing(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    stats = {
        "users": User.objects.count(),
        "files": VaultFile.objects.filter(is_deleted=False).count(),
        "groups": Group.objects.count(),
    }
    return render(request, "landing.html", {"stats": stats})


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(request, "Welcome to Locker. Your vault is ready.")
            return redirect("dashboard")
    else:
        form = RegisterForm()
    return render(request, "auth/register.html", {"form": form})


class LockerLoginView(LoginView):
    template_name = "auth/login.html"
    redirect_authenticated_user = True
    form_class = CustomLoginForm


def logout_view(request):
    logout(request)
    return redirect("landing")


# ---------- dashboard ----------

@login_required
def dashboard(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    recent_files = VaultFile.objects.filter(uploaded_by=request.user, is_deleted=False, group__isnull=True)[:8]
    my_groups = request.user.vault_groups.all()[:6]
    recent_activity = ActivityLog.objects.filter(user=request.user).select_related("file", "group")[:10]
    unread_notifications = Notification.objects.filter(user=request.user, is_read=False).count()
    return render(request, "dashboard.html", {
        "profile": profile,
        "recent_files": recent_files,
        "my_groups": my_groups,
        "recent_activity": recent_activity,
        "unread_notifications": unread_notifications,
    })


# ---------- personal files ----------

@login_required
def file_explorer(request):
    files = VaultFile.objects.filter(uploaded_by=request.user, is_deleted=False, group__isnull=True)

    query = request.GET.get("q", "").strip()
    if query:
        files = files.filter(Q(file_name__icontains=query) | Q(description__icontains=query))

    file_type = request.GET.get("type")
    if file_type:
        files = files.filter(file_type=file_type)

    only_favorites = request.GET.get("favorites")
    if only_favorites:
        files = files.filter(is_favorite=True)

    sort = request.GET.get("sort", "-uploaded_at")
    allowed_sorts = {"-uploaded_at", "uploaded_at", "file_name", "-file_name", "-file_size", "file_size"}
    if sort in allowed_sorts:
        files = files.order_by(sort)

    paginator = Paginator(files, 24)
    page_obj = paginator.get_page(request.GET.get("page"))

    if request.method == "POST":
        form = VaultFileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file_size = request.FILES["file"].size
            profile, _ = Profile.objects.get_or_create(user=request.user)
            if profile.storage_used + file_size > profile.storage_limit:
                messages.error(request, "Storage limit exceeded! Please delete some files.")
                return redirect("file_explorer")

            vfile = form.save(commit=False)
            vfile.uploaded_by = request.user
            vfile.file_name = request.FILES["file"].name
            vfile.file_size = file_size
            vfile.file_type = VaultFile.guess_type(vfile.file_name)
            vfile.file_hash = VaultFile.compute_hash(request.FILES["file"])
            vfile.save()

            profile.storage_used += file_size
            profile.save()

            log_activity(request.user, "upload", file=vfile, description=vfile.file_name, request=request)
            messages.success(request, f'"{vfile.file_name}" uploaded to your vault.')
            return redirect("file_explorer")
    else:
        form = VaultFileUploadForm()

    return render(request, "files/explorer.html", {
        "page_obj": page_obj, "form": form, "query": query, "file_type": file_type, "sort": sort,
    })


@login_required
@rate_limit(max_requests=60, window_seconds=60)
def file_download(request, pk):
    vfile = get_object_or_404(VaultFile, pk=pk)
    if not _can_access_file(request.user, vfile):
        raise Http404
    vfile.download_count += 1
    vfile.save(update_fields=["download_count"])
    log_activity(request.user, "download", file=vfile, description=vfile.file_name, request=request)
    return FileResponse(vfile.file.open("rb"), as_attachment=True, filename=vfile.file_name)


def _can_access_file(user, vfile):
    if vfile.group_id:
        return GroupMembership.objects.filter(group_id=vfile.group_id, user=user).exists()
    return vfile.uploaded_by_id == user.id


@login_required
@require_POST
def file_delete(request, pk):
    vfile = get_object_or_404(VaultFile, pk=pk, uploaded_by=request.user)
    vfile.is_deleted, vfile.deleted_at, vfile.deleted_by = True, timezone.now(), request.user
    vfile.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])
    log_activity(request.user, "delete", file=vfile, description=vfile.file_name, request=request)
    messages.info(request, f'"{vfile.file_name}" moved to trash.')
    return redirect("group_detail", slug=vfile.group.slug) if vfile.group_id else redirect("file_explorer")


@login_required
@require_POST
def file_restore(request, pk):
    vfile = get_object_or_404(VaultFile, pk=pk, is_deleted=True, uploaded_by=request.user)
    vfile.is_deleted, vfile.deleted_at, vfile.deleted_by = False, None, None
    vfile.save(update_fields=["is_deleted", "deleted_at", "deleted_by"])
    log_activity(request.user, "restore", file=vfile, description=vfile.file_name, request=request)
    messages.success(request, f'"{vfile.file_name}" restored.')
    return redirect("trash")


@login_required
@require_POST
def file_permanent_delete(request, pk):
    vfile = get_object_or_404(VaultFile, pk=pk, is_deleted=True, uploaded_by=request.user)
    name, size = vfile.file_name, vfile.file_size
    vfile.file.delete(save=False)
    vfile.delete()
    Profile.objects.filter(user=request.user).update(storage_used=models.F('storage_used') - size)
    log_activity(request.user, "permanent_delete", description=name, request=request)
    messages.warning(request, f'"{name}" permanently deleted.')
    return redirect("trash")


@login_required
def trash(request):
    files = VaultFile.objects.filter(uploaded_by=request.user, is_deleted=True)
    return render(request, "files/trash.html", {"files": files})


@login_required
@require_POST
def toggle_favorite(request, pk):
    vfile = get_object_or_404(VaultFile, pk=pk)
    if not _can_access_file(request.user, vfile):
        raise Http404
    vfile.is_favorite = not vfile.is_favorite
    vfile.save(update_fields=["is_favorite"])
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"is_favorite": vfile.is_favorite})
    return redirect(request.META.get("HTTP_REFERER", "file_explorer"))


# ---------- groups ----------

@login_required
def group_list(request):
    groups = request.user.vault_groups.all()
    return render(request, "groups/list.html", {"groups": groups})


@login_required
def group_create(request):
    if request.method == "POST":
        form = GroupForm(request.POST, request.FILES)
        if form.is_valid():
            group = form.save(commit=False)
            group.created_by = request.user
            group.save()
            GroupMembership.objects.create(group=group, user=request.user, is_admin=True)
            log_activity(request.user, "create_group", group=group, description=group.name, request=request)
            messages.success(request, f'Group "{group.name}" created. Invite code: {group.group_code}')
            return redirect("group_detail", slug=group.slug)
    else:
        form = GroupForm()
    return render(request, "groups/create.html", {"form": form})


@login_required
def group_detail(request, slug):
    group = get_object_or_404(Group, slug=slug)
    membership = GroupMembership.objects.filter(group=group, user=request.user).first()
    if not membership:
        raise Http404
    files = group.files.filter(is_deleted=False)
    memberships = GroupMembership.objects.filter(group=group).select_related("user")
    activity = group.activity_logs.select_related("user", "file").all()[:15]

    if request.method == "POST" and "file" in request.FILES:
        form = VaultFileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file_size = request.FILES["file"].size
            profile, _ = Profile.objects.get_or_create(user=request.user)
            if profile.storage_used + file_size > profile.storage_limit:
                messages.error(request, "Storage limit exceeded! Please delete some files.")
                return redirect("group_detail", slug=group.slug)

            vfile = form.save(commit=False)
            vfile.uploaded_by = request.user
            vfile.group = group
            vfile.file_name = request.FILES["file"].name
            vfile.file_size = file_size
            vfile.file_type = VaultFile.guess_type(vfile.file_name)
            vfile.file_hash = VaultFile.compute_hash(request.FILES["file"])
            vfile.save()
            
            profile.storage_used += file_size
            profile.save()
            log_activity(request.user, "upload", file=vfile, group=group, description=vfile.file_name, request=request)
            notify_group_members(
                group, request.user,
                f"{request.user.username} uploaded \"{vfile.file_name}\" to {group.name}",
                ntype="upload", link=f"/groups/{group.slug}/",
            )
            messages.success(request, f'"{vfile.file_name}" shared with {group.name}.')
            return redirect("group_detail", slug=group.slug)
    else:
        form = VaultFileUploadForm()

    return render(request, "groups/detail.html", {
        "group": group, "files": files, "memberships": memberships,
        "activity": activity, "form": form, "membership": membership,
    })


@login_required
@require_POST
def group_join(request, code):
    group = get_object_or_404(Group, group_code=code.upper())
    if group.member_count >= group.max_members:
        messages.error(request, "This group is full.")
        return redirect("group_list")
    GroupMembership.objects.get_or_create(group=group, user=request.user)
    log_activity(request.user, "join", group=group, description=group.name, request=request)
    notify_group_members(group, request.user, f"{request.user.username} joined {group.name}", ntype="invite")
    messages.success(request, f'Joined "{group.name}".')
    return redirect("group_detail", slug=group.slug)


@login_required
def group_join_form(request):
    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        return group_join(request, code)
    return render(request, "groups/join.html")


@login_required
@require_POST
def group_leave(request, slug):
    group = get_object_or_404(Group, slug=slug)
    GroupMembership.objects.filter(group=group, user=request.user).delete()
    log_activity(request.user, "leave", group=group, description=group.name, request=request)
    messages.info(request, f'Left "{group.name}".')
    return redirect("group_list")


@login_required
@require_POST
def group_add_member(request, slug):
    group = get_object_or_404(Group, slug=slug)
    membership = get_object_or_404(GroupMembership, group=group, user=request.user)
    if not membership.is_admin:
        raise Http404
    email_or_username = request.POST.get("identifier", "").strip()
    target = User.objects.filter(Q(email=email_or_username) | Q(username=email_or_username)).first()
    if not target:
        messages.error(request, "No matching user found.")
    else:
        GroupMembership.objects.get_or_create(group=group, user=target)
        notify(target, f"You were added to {group.name}", ntype="invite", link=f"/groups/{group.slug}/")
        messages.success(request, f"{target.username} added to the group.")
    return redirect("group_detail", slug=slug)


@login_required
@require_POST
def group_remove_member(request, slug, user_id):
    group = get_object_or_404(Group, slug=slug)
    membership = get_object_or_404(GroupMembership, group=group, user=request.user)
    if not membership.is_admin:
        raise Http404
    GroupMembership.objects.filter(group=group, user_id=user_id).delete()
    messages.info(request, "Member removed.")
    return redirect("group_detail", slug=slug)


# ---------- notifications ----------

@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user).only("id", "message", "type", "is_read", "link", "created_at")
    return render(request, "notifications/list.html", {"notifications": notifications})


@login_required
@require_POST
def notification_read(request, pk):
    Notification.objects.filter(pk=pk, user=request.user).update(is_read=True)
    return redirect("notifications")


@login_required
@require_POST
def notification_read_all(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect("notifications")


@login_required
@rate_limit(max_requests=120, window_seconds=60)
def notification_poll(request):
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({"unread": count})


# ---------- profile ----------

@login_required
def profile_view(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("profile")
    else:
        form = ProfileForm(instance=profile, user=request.user)
    file_count = VaultFile.objects.filter(uploaded_by=request.user, is_deleted=False).count()
    return render(request, "users/profile.html", {"form": form, "profile": profile, "file_count": file_count})
