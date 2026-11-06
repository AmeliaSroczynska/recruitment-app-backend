from django.contrib.auth import login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .emails import send_login_code
from .serializers import LoginSerializer, MeSerializer, RequestCodeSerializer
from .services import create_login_code, verify_login_code

DetailSerializer = inline_serializer("Detail", {"detail": serializers.CharField()})


@method_decorator(ensure_csrf_cookie, name="get")
class CsrfView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        tags=["Logowanie"],
        summary="Pobierz token CSRF",
        description="Ustawia ciasteczko csrftoken. Frontend woła to przed pierwszym POST.",
        responses={204: None},
    )
    def get(self, request):
        return Response(status=status.HTTP_204_NO_CONTENT)


class RequestCodeView(APIView):
    permission_classes = (AllowAny,)
    throttle_scope = "auth_code"

    @extend_schema(
        tags=["Logowanie"],
        summary="Wyślij kod logowania",
        description="Wysyła 6-cyfrowy kod na podany e-mail. Jeśli konta nie ma, zakłada je.",
        request=RequestCodeSerializer,
        responses={200: DetailSerializer},
    )
    def post(self, request):
        serializer = RequestCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user, code = create_login_code(serializer.validated_data["email"])
        send_login_code(user.email, code)
        return Response({"detail": "Wysłaliśmy kod na podany adres e-mail."})


class LoginView(APIView):
    permission_classes = (AllowAny,)
    throttle_scope = "auth_login"

    @extend_schema(
        tags=["Logowanie"],
        summary="Zaloguj się kodem",
        description="Sprawdza kod z maila i loguje. Zwraca dane konta.",
        request=LoginSerializer,
        responses={200: MeSerializer, 400: DetailSerializer},
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = verify_login_code(
            serializer.validated_data["email"], serializer.validated_data["code"]
        )
        if user is None or not user.is_active:
            return Response(
                {"detail": "Kod jest nieprawidłowy albo wygasł."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        login(request, user)
        return Response(MeSerializer(user).data)


class MeView(APIView):
    @extend_schema(
        tags=["Logowanie"],
        summary="Moje konto",
        description="Dane zalogowanej osoby: członkostwa w edycjach i zgłoszenia.",
        responses={200: MeSerializer},
    )
    def get(self, request):
        return Response(MeSerializer(request.user).data)


class LogoutView(APIView):
    @extend_schema(
        tags=["Logowanie"],
        summary="Wyloguj się",
        request=None,
        responses={204: None},
    )
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)
