"""AI feedback summaries are open to the event's organiser and to any super admin. OpenAI is never called."""
import pytest

from domain import models
from tests.conftest import auth_headers


@pytest.fixture
def event(make_event):
    return make_event()


@pytest.fixture
def admin(make_user):
    return make_user(email="admin@example.com", roles=("super_admin",))


@pytest.fixture
def other_organiser_headers(make_user):
    return auth_headers(make_user(email="other-organiser@example.com", roles=("organiser",)))


@pytest.fixture
def summary(db, event, organiser):
    made = models.AISummary(event_id=event.event_id, generated_by_user_id=organiser.user_id, feedback_count=5,
                            summary_text="People loved the talks.", summary_json={"highlights": []},
                            model_used="test-model", sent_to_emails=[])
    db.add(made)
    db.commit()
    return made


def base(event):
    return f"/admin/events/{event.event_id}/feedback/summaries"


class TestSuperAdmin:
    def test_can_list_and_read_summaries_for_an_event_they_did_not_create(self, client, admin, event, summary):
        headers = auth_headers(admin)

        listed = client.get(base(event), headers=headers)
        assert listed.status_code == 200
        assert listed.json()["total_count"] == 1

        one = client.get(f"{base(event)}/{summary.summary_id}", headers=headers)
        assert one.status_code == 200
        assert one.json()["summary_text"] == "People loved the talks."

    def test_can_send_a_summary(self, client, admin, event, summary, sent_emails):
        response = client.post(f"{base(event)}/{summary.summary_id}/send",
                               json={"custom_emails": ["board@example.com"]}, headers=auth_headers(admin))

        assert response.status_code == 200
        assert [email["to"] for email in sent_emails] == ["board@example.com"]

    def test_gets_past_the_permission_check_when_generating(self, client, admin, event):
        # With no feedback yet the request stops before reaching OpenAI.
        response = client.post(f"{base(event)}/generate", headers=auth_headers(admin))

        assert response.status_code == 400
        assert response.json()["detail"] == "Need at least 3 feedback responses to generate a summary"


class TestEventOrganiser:
    def test_can_list_their_own_events_summaries(self, client, organiser_headers, event, summary):
        assert client.get(base(event), headers=organiser_headers).status_code == 200


class TestOtherOrganiser:
    def test_is_refused_everywhere_and_nothing_is_sent(self, client, other_organiser_headers, event, summary, sent_emails):
        responses = [
            client.get(base(event), headers=other_organiser_headers),
            client.get(f"{base(event)}/{summary.summary_id}", headers=other_organiser_headers),
            client.post(f"{base(event)}/{summary.summary_id}/send",
                        json={"custom_emails": ["board@example.com"]}, headers=other_organiser_headers),
            client.post(f"{base(event)}/generate", headers=other_organiser_headers),
        ]

        assert [r.status_code for r in responses] == [403, 403, 403, 403]
        assert responses[0].json()["detail"] == "Only the event organiser or a super admin can access AI summaries"
        assert sent_emails == []
