from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import IsCoordinator
from .serializers import (
    CreatedOrganizationSerializer,
    EditionSerializer,
    OrganizationCreateSerializer,
    OrganizationSerializer,
)
from .services import create_edition, create_organization


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
