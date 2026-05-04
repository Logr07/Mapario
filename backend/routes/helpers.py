"""Shared helpers for route handlers."""

from flask import session


def get_current_user_id() -> int | None:
    user_id = session.get("user_id")
    if user_id is None:
        return None
    return int(user_id)
