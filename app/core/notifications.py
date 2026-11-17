from app.models.notification import Notification


def add_member_notification(
    db,
    *,
    recipient_id: int,
    service_request_id: int | None = None,
    notification_type: str,
    title: str,
    message: str,
) -> None:
    db.add(Notification(
        recipient_id=recipient_id,
        service_request_id=service_request_id,
        notification_type=notification_type,
        title=title,
        message=message,
    ))
