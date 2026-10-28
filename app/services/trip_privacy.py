from app.enums import PrivacyEntityType, PrivacyType
from app.models import Friendship, PrivacySettings, Trip
from sqlmodel import Session


def can_view_trip(
    db: Session,
    trip: Trip,
    viewer_id: int,
    friend_ids: set[int] | None = None,
) -> bool:
    if trip.user_id == viewer_id:
        return True

    setting = db.query(PrivacySettings).filter(
        PrivacySettings.entity_type == PrivacyEntityType.trip,
        PrivacySettings.entity_id == trip.id,
    ).first()
    privacy_type = setting.privacy_type if setting else PrivacyType.public

    if privacy_type == PrivacyType.public:
        return True
    if privacy_type == PrivacyType.private:
        return False

    if friend_ids is None:
        friend_ids = {
            friendship.user_2_id
            if friendship.user_1_id == viewer_id
            else friendship.user_1_id
            for friendship in db.query(Friendship).filter(
                (Friendship.user_1_id == viewer_id)
                | (Friendship.user_2_id == viewer_id)
            ).all()
        }

    return trip.user_id in friend_ids