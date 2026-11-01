from django.urls import path

from .views import CsrfView, LoginView, LogoutView, MeView, RequestCodeView

urlpatterns = [
    path("csrf/", CsrfView.as_view()),
    path("code/", RequestCodeView.as_view()),
    path("login/", LoginView.as_view()),
    path("me/", MeView.as_view()),
    path("logout/", LogoutView.as_view()),
]
