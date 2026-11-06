from django.db.models import Max

from organizations.services import generate_slug

from .models import Form, FormQuestion


def get_or_create_form(edition):
    form = Form.objects.filter(edition=edition).first()
    if form is not None:
        return form
    return Form.objects.create(
        edition=edition,
        title=edition.name,
        slug=generate_slug(f"{edition.organization.slug}-{edition.name}", Form),
    )


def create_question(form, **data):
    last_position = form.questions.aggregate(Max("position"))["position__max"]
    position = 0 if last_position is None else last_position + 1
    return FormQuestion.objects.create(form=form, position=position, **data)


def delete_question(question):
    question.is_deleted = True
    question.save(update_fields=["is_deleted"])
