from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Survey",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=180)),
                (
                    "slug",
                    models.SlugField(
                        help_text="Stable public identifier used in API URLs.",
                        max_length=140,
                        unique=True,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                (
                    "thank_you_message",
                    models.CharField(
                        blank=True,
                        default="Thanks for your response.",
                        max_length=240,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("published", "Published"),
                            ("closed", "Closed"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("starts_at", models.DateTimeField(blank=True, null=True)),
                ("ends_at", models.DateTimeField(blank=True, null=True)),
                ("allow_multiple_responses", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["-updated_at", "title"],
            },
        ),
        migrations.CreateModel(
            name="SurveyQuestion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("prompt", models.CharField(max_length=280)),
                ("slug", models.SlugField(blank=True, max_length=140)),
                ("help_text", models.CharField(blank=True, max_length=240)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("short_text", "Short text"),
                            ("long_text", "Long text"),
                            ("single_choice", "Single choice"),
                            ("multiple_choice", "Multiple choice"),
                            ("rating", "Rating"),
                            ("yes_no", "Yes/No"),
                        ],
                        default="short_text",
                        max_length=30,
                    ),
                ),
                ("is_required", models.BooleanField(default=True)),
                ("position", models.PositiveIntegerField(default=0)),
                ("min_value", models.IntegerField(blank=True, default=1, null=True)),
                ("max_value", models.IntegerField(blank=True, default=5, null=True)),
                (
                    "survey",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="questions",
                        to="surveys.survey",
                    ),
                ),
            ],
            options={
                "ordering": ["position", "id"],
                "unique_together": {("survey", "slug")},
            },
        ),
        migrations.CreateModel(
            name="SurveyChoice",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("label", models.CharField(max_length=180)),
                ("value", models.SlugField(blank=True, max_length=140)),
                ("position", models.PositiveIntegerField(default=0)),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="choices",
                        to="surveys.surveyquestion",
                    ),
                ),
            ],
            options={
                "ordering": ["position", "id"],
                "unique_together": {("question", "value")},
            },
        ),
        migrations.CreateModel(
            name="SurveyResponse",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("respondent_email", models.EmailField(blank=True, max_length=254)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=255)),
                ("submitted_at", models.DateTimeField(auto_now_add=True)),
                (
                    "survey",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="responses",
                        to="surveys.survey",
                    ),
                ),
            ],
            options={
                "ordering": ["-submitted_at"],
            },
        ),
        migrations.CreateModel(
            name="SurveyAnswer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("value", models.JSONField(blank=True, default=dict)),
                (
                    "question",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="answers",
                        to="surveys.surveyquestion",
                    ),
                ),
                (
                    "response",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="answers",
                        to="surveys.surveyresponse",
                    ),
                ),
                (
                    "selected_choices",
                    models.ManyToManyField(
                        blank=True,
                        related_name="answers",
                        to="surveys.surveychoice",
                    ),
                ),
            ],
            options={
                "ordering": ["question__position", "id"],
                "unique_together": {("response", "question")},
            },
        ),
    ]
