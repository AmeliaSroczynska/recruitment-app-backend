from django.core.management.base import BaseCommand

from recruitment.services import delete_expired_editions


class Command(BaseCommand):
    help = "Usuwa nieaktywne edycje naboru utworzone ponad 2 lata temu."

    def handle(self, *args, **options):
        count = delete_expired_editions()
        self.stdout.write(f"Usunięte edycje: {count}")
