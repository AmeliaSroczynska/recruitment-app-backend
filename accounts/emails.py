from django.conf import settings
from django.core.mail import send_mail


def send_login_code(email, code):
    minutes = settings.LOGIN_CODE_LIFETIME_MINUTES
    send_mail(
        subject=f"Twój kod logowania: {code}",
        message=(
            f"Twój kod logowania do Aplikacji do rekrutacji i wdrożenia w organizacji studenckiej, do której chcesz się dostać to: {code}\n\n"
            f"Kod jest ważny przez {minutes} minut i działa tylko raz.\n"
            "Jeśli nie próbujesz się zalogować, zignoruj tę wiadomość."
        ),
        from_email=None,
        recipient_list=[email],
    )
