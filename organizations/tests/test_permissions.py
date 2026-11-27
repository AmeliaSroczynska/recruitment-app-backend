from types import SimpleNamespace

import pytest
from rest_framework.exceptions import NotFound

from organizations.models import Role
from organizations.permissions import (
    IsAcceptedCandidate,
    IsCandidate,
    IsCoordinator,
    IsCoordinatorOrReadOnly,
    IsEditionMember,
    IsMentor,
    IsRecruiter,
    has_role,
)
from recruitment.models import ApplicationStatus

pytestmark = pytest.mark.django_db

COORDINATOR = Role.Name.COORDINATOR
RECRUITER = Role.Name.RECRUITER
MENTOR = Role.Name.MENTOR
OBSERVER = Role.Name.OBSERVER


def check(permission, user, method, **kwargs):
    request = SimpleNamespace(user=user, method=method)
    view = SimpleNamespace(kwargs=kwargs)
    return permission().has_permission(request, view), view


def check_edition(permission, membership, method="GET"):
    allowed, _ = check(
        permission, membership.user, method, edition_id=membership.edition_id
    )
    return allowed


@pytest.mark.parametrize(
    ("role", "required", "expected"),
    [
        (COORDINATOR, COORDINATOR, True),
        (COORDINATOR, RECRUITER, True),
        (COORDINATOR, MENTOR, True),
        (RECRUITER, RECRUITER, True),
        (RECRUITER, MENTOR, False),
        (RECRUITER, COORDINATOR, False),
        (MENTOR, MENTOR, True),
        (MENTOR, RECRUITER, False),
        (OBSERVER, RECRUITER, False),
    ],
)
def test_has_role_follows_role_inheritance(make_member, role, required, expected):
    assert has_role(make_member(role), required) is expected


def test_edition_member_hides_edition_from_outsider(user, edition):
    with pytest.raises(NotFound):
        check(IsEditionMember, user, "GET", edition_id=edition.id)


def test_edition_member_sets_membership_on_view(make_member):
    membership = make_member(MENTOR)

    allowed, view = check(
        IsEditionMember, membership.user, "GET", edition_id=membership.edition_id
    )

    assert allowed is True
    assert view.membership == membership
    assert view.edition == membership.edition


@pytest.mark.parametrize(
    ("role", "method", "expected"),
    [
        (OBSERVER, "GET", True),
        (OBSERVER, "POST", False),
        (MENTOR, "POST", True),
        (RECRUITER, "DELETE", True),
    ],
)
def test_edition_member_blocks_only_observer_writes(
    make_member, role, method, expected
):
    assert check_edition(IsEditionMember, make_member(role), method) is expected


@pytest.mark.parametrize(
    ("role", "method", "expected"),
    [
        (RECRUITER, "GET", True),
        (RECRUITER, "PATCH", False),
        (COORDINATOR, "PATCH", True),
    ],
)
def test_coordinator_or_read_only(make_member, role, method, expected):
    assert check_edition(IsCoordinatorOrReadOnly, make_member(role), method) is expected


@pytest.mark.parametrize(
    ("permission", "role", "method", "expected"),
    [
        (IsCoordinator, COORDINATOR, "PATCH", True),
        (IsCoordinator, RECRUITER, "GET", False),
        (IsCoordinator, OBSERVER, "GET", True),
        (IsCoordinator, OBSERVER, "PATCH", False),
        (IsRecruiter, RECRUITER, "POST", True),
        (IsRecruiter, COORDINATOR, "POST", True),
        (IsRecruiter, MENTOR, "GET", False),
        (IsRecruiter, OBSERVER, "GET", True),
        (IsMentor, MENTOR, "POST", True),
        (IsMentor, COORDINATOR, "POST", True),
        (IsMentor, RECRUITER, "GET", False),
        (IsMentor, OBSERVER, "GET", True),
        (IsMentor, OBSERVER, "POST", False),
    ],
)
def test_role_permissions(make_member, permission, role, method, expected):
    assert check_edition(permission, make_member(role), method) is expected


def test_candidate_sees_own_application(user, make_application):
    application = make_application(user)

    allowed, view = check(IsCandidate, user, "GET", application_id=application.id)

    assert allowed is True
    assert view.application == application


def test_candidate_cannot_see_other_application(user, make_member, make_application):
    other = make_member(MENTOR).user
    application = make_application(other)

    with pytest.raises(NotFound):
        check(IsCandidate, user, "GET", application_id=application.id)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (ApplicationStatus.Name.ACCEPTED, True),
        (ApplicationStatus.Name.NEW, False),
        (ApplicationStatus.Name.REJECTED, False),
    ],
)
def test_onboarding_only_for_accepted_candidate(
    user, make_application, status, expected
):
    application = make_application(user, status)

    allowed, _ = check(IsAcceptedCandidate, user, "GET", application_id=application.id)

    assert allowed is expected
