"""The pending Ennova members list on its own, without the API."""
from domain import models
from domain.use_cases import db_ennova_members


def test_normalize_email():
    assert db_ennova_members.normalize_email("  Ana.Garcia@ESADE.edu ") == "ana.garcia@esade.edu"


def test_save_pending_skips_blanks_and_duplicates(db, organiser):
    saved = db_ennova_members.save_pending(
        db, ["a@esade.edu", "A@esade.edu", " ", "b@esade.edu"], "list.xlsx", organiser.user_id
    )
    assert saved == 2
    assert db_ennova_members.save_pending(db, ["b@esade.edu"], "list.xlsx", organiser.user_id) == 0
    assert db_ennova_members.save_pending(db, [], None, None) == 0


def test_claim_only_when_listed(db, make_user):
    db_ennova_members.save_pending(db, ["listed@esade.edu"], None, None)
    listed = make_user(email="Listed@esade.edu")
    other = make_user(email="other@esade.edu")

    assert db_ennova_members.claim_pending_membership(db, other) is False
    assert other.is_ennova_member is False
    assert db_ennova_members.claim_pending_membership(db, listed) is True
    assert listed.is_ennova_member is True
    db.flush()
    assert db.query(models.PendingEnnovaMember).count() == 0


def test_find_users_by_emails_ignores_case(db, make_user):
    user = make_user(email="Mixed.Case@esade.edu")
    assert db_ennova_members.find_users_by_emails(db, ["MIXED.case@esade.edu"]) == {"mixed.case@esade.edu": user}
    assert db_ennova_members.find_users_by_emails(db, []) == {}
