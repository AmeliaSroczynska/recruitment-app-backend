from rest_framework.exceptions import NotFound
from rest_framework.permissions import SAFE_METHODS, BasePermission

from recruitment.models import Application, ApplicationStatus

from .models import Membership, Role

ROLE_INHERITANCE = {
    Role.Name.COORDINATOR: (
        Role.Name.COORDINATOR,
        Role.Name.RECRUITER,
        Role.Name.MENTOR,
    ),
    Role.Name.RECRUITER: (Role.Name.RECRUITER,),
    Role.Name.MENTOR: (Role.Name.MENTOR,),
    Role.Name.OBSERVER: (),
}


def has_role(membership, role):
    return role in ROLE_INHERITANCE[membership.role.name]


class IsEditionMember(BasePermission):
    required_role = None

    def has_permission(self, request, view):
        membership = (
            Membership.objects.select_related("edition", "role")
            .filter(edition_id=view.kwargs["edition_id"], user=request.user)
            .first()
        )
        if membership is None:
            raise NotFound
        view.membership = membership
        view.edition = membership.edition
        if request.method in SAFE_METHODS:
            return True
        if self.required_role is None:
            return membership.role.name != Role.Name.OBSERVER
        return has_role(membership, self.required_role)


class IsCoordinator(IsEditionMember):
    required_role = Role.Name.COORDINATOR


class IsRecruiter(IsEditionMember):
    required_role = Role.Name.RECRUITER


class IsMentor(IsEditionMember):
    required_role = Role.Name.MENTOR


class IsCandidate(BasePermission):
    def has_permission(self, request, view):
        application = (
            Application.objects.select_related("status", "form__edition")
            .filter(pk=view.kwargs["application_id"], user=request.user)
            .first()
        )
        if application is None:
            raise NotFound
        view.application = application
        return True


class IsAcceptedCandidate(IsCandidate):
    def has_permission(self, request, view):
        super().has_permission(request, view)
        return view.application.status.name == ApplicationStatus.Name.ACCEPTED
