# Survey Studio API Guide

Survey Studio is a Django service for creating surveys in admin and collecting
public responses through JSON endpoints.

## Local Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open:

- Welcome page: `http://127.0.0.1:8000/`
- Documentation page: `http://127.0.0.1:8000/docs/`
- Admin panel: `http://127.0.0.1:8000/admin/`
- Survey API: `http://127.0.0.1:8000/api/surveys/`

## Survey Workflow

1. Sign in to Django admin.
2. Create a survey.
3. Add questions inline.
4. Add choices to single-choice and multiple-choice questions.
5. Publish the survey.
6. Fetch the survey schema from the API.
7. Submit public responses to the response endpoint.

## Question Types

- `short_text`
- `long_text`
- `single_choice`
- `multiple_choice`
- `rating`
- `yes_no`

## Endpoints

### List published surveys

```http
GET /api/surveys/
```

Example response:

```json
{
  "results": [
    {
      "id": 1,
      "title": "Customer Feedback",
      "slug": "customer-feedback",
      "description": "Monthly product feedback",
      "thank_you_message": "Thanks for your response.",
      "starts_at": null,
      "ends_at": null,
      "url": "http://127.0.0.1:8000/api/surveys/customer-feedback/",
      "response_url": "http://127.0.0.1:8000/api/surveys/customer-feedback/responses/"
    }
  ]
}
```

### Read a survey schema

```http
GET /api/surveys/customer-feedback/
```

Example response:

```json
{
  "id": 1,
  "title": "Customer Feedback",
  "slug": "customer-feedback",
  "description": "Monthly product feedback",
  "thank_you_message": "Thanks for your response.",
  "starts_at": null,
  "ends_at": null,
  "url": "http://127.0.0.1:8000/api/surveys/customer-feedback/",
  "response_url": "http://127.0.0.1:8000/api/surveys/customer-feedback/responses/",
  "questions": [
    {
      "id": 10,
      "slug": "experience",
      "prompt": "How was your experience?",
      "help_text": "",
      "type": "single_choice",
      "required": true,
      "position": 1,
      "choices": [
        {
          "id": 100,
          "label": "Good",
          "value": "good",
          "position": 1
        }
      ]
    }
  ]
}
```

### Submit a response

```http
POST /api/surveys/customer-feedback/responses/
Content-Type: application/json
```

```json
{
  "respondent_email": "person@example.com",
  "metadata": {
    "source": "website"
  },
  "answers": [
    {
      "question": "name",
      "value": "Alex"
    },
    {
      "question": "experience",
      "choice": "good"
    }
  ]
}
```

Successful response:

```json
{
  "id": 24,
  "survey": "customer-feedback",
  "submitted_at": "2026-05-02T12:00:00+00:00",
  "thank_you_message": "Thanks for your response."
}
```

## Answer Formats

List style:

```json
{
  "answers": [
    {
      "question": "name",
      "value": "Alex"
    }
  ]
}
```

Object style:

```json
{
  "answers": {
    "name": "Alex",
    "score": 5,
    "subscribe": true
  }
}
```

Choice answers accept either the choice `value` or choice `id`.

## Validation

- Required questions must be answered.
- Unknown question slugs are rejected.
- Duplicate answers for the same question are rejected.
- Rating answers must be numeric and inside the configured range.
- Yes/no answers accept booleans or `yes`, `no`, `true`, `false`, `1`, `0`.
- Closed, draft, expired, or not-yet-started surveys reject responses.

## Environment Variables

- `DJANGO_SECRET_KEY`: required for production deployments.
- `DJANGO_DEBUG`: set to `0` in production.
- `DJANGO_ALLOWED_HOSTS`: comma-separated host list. Defaults to `*`.
- `SURVEY_API_CORS_ORIGINS`: comma-separated origin list for `/api/`.
