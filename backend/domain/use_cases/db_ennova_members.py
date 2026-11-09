"""
Ennova members who haven't made an account yet.

An imported members list usually has emails that don't match any account. We
keep those as pending members, and when someone signs up with one of them they
become an Ennova member straight away. Emails are compared case-insensitively
and stored lowercased.
"""
import logging
import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from domain import models

logger = logging.getLogger(__name__)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def save_pending(
    db: Session,
    emails: list[str],
    source_filename: str | None,
    added_by_user_id: uuid.UUID | None,
) -> int:
    """
    Remember emails that have no account yet. Emails already on the pending
    list are left as they were. Returns how many were newly saved. Doesn't
    commit: the caller's import commits it with the members it added.
    """
    normalized = sorted({normalize_email(e) for e in emails if e and e.strip()})
    if not normalized:
        return 0

    statement = (
        insert(models.PendingEnnovaMember)
        .values([
            {"email": email, "source_filename": source_filename, "added_by_user_id": added_by_user_id}
            for email in normalized
        ])
        .on_conflict_do_nothing(index_elements=["email"])
        .returning(models.PendingEnnovaMember.pending_member_id)
    )
    return len(db.execute(statement).fetchall())


def claim_pending_membership(db: Session, user: models.User) -> bool:
    """
    If the user's email is on the pending list, make them an Ennova member and
    take the email off the list. Doesn't commit, so it's part of creating the
    account.
    """
    pending = (
        db.query(models.PendingEnnovaMember)
        .filter(models.PendingEnnovaMember.email == normalize_email(user.email))
        .first()
    )
    if pending is None:
        return False

    user.is_ennova_member = True
    db.delete(pending)
    logger.info(
        f"New account {user.email} is on the Ennova members list "
        f"(imported from {pending.source_filename or 'an earlier import'}): made a member"
    )
    return True


def list_pending(db: Session, search: str | None = None, skip: int = 0, limit: int = 100):
    """Pending emails, newest first, with the total count for the same search."""
    query = db.query(models.PendingEnnovaMember)
    if search:
        query = query.filter(models.PendingEnnovaMember.email.ilike(f"%{search.strip()}%"))
    total = query.count()
    rows = (
        query.order_by(models.PendingEnnovaMember.created_at.desc(), models.PendingEnnovaMember.email)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return rows, total


def remove_pending(db: Session, pending_member_id: int) -> models.PendingEnnovaMember | None:
    """Take one email off the pending list. Returns None if there's no such row."""
    pending = db.get(models.PendingEnnovaMember, pending_member_id)
    if pending is None:
        return None
    db.delete(pending)
    db.commit()
    return pending


def clear_pending(db: Session) -> int:
    """Empty the pending list (e.g. for a new academic year). Returns how many were removed."""
    removed = db.query(models.PendingEnnovaMember).delete(synchronize_session=False)
    db.commit()
    return removed


def find_users_by_emails(db: Session, emails: list[str]) -> dict[str, models.User]:
    """Accounts for these emails, keyed by lowercased email, ignoring case on both sides."""
    normalized = {normalize_email(e) for e in emails}
    if not normalized:
        return {}
    users = db.query(models.User).filter(func.lower(models.User.email).in_(normalized)).all()
    return {normalize_email(user.email): user for user in users}
