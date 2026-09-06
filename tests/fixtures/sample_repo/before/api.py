def get_user(user_id):
    """Fetch a user by id."""
    return db.query(user_id)
