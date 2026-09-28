from notifications.models import Notification

def notification_data(request):

    if not request.user.is_authenticated:
        return {}

    notifications = Notification.objects.filter(
        user=request.user
    ).order_by("-id")[:5]

    unread_count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()

    return {
        "notifications": notifications,
        "unread_count": unread_count,
    }