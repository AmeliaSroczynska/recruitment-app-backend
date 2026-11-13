MAX_ANSWER_LENGTH = 2000


def shorten(text):
    if len(text) <= MAX_ANSWER_LENGTH:
        return text
    return text[:MAX_ANSWER_LENGTH] + "..."


def answer_to_text(answer):
    choices = sorted(answer.selected_choices.all(), key=lambda choice: choice.position)
    if choices:
        return ", ".join(choice.text for choice in choices)
    return shorten((answer.text or "").strip())


def build_application_text(application):
    parts = []
    for answer in application.answers.all():
        text = answer_to_text(answer)
        if text:
            parts.append(f"Pytanie: {answer.question.text}\nOdpowiedź: {text}")
    return "\n\n".join(parts)
