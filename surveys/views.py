import json

from django.core.exceptions import ValidationError
from django.core.validators import validate_email, validate_ipv46_address
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from .models import Survey, SurveyAnswer, SurveyQuestion, SurveyResponse


@require_GET
def survey_list(request):
    surveys = Survey.objects.public()
    return JsonResponse(
        {
            "results": [
                serialize_survey(request, survey, include_questions=False)
                for survey in surveys
            ]
        }
    )


@require_GET
def survey_detail(request, slug):
    survey = get_object_or_404(
        Survey.objects.public().prefetch_related("questions__choices"),
        slug=slug,
    )
    return JsonResponse(serialize_survey(request, survey, include_questions=True))


@csrf_exempt
@require_http_methods(["POST"])
def submit_survey_response(request, slug):
    survey = get_object_or_404(
        Survey.objects.prefetch_related("questions__choices"),
        slug=slug,
    )
    accepts_responses, reason = survey.accepts_responses()
    if not accepts_responses:
        return JsonResponse({"detail": reason}, status=403)

    payload, error = parse_json_body(request)
    if error:
        return JsonResponse({"detail": error}, status=400)

    respondent_email = str(payload.get("respondent_email", "")).strip()
    email_error = validate_optional_email(respondent_email)
    if email_error:
        return JsonResponse({"errors": {"respondent_email": email_error}}, status=400)

    metadata = payload.get("metadata") or {}
    if not isinstance(metadata, dict):
        return JsonResponse({"errors": {"metadata": "Metadata must be an object."}}, status=400)

    if not survey.allow_multiple_responses and respondent_email:
        already_responded = survey.responses.filter(respondent_email=respondent_email).exists()
        if already_responded:
            return JsonResponse(
                {"detail": "This email has already submitted a response."},
                status=409,
            )

    answers, errors = validate_answers(survey, payload.get("answers"))
    if errors:
        return JsonResponse({"errors": errors}, status=400)

    with transaction.atomic():
        response = SurveyResponse.objects.create(
            survey=survey,
            respondent_email=respondent_email,
            metadata=metadata,
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:255],
        )
        for answer_data in answers:
            answer = SurveyAnswer.objects.create(
                response=response,
                question=answer_data["question"],
                value=answer_data["value"],
            )
            if answer_data["choices"]:
                answer.selected_choices.set(answer_data["choices"])

    return JsonResponse(
        {
            "id": response.pk,
            "survey": survey.slug,
            "submitted_at": response.submitted_at.isoformat(),
            "thank_you_message": survey.thank_you_message,
        },
        status=201,
    )


def serialize_survey(request, survey, include_questions):
    response_url = reverse("survey-response-submit", args=[survey.slug])
    detail_url = reverse("survey-detail", args=[survey.slug])
    data = {
        "id": survey.pk,
        "title": survey.title,
        "slug": survey.slug,
        "description": survey.description,
        "thank_you_message": survey.thank_you_message,
        "starts_at": serialize_datetime(survey.starts_at),
        "ends_at": serialize_datetime(survey.ends_at),
        "url": request.build_absolute_uri(detail_url),
        "response_url": request.build_absolute_uri(response_url),
    }
    if include_questions:
        data["questions"] = [serialize_question(question) for question in survey.questions.all()]
    return data


def serialize_question(question):
    data = {
        "id": question.pk,
        "slug": question.slug,
        "prompt": question.prompt,
        "help_text": question.help_text,
        "type": question.type,
        "required": question.is_required,
        "position": question.position,
    }
    if question.type == SurveyQuestion.Type.RATING:
        data["min_value"] = question.min_value
        data["max_value"] = question.max_value
    if question.type in {
        SurveyQuestion.Type.SINGLE_CHOICE,
        SurveyQuestion.Type.MULTIPLE_CHOICE,
    }:
        data["choices"] = [serialize_choice(choice) for choice in question.choices.all()]
    else:
        data["choices"] = []
    return data


def serialize_choice(choice):
    return {
        "id": choice.pk,
        "label": choice.label,
        "value": choice.value,
        "position": choice.position,
    }


def serialize_datetime(value):
    if value is None:
        return None
    return value.isoformat()


def parse_json_body(request):
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None, "Request body must be valid JSON."
    if not isinstance(payload, dict):
        return None, "Request body must be a JSON object."
    return payload, None


def validate_optional_email(email):
    if not email:
        return None
    try:
        validate_email(email)
    except ValidationError:
        return "Enter a valid email address."
    return None


def validate_answers(survey, raw_answers):
    normalized_answers, normalize_error = normalize_answers(raw_answers)
    if normalize_error:
        return [], {"answers": normalize_error}

    questions = list(survey.questions.all())
    question_by_lookup = {}
    for question in questions:
        question_by_lookup[str(question.pk)] = question
        question_by_lookup[question.slug] = question

    validated = []
    errors = {}
    answered_question_ids = set()

    for index, answer_payload in enumerate(normalized_answers):
        if not isinstance(answer_payload, dict):
            errors[f"answers[{index}]"] = "Each answer must be an object."
            continue

        question_lookup = answer_payload.get("question", answer_payload.get("question_id"))
        question = question_by_lookup.get(str(question_lookup))
        if question is None:
            errors[f"answers[{index}].question"] = "Unknown question."
            continue
        if question.pk in answered_question_ids:
            errors[question.slug] = "Question answered more than once."
            continue

        answer_value, selected_choices, error = validate_answer_value(question, answer_payload)
        if error:
            errors[question.slug] = error
            continue
        if answer_value is None:
            continue

        answered_question_ids.add(question.pk)
        validated.append(
            {
                "question": question,
                "value": answer_value,
                "choices": selected_choices,
            }
        )

    for question in questions:
        if question.is_required and question.pk not in answered_question_ids:
            errors.setdefault(question.slug, "This question is required.")

    return validated, errors


def normalize_answers(raw_answers):
    if raw_answers is None:
        return [], None
    if isinstance(raw_answers, dict):
        return [
            {"question": question, "value": value}
            for question, value in raw_answers.items()
        ], None
    if isinstance(raw_answers, list):
        return raw_answers, None
    return None, "Answers must be a list or an object keyed by question slug."


def validate_answer_value(question, answer_payload):
    if question.type in {SurveyQuestion.Type.SHORT_TEXT, SurveyQuestion.Type.LONG_TEXT}:
        return validate_text_answer(question, answer_payload)
    if question.type == SurveyQuestion.Type.SINGLE_CHOICE:
        return validate_single_choice_answer(question, answer_payload)
    if question.type == SurveyQuestion.Type.MULTIPLE_CHOICE:
        return validate_multiple_choice_answer(question, answer_payload)
    if question.type == SurveyQuestion.Type.RATING:
        return validate_rating_answer(question, answer_payload)
    if question.type == SurveyQuestion.Type.YES_NO:
        return validate_yes_no_answer(question, answer_payload)
    return None, [], "Unsupported question type."


def validate_text_answer(question, answer_payload):
    raw_value = answer_payload.get("value", answer_payload.get("text"))
    if is_empty(raw_value):
        if question.is_required:
            return None, [], "This question is required."
        return None, [], None
    if not isinstance(raw_value, str):
        return None, [], "Answer must be text."
    return {"text": raw_value.strip()}, [], None


def validate_single_choice_answer(question, answer_payload):
    raw_choice = answer_payload.get("choice", answer_payload.get("value"))
    if is_empty(raw_choice):
        if question.is_required:
            return None, [], "Select one choice."
        return None, [], None

    choice, error = resolve_choice(question, raw_choice)
    if error:
        return None, [], error
    return {"choice": choice.value}, [choice], None


def validate_multiple_choice_answer(question, answer_payload):
    raw_choices = answer_payload.get("choices", answer_payload.get("value"))
    if raw_choices in (None, "") or raw_choices == []:
        if question.is_required:
            return None, [], "Select at least one choice."
        return None, [], None
    if not isinstance(raw_choices, list):
        return None, [], "Answer must be a list of choices."

    selected_choices = []
    seen_choice_ids = set()
    for raw_choice in raw_choices:
        choice, error = resolve_choice(question, raw_choice)
        if error:
            return None, [], error
        if choice.pk not in seen_choice_ids:
            selected_choices.append(choice)
            seen_choice_ids.add(choice.pk)

    if question.is_required and not selected_choices:
        return None, [], "Select at least one choice."

    return {"choices": [choice.value for choice in selected_choices]}, selected_choices, None


def validate_rating_answer(question, answer_payload):
    raw_value = answer_payload.get("value", answer_payload.get("rating"))
    if is_empty(raw_value):
        if question.is_required:
            return None, [], "Rating is required."
        return None, [], None
    if isinstance(raw_value, bool):
        return None, [], "Rating must be a number."
    try:
        rating = int(raw_value)
    except (TypeError, ValueError):
        return None, [], "Rating must be a number."

    min_value = question.min_value if question.min_value is not None else 1
    max_value = question.max_value if question.max_value is not None else 5
    if rating < min_value or rating > max_value:
        return None, [], f"Rating must be between {min_value} and {max_value}."
    return {"rating": rating}, [], None


def validate_yes_no_answer(question, answer_payload):
    raw_value = answer_payload.get("value", answer_payload.get("answer"))
    if is_empty(raw_value):
        if question.is_required:
            return None, [], "Answer yes or no."
        return None, [], None
    if isinstance(raw_value, bool):
        return {"answer": raw_value}, [], None
    if isinstance(raw_value, str):
        normalized_value = raw_value.strip().lower()
        if normalized_value in {"true", "yes", "1"}:
            return {"answer": True}, [], None
        if normalized_value in {"false", "no", "0"}:
            return {"answer": False}, [], None
    return None, [], "Answer must be true or false."


def resolve_choice(question, raw_choice):
    choices = list(question.choices.all())
    if not choices:
        return None, "This question has no choices configured."

    lookup = str(raw_choice)
    for choice in choices:
        if lookup in {str(choice.pk), choice.value}:
            return choice, None

    allowed_values = ", ".join(choice.value for choice in choices)
    return None, f"Select one of: {allowed_values}."


def is_empty(value):
    return value is None or (isinstance(value, str) and not value.strip())


def get_client_ip(request):
    raw_ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
    ip_address = raw_ip or request.META.get("REMOTE_ADDR")
    if not ip_address:
        return None
    try:
        validate_ipv46_address(ip_address)
    except (TypeError, ValidationError):
        return None
    return ip_address
