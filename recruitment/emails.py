from django.conf import settings
from django.core.mail import send_mail

WEEKDAYS = (
    "poniedziałek",
    "wtorek",
    "środa",
    "czwartek",
    "piątek",
    "sobota",
    "niedziela",
)
MONTHS = (
    "stycznia",
    "lutego",
    "marca",
    "kwietnia",
    "maja",
    "czerwca",
    "lipca",
    "sierpnia",
    "września",
    "października",
    "listopada",
    "grudnia",
)


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


def send_interview_invitation(application):
    user = application.user
    edition = application.form.edition
    send_mail(
        subject=f"Zaproszenie na rozmowę - {edition.organization.name}",
        message=(
            f"Cześć {user.first_name}!\n\n"
            f"Zapraszamy Cię na rozmowę w organizacji {edition.organization.name}. "
            "Zaloguj się do panelu kandydata i zaznacz w kalendarzu, kiedy "
            "możesz. Termin wybierzemy z Twojej dostępności:\n"
            f"{settings.FRONTEND_URL}/candidate/{edition.id}\n\n"
            f"Zaloguj się adresem {user.email}, a wyślemy Ci jednorazowy kod."
        ),
        from_email=None,
        recipient_list=[user.email],
        fail_silently=True,
    )


def format_term(date, start_time, end_time):
    return (
        f"{WEEKDAYS[date.weekday()]}, {date.day} {MONTHS[date.month - 1]}, "
        f"{start_time:%H:%M}-{end_time:%H:%M}"
    )


def send_interview_scheduled(interview):
    application = interview.application
    user = application.user
    edition = application.form.edition
    info = f"\n\n{edition.interview_info}" if edition.interview_info else ""
    send_mail(
        subject=f"Termin rozmowy - {edition.organization.name}",
        message=(
            f"Cześć {user.first_name}!\n\n"
            "Wybraliśmy termin Twojej rozmowy: "
            f"{format_term(interview.date, interview.start_time, interview.end_time)}."
            f"{info}\n\n"
            "Szczegóły zobaczysz w panelu kandydata, tam też możesz odwołać "
            f"rozmowę:\n{settings.FRONTEND_URL}/candidate/{edition.id}"
        ),
        from_email=None,
        recipient_list=[user.email],
        fail_silently=True,
    )


def send_interview_cancelled(interview, date, start_time, end_time):
    application = interview.application
    user = application.user
    edition = application.form.edition
    term = format_term(date, start_time, end_time)
    send_mail(
        subject=f"Rozmowa odwołana - {edition.organization.name}",
        message=(
            f"Cześć {user.first_name}!\n\n"
            f"Twoja rozmowa została odwołana (termin: {term}). W panelu kandydata "
            "możesz poprawić swoją dostępność, a my wybierzemy nowy termin:\n"
            f"{settings.FRONTEND_URL}/candidate/{edition.id}"
        ),
        from_email=None,
        recipient_list=[user.email],
        fail_silently=True,
    )
    interviewers = [
        membership.user.email for membership in interview.interviewers.all()
    ]
    if interviewers:
        send_mail(
            subject=f"Rozmowa odwołana - {user.first_name} {user.last_name}",
            message=(
                f"Kandydat {user.first_name} {user.last_name} ({user.email}) "
                f"odwołał rozmowę (termin: {term}). Ta "
                "osoba jest znowu na liście Do umówienia w kalendarzu rozmów:\n"
                f"{settings.FRONTEND_URL}/organization/{edition.id}/calendar"
            ),
            from_email=None,
            recipient_list=interviewers,
            fail_silently=True,
        )
