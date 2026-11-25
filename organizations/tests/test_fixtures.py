from organizations.models import Role


def test_make_member_creates_membership_with_role(make_member, edition):
    membership = make_member(Role.Name.RECRUITER)

    assert membership.edition == edition
    assert membership.role.name == Role.Name.RECRUITER
