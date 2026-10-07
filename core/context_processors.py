from .models import Notification


def workpulse_notifications(request):
    if not request.user.is_authenticated:
        return {}
    notifications = Notification.objects.filter(recipient=request.user)
    return {
        'unread_notifications': notifications.filter(read_at__isnull=True)[:5],
        'unread_notification_count': notifications.filter(read_at__isnull=True).count(),
    }
