# dg-surv

A Django survey API service with an admin panel for building surveys and public
JSON endpoints for anonymous responses.

## What is included

- Welcome page at `/`
- Browser documentation at `/docs/`
- Modern Django admin styling for survey management
- Public survey schema API
- Anonymous response submission API
- Built-in validation for text, choice, rating, and yes/no answers
- CORS headers for `/api/`
- Django tests for core API behavior

## Setup

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
- Documentation: `http://127.0.0.1:8000/docs/`
- Admin panel: `http://127.0.0.1:8000/admin/`
- API index: `http://127.0.0.1:8000/api/surveys/`

## Creating a survey

1. Create a survey in the admin panel.
2. Add questions inline on the survey page.
3. For single-choice or multiple-choice questions, open the question record and
   add choices.
4. Set the survey status to `Published`.

Supported question types:

- `short_text`
- `long_text`
- `single_choice`
- `multiple_choice`
- `rating`
- `yes_no`

## Public API

List published surveys:

```http
GET /api/surveys/
```

Read a survey schema:

```http
GET /api/surveys/customer-feedback/
```

Submit a response without authentication:

```http
POST /api/surveys/customer-feedback/responses/
Content-Type: application/json

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

`answers` can also be an object keyed by question slug:

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

## Documentation

Detailed API documentation is available in two places:

- Browser page: `http://127.0.0.1:8000/docs/`
- Markdown guide: [docs/API.md](docs/API.md)

## Configuration

Environment variables:

- `DJANGO_SECRET_KEY`: required for production deployments.
- `DJANGO_DEBUG`: set to `0` in production.
- `DJANGO_ALLOWED_HOSTS`: comma-separated host list. Defaults to `*`.
- `SURVEY_API_CORS_ORIGINS`: comma-separated origin list for `/api/`.
  Defaults to `*`.

Run tests:

```bash
python manage.py test
```

## Project layout

```text
survey_service/        Django project settings and root URLs
surveys/               Survey models, admin, API views, tests, middleware
templates/             Welcome page, docs page, admin override
static/surveys/        Admin and public page styles/assets
docs/API.md            Markdown API guide
```
