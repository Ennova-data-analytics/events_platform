"""Who may manage an event: its creator or a super admin. Unsaved model objects: no database."""
import uuid

import pytest
from fastapi import HTTPException

from api.deps import ensure_can_manage_event
from domain import models
from domain.use_cases.event_permissions import can_manage_event, check_can_manage_event


def user(*roles):
    person = models.User(user_id=uuid.uuid4(), email=f"{uuid.uuid4().hex[:8]}@example.com")
    person.roles = [models.Role(role_name=name) for name in roles]
    return person


def event_by(creator):
    return models.Event(event_id=1, created_by_user_id=creator.user_id)


class TestCanManageEvent:
    def test_event_creator_may(self):
        creator = user('organiser')
        assert can_manage_event(event_by(creator), creator)

    def test_super_admin_may_for_any_event(self):
        assert can_manage_event(event_by(user('organiser')), user('super_admin'))

    def test_super_admin_alongside_other_roles_may(self):
        assert can_manage_event(event_by(user('organiser')), user('attendee', 'super_admin'))

    @pytest.mark.parametrize('roles', [('organiser',), ('recruiter',), ('attendee',), ()])
    def test_anyone_else_may_not(self, roles):
        assert not can_manage_event(event_by(user('organiser')), user(*roles))


class TestCheckCanManageEvent:
    def test_passes_for_a_super_admin(self):
        check_can_manage_event(event_by(user('organiser')), user('super_admin'), "create discount codes for this event")

    def test_refuses_with_a_403_naming_the_action(self):
        with pytest.raises(HTTPException) as refused:
            check_can_manage_event(event_by(user('organiser')), user('organiser'), "create referral links for this event")

        assert refused.value.status_code == 403
        assert refused.value.detail == "You don't have permission to create referral links for this event"


class TestEnsureCanManageEvent:
    def test_passes_for_a_super_admin(self):
        ensure_can_manage_event(event_by(user('organiser')), user('super_admin'))

    def test_refuses_another_organiser(self):
        with pytest.raises(HTTPException) as refused:
            ensure_can_manage_event(event_by(user('organiser')), user('organiser'))

        assert refused.value.status_code == 403
        assert refused.value.detail == "Not authorized to modify this event"
