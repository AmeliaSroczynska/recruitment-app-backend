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

    @extend_schema(responses={200: OrganizationSerializer})
    def get(self, request, edition_id):
        return Response(OrganizationSerializer(self.edition.organization).data)

    @extend_schema(
        request=OrganizationSerializer, responses={200: OrganizationSerializer}
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

    @extend_schema(responses={200: EditionSerializer(many=True)})
    def get(self, request, edition_id):
        editions = self.edition.organization.editions.order_by("-id")
        return Response(EditionSerializer(editions, many=True).data)

    @extend_schema(request=EditionSerializer, responses={201: EditionSerializer})
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

    @extend_schema(responses={200: EditionSerializer})
    def get(self, request, edition_id):
        return Response(EditionSerializer(self.edition).data)

    @extend_schema(request=EditionSerializer, responses={200: EditionSerializer})
    def patch(self, request, edition_id):
        serializer = EditionSerializer(self.edition, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
