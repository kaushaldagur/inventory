import secrets

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models
from .security import hash_password


class UserAlreadyExistsError(Exception):
    pass


def create_user_account(db: Session, *, full_name: str, email: str, password: str) -> models.User:
    salt = secrets.token_hex(16)
    user = models.User(
        full_name=full_name,
        email=email,
        password_hash=hash_password(password, salt),
        password_salt=salt,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise UserAlreadyExistsError(f"User with email {email} already exists") from exc
    db.refresh(user)
    return user
