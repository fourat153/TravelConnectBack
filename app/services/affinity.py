from datetime import datetime
from Dbengin import SessionLocal
from app.models.UserCityAffinity import UserCityAffinity


def increment_city_affinity(user_id: int, city_id: int):
    db = SessionLocal()
    try:
        affinity = (
            db.query(UserCityAffinity)
            .filter(
                UserCityAffinity.user_id == user_id,
                UserCityAffinity.city_id == city_id
            )
            .first()
        )

        if affinity:
            affinity.visit_count += 1
            affinity.updated_at = datetime.utcnow()
        else:
            affinity = UserCityAffinity(
                user_id=user_id,
                city_id=city_id,
                visit_count=1,
                updated_at=datetime.utcnow()
            )
            db.add(affinity)

        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()