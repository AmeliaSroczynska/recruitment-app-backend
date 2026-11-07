from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.files import replace_file

from .models import Role
from .permissions import IsCoordinator
from .serializers import (
    CreatedOrganizationSerializer,
    EditionSerializer,
    MemberCreateSerializer,
    MemberSerializer,
    OrganizationCreateSerializer,
    OrganizationLogoSerializer,
    OrganizationSerializer,
    RoleSerializer,
)
from .services import (
    add_member,
    change_role,
    create_edition,
    create_organization,
    delete_edition,
    remove_member,
)


class OrganizationCreateView(APIView):
    @extend_schema(
        tags=["Organizacja"],
        summary="Utwórz organizację",
        description="Tworzy organizację, jej pierwszą edycję i robi Cię w niej koordynatorem.",
        request=OrganizationCreateSerializer,
        responses={201: CreatedOrganizationSerializer},
    )
    def post(self, request):
        serializer = OrganizationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization, edition = create_organization(
            request.user,
            serializer.validated_data["name"],
            serializer.validated_data.get("contact_email", request.user.email),
        )
        organization.edition_id = edition.id
        return Response(
            CreatedOrganizationSerializer(organization).data,
            status=status.HTTP_201_CREATED,
        )


class OrganizationDetailView(APIView):
    permission_classes = (IsAuthenticated, IsCoordinator)

    @extend_schema(
        tags=["Organizacja"],
        summary="Dane organizacji",
        description="Organizacja, do której należy edycja. Widzi każdy członek edycji.",
        responses={200: OrganizationSerializer},
    )
    def get(self, request, edition_id):
        return Response(OrganizationSerializer(self.edition.organization).data)

    @extend_schema(
        tags=["Organizacja"],
        summary="Zmień dane organizacji",
        description="Nazwa, e-mail kontaktowy, adres (slug). Tylko koordynator.",
        request=OrganizationSerializer,
        responses={200: OrganizationSerializer},
    )
    def patch(self, request, edition_id):
        serializer = OrganizationSerializer(
            self.edition.organization, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)



class OrganizationLogoView(APIView):
    permission_classes = (IsAuthenticated, IsCoordinator)
    parser_classes = (MultiPartParser,)

    @extend_schema(
        tags=["Organizacja"],
        summary="Wgraj logo organizacji",
        description="Plik w polu logo (jpg, png, webp, do 4 MB). Zastępuje stare logo. Tylko koordynator.",
        request={"multipart/form-data": OrganizationLogoSerializer},
        responses={200: OrganizationSerializer},
    )
    def post(self, request, edition_id):
        serializer = OrganizationLogoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        organization = self.edition.organization
        replace_file(organization, "logo", serializer.validated_data["logo"])
        return Response(OrganizationSerializer(organization).data)

    @extend_schema(
        tags=["Organizacja"],
        summary="Usuń logo organizacji",
        description="Usuwa logo, w aplikacji wraca pierwsza litera nazwy. Tylko koordynator.",
        responses={200: OrganizationSerializer},
    )
    def delete(self, request, edition_id):
        organization = self.edition.organization
        replace_file(organization, "logo", None)
        return Response(OrganizationSerializer(organization).data)

class EditionListView(APIView):
    permission_classes = (IsAuthenticated, IsCoordinator)

    @extend_schema(
        tags=["Edycje"],
        summary="Lista edycji organizacji",
        description="Wszystkie edycje, najnowsza pierwsza.",
        responses={200: EditionSerializer(many=True)},
    )
    def get(self, request, edition_id):
        editions = self.edition.organization.editions.order_by("-id")
        return Response(EditionSerializer(editions, many=True).data)

    @extend_schema(
        tags=["Edycje"],
        summary="Nowa edycja",
        description="Poprzednia edycja przestaje być aktywna. Nowa startuje pusta, a Ty jesteś w niej koordynatorem. Tylko koordynator.",
        request=EditionSerializer,
        responses={201: EditionSerializer},
    )
    def post(self, request, edition_id):
        serializer = EditionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        edition = create_edition(
            self.edition.organization,
            request.user,
            serializer.validated_data["name"],
        )
        return Response(EditionSerializer(edition).data, status=status.HTTP_201_CREATED)


class EditionDetailView(APIView):
    permission_classes = (IsAuthenticated, IsCoordinator)

    @extend_schema(
        tags=["Edycje"],
        summary="Dane edycji",
        responses={200: EditionSerializer},
    )
    def get(self, request, edition_id):
        return Response(EditionSerializer(self.edition).data)

    @extend_schema(
        tags=["Edycje"],
        summary="Zmień nazwę edycji",
        description="Tylko koordynator.",
        request=EditionSerializer,
        responses={200: EditionSerializer},
    )
    def patch(self, request, edition_id):
        serializer = EditionSerializer(self.edition, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(
        tags=["Edycje"],
        summary="Usuń edycję",
        description=(
            "Tylko koordynator. Usuwa edycję razem ze wszystkim, co w niej jest. "
            "Jedynej edycji organizacji nie da się usunąć. Jeśli usuwana edycja "
            "była aktywna, aktywna staje się najnowsza z pozostałych."
        ),
        responses={204: None},
    )
    def delete(self, request, edition_id):
        delete_edition(self.edition)
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoleListView(APIView):
    @extend_schema(
        tags=["Członkowie"],
        summary="Lista ról",
        description="Role do wyboru przy dodawaniu członka.",
        responses={200: RoleSerializer(many=True)},
    )
    def get(self, request):
        roles = sorted(
            Role.objects.all(), key=lambda role: Role.Name.values.index(role.name)
        )
        return Response(RoleSerializer(roles, many=True).data)


class MemberListView(APIView):
    permission_classes = (IsAuthenticated, IsCoordinator)

    @extend_schema(
        tags=["Członkowie"],
        summary="Lista członków edycji",
        description="Osoby z zespołu i ich role. Widzi każdy członek edycji.",
        responses={200: MemberSerializer(many=True)},
    )
    def get(self, request, edition_id):
        members = self.edition.memberships.select_related("user", "role").order_by(
            "user__email"
        )
        return Response(MemberSerializer(members, many=True).data)

    @extend_schema(
        tags=["Członkowie"],
        summary="Dodaj członka",
        description="Dodaje osobę po e-mailu z wybraną rolą. Jeśli konta nie ma, zakłada je. Tylko koordynator.",
        request=MemberCreateSerializer,
        responses={201: MemberSerializer},
    )
    def post(self, request, edition_id):
        serializer = MemberCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = add_member(
            self.edition,
            serializer.validated_data["email"],
            serializer.validated_data["role"],
        )
        return Response(
            MemberSerializer(membership).data, status=status.HTTP_201_CREATED
        )


class MemberDetailView(APIView):
    permission_classes = (IsAuthenticated, IsCoordinator)

    def get_membership(self, member_id):
        return get_object_or_404(
            self.edition.memberships.select_related("user", "role"), pk=member_id
        )

    @extend_schema(
        tags=["Członkowie"],
        summary="Zmień rolę członka",
        description="Ostatniego koordynatora nie da się zmienić na inną rolę. Tylko koordynator.",
        request=MemberSerializer,
        responses={200: MemberSerializer},
    )
    def patch(self, request, edition_id, member_id):
        membership = self.get_membership(member_id)
        serializer = MemberSerializer(membership, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data.get("role", membership.role)
        return Response(MemberSerializer(change_role(membership, role)).data)

    @extend_schema(
        tags=["Członkowie"],
        summary="Usuń członka z edycji",
        description="Ostatniego koordynatora nie da się usunąć. Tylko koordynator.",
        responses={204: None},
    )
    def delete(self, request, edition_id, member_id):
        remove_member(self.get_membership(member_id))
        return Response(status=status.HTTP_204_NO_CONTENT)
