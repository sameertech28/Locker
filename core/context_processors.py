from .models import Notification


def notifications(request):
    if request.user.is_authenticated:
        unread = Notification.objects.filter(user=request.user, is_read=False).count()
        return {"unread_notification_count": unread}
    return {"unread_notification_count": 0}
