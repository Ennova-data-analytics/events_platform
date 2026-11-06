"""
An event's photos, attachments and sponsor logos can be changed by the event's
organiser and by any super admin, and by nobody else. S3 is stubbed out.
"""
import pytest

from domain import models
from tests.conftest import auth_headers


@pytest.fixture
def event(make_event):
    return make_event(sponsor_logos=["sponsor_logos/one.png", "sponsor_logos/two.png"])


@pytest.fixture
def admin_headers(make_user):
    return auth_headers(make_user(email="admin@example.com", roles=("super_admin",)))


@pytest.fixture
def other_organiser_headers(make_user):
    return auth_headers(make_user(email="other-organiser@example.com", roles=("organiser",)))


@pytest.fixture
def photos(db, event):
    made = [
        models.EventPhoto(event_id=event.event_id, photo_url=f"https://cdn.example.invalid/{n}.jpg", display_order=n)
        for n in range(2)
    ]
    db.add_all(made)
    db.commit()
    return made


@pytest.fixture
def attachments(db, event):
    made = [
        models.EventAttachment(event_id=event.event_id, file_url=f"https://cdn.example.invalid/{n}.pdf",
                               file_name=f"guide-{n}.pdf", file_type="pdf", display_order=n)
        for n in range(2)
    ]
    db.add_all(made)
    db.commit()
    return made


@pytest.fixture
def s3_uploads(monkeypatch):
    """Record uploads instead of sending them to S3."""
    from api.routers import events as events_router
    from domain.use_cases import db_event_attachments, db_event_photos

    uploaded = []

    def upload_logo(file, key):
        uploaded.append(key)

    def upload_photo(photo_file, event_id, process_images=True):
        uploaded.append(photo_file.filename)
        return f"https://cdn.example.invalid/{photo_file.filename}", None

    def upload_attachment(file, event_id):
        uploaded.append(file.filename)
        return f"attachments/{file.filename}", "pdf", 3

    monkeypatch.setattr(events_router.image_processing_service, "validate_image", lambda f: (True, None))
    monkeypatch.setattr(events_router.s3_service, "upload_file_to_s3", upload_logo)
    monkeypatch.setattr(db_event_photos, "upload_photo_to_s3", upload_photo)
    monkeypatch.setattr(db_event_attachments, "upload_attachment_to_s3", upload_attachment)
    return uploaded


def every_change(client, headers, event, photos, attachments):
    """Hit each owner-only endpoint once, in order; return {name: status code}."""
    e = event.event_id
    keep_photo, drop_photo = (p.photo_id for p in photos)
    keep_attachment, drop_attachment = (a.attachment_id for a in attachments)
    upload = lambda name: (name, b"bytes", "application/octet-stream")  # noqa: E731
    photo_ids = lambda: [p["photo_id"] for p in client.get(f"/events/{e}/photos").json()]  # noqa: E731
    attachment_ids = lambda: [a["attachment_id"] for a in client.get(f"/events/{e}/attachments").json()]  # noqa: E731

    status = {}
    status["upload logos"] = client.post(f"/events/{e}/sponsor-logos?process_images=false",
                                         files=[("logo_files", upload("logo.png"))], headers=headers).status_code
    status["delete logo"] = client.delete(f"/events/{e}/sponsor-logos/0", headers=headers).status_code
    status["upload photos"] = client.post(f"/events/{e}/photos",
                                          files=[("photo_files", upload("new.jpg"))], headers=headers).status_code
    status["update photo"] = client.patch(f"/events/{e}/photos/{keep_photo}", json={"caption": "Hi"},
                                          headers=headers).status_code
    status["reorder photos"] = client.post(f"/events/{e}/photos/reorder", json=photo_ids()[::-1],
                                           headers=headers).status_code
    status["delete photo"] = client.delete(f"/events/{e}/photos/{drop_photo}", headers=headers).status_code
    status["upload attachment"] = client.post(f"/events/{e}/attachments",
                                              files={"file": upload("agenda.pdf")}, headers=headers).status_code
    status["update attachment"] = client.patch(f"/events/{e}/attachments/{keep_attachment}",
                                               json={"description": "Agenda"}, headers=headers).status_code
    status["reorder attachments"] = client.post(f"/events/{e}/attachments/reorder", json=attachment_ids()[::-1],
                                                headers=headers).status_code
    status["delete attachment"] = client.delete(f"/events/{e}/attachments/{drop_attachment}",
                                                headers=headers).status_code
    return status


ALLOWED = {
    "upload logos": 200, "delete logo": 200,
    "upload photos": 200, "update photo": 200, "reorder photos": 200, "delete photo": 204,
    "upload attachment": 201, "update attachment": 200, "reorder attachments": 200, "delete attachment": 204,
}


def test_super_admin_can_change_media_on_an_event_they_did_not_create(
    client, db, admin_headers, event, photos, attachments, s3_uploads
):
    assert every_change(client, admin_headers, event, photos, attachments) == ALLOWED

    db.expire_all()
    logos = db.get(models.Event, event.event_id).sponsor_logos
    assert logos[0] == "sponsor_logos/two.png" and len(logos) == 2
    assert s3_uploads == [logos[1], "new.jpg", "agenda.pdf"]
    assert db.get(models.EventPhoto, photos[0].photo_id).caption == "Hi"
    assert db.get(models.EventPhoto, photos[1].photo_id) is None
    assert db.get(models.EventAttachment, attachments[0].attachment_id).description == "Agenda"
    assert db.get(models.EventAttachment, attachments[1].attachment_id) is None


def test_event_organiser_can_change_their_own_event(
    client, organiser_headers, event, photos, attachments, s3_uploads
):
    assert every_change(client, organiser_headers, event, photos, attachments) == ALLOWED


def test_another_organiser_is_refused_everywhere_and_nothing_changes(
    client, db, other_organiser_headers, event, photos, attachments, s3_uploads
):
    results = every_change(client, other_organiser_headers, event, photos, attachments)

    assert results == {name: 403 for name in ALLOWED}
    assert s3_uploads == []
    db.expire_all()
    assert db.get(models.Event, event.event_id).sponsor_logos == ["sponsor_logos/one.png", "sponsor_logos/two.png"]
    assert db.query(models.EventPhoto).filter_by(event_id=event.event_id).count() == 2
    assert db.query(models.EventAttachment).filter_by(event_id=event.event_id).count() == 2
