from django.conf import settings
from django.core.mail import send_mail


def send_application_received(application):
    user = application.user
    organization = application.form.edition.organization.name
    send_mail(
        subject=f"Dostaliśmy Twoje zgłoszenie do organizacji {organization}",
        message=(
            f"Cześć {user.first_name}!\n\n"
            f"Dziękujemy za wysłanie zgłoszenia do organizacji {organization}. "
            "Zespół przejrzy je i da Ci znać o kolejnych krokach.\n\n"
            "Status zgłoszenia sprawdzisz w panelu kandydata:\n"
            f"{settings.FRONTEND_URL}/login/candidate\n\n"
            f"Zaloguj się adresem {user.email}, a wyślemy Ci jednorazowy kod."
        ),
        from_email=None,
        recipient_list=[user.email],
        fail_silently=True,
    )


def send_application_accepted(application):
    user = application.user
    edition = application.form.edition
    send_mail(
        subject=f"Witamy w organizacji {edition.organization.name}!",
        message=(
            f"Cześć {user.first_name}!\n\n"
            f"Z radością informujemy, że zostałeś przyjęty do organizacji "
            f"{edition.organization.name}. W panelu kandydata czeka na Ciebie "
            "wdrożenie:\n"
            f"{settings.FRONTEND_URL}/candidate/{edition.id}/onboarding\n\n"
            f"Zaloguj się adresem {user.email}, a wyślemy Ci jednorazowy kod."
        ),
        from_email=None,
        recipient_list=[user.email],
        fail_silently=True,
    )
