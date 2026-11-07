import uuid
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils.deconstruct import deconstructible

MAX_FILE_SIZE = 4 * 1024 * 1024
IMAGE_EXTENSIONS = ["jpg", "jpeg", "png", "webp"]
DOCUMENT_EXTENSIONS = ["pdf", "docx"]
EXTENSION_MESSAGE = "Dozwolone formaty: %(allowed_extensions)s."


@deconstructible
class RandomFileName:
    def __init__(self, folder):
        self.folder = folder

    def __call__(self, instance, filename):
        extension = Path(filename).suffix.lower()
        return f"{self.folder}/{uuid.uuid4().hex}{extension}"


def validate_file_size(file):
    if file.size > MAX_FILE_SIZE:
        raise ValidationError("Plik może mieć najwyżej 4 MB.")


validate_image = FileExtensionValidator(IMAGE_EXTENSIONS, EXTENSION_MESSAGE)
validate_image_or_document = FileExtensionValidator(
    IMAGE_EXTENSIONS + DOCUMENT_EXTENSIONS, EXTENSION_MESSAGE
)
IMAGE_VALIDATORS = [validate_file_size, validate_image]
FILE_VALIDATORS = [validate_file_size, validate_image_or_document]


def get_file_url(file):
    return file.url if file else None


def replace_file(instance, field_name, new_file):
    old_file = getattr(instance, field_name)
    old_name = old_file.name if old_file else None
    setattr(instance, field_name, new_file or None)
    instance.save(update_fields=[field_name])
    new_name = getattr(instance, field_name).name
    if old_name and old_name != new_name:
        old_file.storage.delete(old_name)


def delete_files(files):
    for file in files:
        file.storage.delete(file.name)
