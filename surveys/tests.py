from django.contrib.staticfiles import finders
from django.test import Client, TestCase

from .models import Survey, SurveyAnswer, SurveyChoice, SurveyQuestion, SurveyResponse


class SurveyApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.survey = Survey.objects.create(
            title="Customer Feedback",
            slug="customer-feedback",
            status=Survey.Status.PUBLISHED,
            thank_you_message="Thanks for helping us improve.",
        )
        self.name_question = SurveyQuestion.objects.create(
            survey=self.survey,
            prompt="What is your name?",
            slug="name",
            type=SurveyQuestion.Type.SHORT_TEXT,
            position=1,
        )
        self.mood_question = SurveyQuestion.objects.create(
            survey=self.survey,
            prompt="How was your experience?",
            slug="experience",
            type=SurveyQuestion.Type.SINGLE_CHOICE,
            position=2,
        )
        self.good_choice = SurveyChoice.objects.create(
            question=self.mood_question,
            label="Good",
            value="good",
            position=1,
        )
        SurveyChoice.objects.create(
            question=self.mood_question,
            label="Bad",
            value="bad",
            position=2,
        )

    def test_lists_public_surveys(self):
        Survey.objects.create(title="Draft Survey", slug="draft", status=Survey.Status.DRAFT)

        response = self.client.get("/api/surveys/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["results"]), 1)
        self.assertEqual(payload["results"][0]["slug"], "customer-feedback")

    def test_returns_survey_detail(self):
        response = self.client.get("/api/surveys/customer-feedback/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["title"], "Customer Feedback")
        self.assertEqual(len(payload["questions"]), 2)
        self.assertEqual(payload["questions"][1]["choices"][0]["value"], "good")

    def test_accepts_anonymous_response(self):
        response = self.client.post(
            "/api/surveys/customer-feedback/responses/",
            data={
                "respondent_email": "person@example.com",
                "metadata": {"source": "test"},
                "answers": [
                    {"question": "name", "value": "Alex"},
                    {"question": "experience", "choice": "good"},
                ],
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["thank_you_message"], "Thanks for helping us improve.")
        self.assertEqual(SurveyResponse.objects.count(), 1)
        self.assertEqual(SurveyAnswer.objects.count(), 2)
        choice_answer = SurveyAnswer.objects.get(question=self.mood_question)
        self.assertEqual(list(choice_answer.selected_choices.all()), [self.good_choice])

    def test_rejects_missing_required_answer(self):
        response = self.client.post(
            "/api/surveys/customer-feedback/responses/",
            data={"answers": [{"question": "name", "value": "Alex"}]},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("experience", response.json()["errors"])

    def test_rejects_closed_survey_response(self):
        self.survey.status = Survey.Status.CLOSED
        self.survey.save(update_fields=["status"])

        response = self.client.post(
            "/api/surveys/customer-feedback/responses/",
            data={"answers": []},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)


class SitePageTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_welcome_page_renders(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Survey Studio")
        self.assertContains(response, "/api/surveys/")

    def test_docs_page_renders(self):
        response = self.client.get("/docs/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Survey Studio Docs")
        self.assertContains(response, "POST")

    def test_public_static_assets_are_discoverable(self):
        self.assertIsNotNone(finders.find("surveys/admin.css"))
        self.assertIsNotNone(finders.find("surveys/site.css"))
        self.assertIsNotNone(finders.find("surveys/survey-flow.svg"))

    def test_admin_theme_css_loads_after_page_css(self):
        response = self.client.get("/admin/login/")
        content = response.content.decode()

        self.assertLess(
            content.index("/static/admin/css/login.css"),
            content.index("/static/surveys/admin.css"),
        )
