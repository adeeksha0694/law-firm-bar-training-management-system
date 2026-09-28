from notifications.models import Notification


def notify(user, title, message):

    try:

        if not user:
            return

        Notification.objects.create(
            user=user,
            title=title,
            message=message
        )

    except Exception:
        pass