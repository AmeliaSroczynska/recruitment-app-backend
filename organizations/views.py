from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import CreatedOrganizationSerializer, OrganizationCreateSerializer
from .services import create_organization


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
