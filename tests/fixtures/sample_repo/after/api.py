def fetch_user(user_id, include_deleted=False):
    """Fetch a user by id, optionally including soft-deleted users."""
    return db.query(user_id, include_deleted=include_deleted)
