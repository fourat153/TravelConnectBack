from sqlalchemy.orm import aliased, Session
from sqlalchemy import func, distinct, or_, and_, union, select, literal

from app.models.user import User
from app.models.Friendship import Friendship
from app.models.FriendshipRequest import FriendshipRequest
from app.models.UserCityAffinity import UserCityAffinity


def _excluded_ids(current_user_id: int):
    return union(
        select(Friendship.user_2_id).where(Friendship.user_1_id == current_user_id),
        select(Friendship.user_1_id).where(Friendship.user_2_id == current_user_id),
        select(FriendshipRequest.receiver_id).where(FriendshipRequest.sender_id == current_user_id),
        select(FriendshipRequest.sender_id).where(FriendshipRequest.receiver_id == current_user_id),
    )


def _my_friend_ids(current_user_id: int):
    return union(
        select(Friendship.user_2_id).where(Friendship.user_1_id == current_user_id),
        select(Friendship.user_1_id).where(Friendship.user_2_id == current_user_id),
    )


def get_friend_suggestions(current_user_id: int, db: Session):
    has_affinity = (
        db.query(UserCityAffinity)
        .filter(UserCityAffinity.user_id == current_user_id)
        .first()
    )

    excluded = _excluded_ids(current_user_id)

    if has_affinity:
        uca_me    = aliased(UserCityAffinity, name="uca_me")
        uca_other = aliased(UserCityAffinity, name="uca_other")
        mf        = aliased(Friendship)

        mutual_count = (
            select(func.count(distinct(mf.id)))
            .where(
                or_(
                    and_(mf.user_1_id == User.id, mf.user_2_id.in_(_my_friend_ids(current_user_id))),
                    and_(mf.user_2_id == User.id, mf.user_1_id.in_(_my_friend_ids(current_user_id))),
                )
            )
            .correlate(User)
            .scalar_subquery()
        )

        results =  (
            db.query(
                User.id,
                User.firstname,
                User.lastname,
                User.profile_picture,
                func.count(distinct(uca_other.city_id)).label("shared_cities"),
                func.sum(uca_other.visit_count).label("affinity_score"),
                mutual_count.label("mutual_friends_count"),
            )
            .select_from(uca_me)
            .join(uca_other, and_(
                uca_me.city_id    == uca_other.city_id,
                uca_other.user_id != current_user_id,
            ))
            .join(User, User.id == uca_other.user_id)
            .filter(
                uca_me.user_id == current_user_id,
                User.id.notin_(excluded),
            )
            .group_by(User.id, User.firstname, User.lastname, User.profile_picture)
            .order_by(
                func.count(distinct(uca_other.city_id)).desc(),
                func.sum(uca_other.visit_count).desc(),
            )
            .limit(3)
            .all()
        )
        if results:
            return results

    return (
            db.query(
                User.id,
                User.firstname,
                User.lastname,
                User.profile_picture,
                literal(0).label("mutual_friends_count"),
            )
            .filter(
                User.id != current_user_id,
                User.id.notin_(excluded),
            )
            .order_by(func.random())
            .limit(3)
            .all()
        )