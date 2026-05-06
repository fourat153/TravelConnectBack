@router.get("/", response_model=FriendshipRequestOut, status_code=status.HTTP_200_OK)
def get_my_friends(
    db: Session = Depends(get_db),
    current_user = Depends(oauth2.get_current_user),
    page: int = 1,
    limit: int = 10,
):
    offset = (page - 1) * limit

    try:
        query = db.query(models.User).join(
            models.Friendship,
            (
                (models.Friendship.user_1_id == current_user.user_id) & (models.Friendship.user_2_id == models.User.id)
            ) | (
                (models.Friendship.user_2_id == current_user.user_id) & (models.Friendship.user_1_id == models.User.id)
            )
        )

        total   = query.count()
        results = query.offset(offset).limit(limit).all()

        if not results:
            return FriendshipRequestOut(
                status_code=status.HTTP_404_NOT_FOUND,
                message="No friends found.",
            )

        friends = [
            FriendOut(
                friend_id       = user.id,
                username        = user.username,
                profile_picture = user.profile_picture,
            )
            for user in results
        ]

    except Exception as e:
        return FriendshipRequestOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(e),
        )

    return FriendshipRequestOut(
        status_code = status.HTTP_200_OK,
        message     = "Friends retrieved successfully.",
        data        = friends,
        total       = total,
        page        = page,
        limit       = limit,
        pages       = ceil(total / limit),
    )