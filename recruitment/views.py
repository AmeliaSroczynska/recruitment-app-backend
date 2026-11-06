from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from organizations.permissions import IsRecruiter

from .serializers import FormSerializer
from .services import get_or_create_form


class FormDetailView(APIView):
    permission_classes = (IsAuthenticated, IsRecruiter)

    @extend_schema(
        tags=["Formularz"],
        summary="Ustawienia formularza",
        description=(
            "Formularz zgłoszeniowy edycji. Każda edycja ma jeden formularz, "
            "który tworzy się sam przy pierwszym wejściu. Widzi każdy członek edycji."
        ),
        responses={200: FormSerializer},
    )
    def get(self, request, edition_id):
        return Response(FormSerializer(get_or_create_form(self.edition)).data)

    @extend_schema(
        tags=["Formularz"],
        summary="Zmień ustawienia formularza",
        description=(
            "Tytuł, opis, adres (slug) i przyjmowanie zgłoszeń. Rekruter i koordynator."
        ),
        request=FormSerializer,
        responses={200: FormSerializer},
    )
    def patch(self, request, edition_id):
        serializer = FormSerializer(
            get_or_create_form(self.edition), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
