from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify


class SurveyQuerySet(models.QuerySet):
    def public(self):
        now = timezone.now()
        return (
            self.filter(status=Survey.Status.PUBLISHED)
            .filter(Q(starts_at__isnull=True) | Q(starts_at__lte=now))
            .filter(Q(ends_at__isnull=True) | Q(ends_at__gte=now))
        )


class Survey(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        CLOSED = "closed", "Closed"

    title = models.CharField(max_length=180)
    slug = models.SlugField(
        max_length=140,
        unique=True,
        help_text="Stable public identifier used in API URLs.",
    )
    description = models.TextField(blank=True)
    thank_you_message = models.CharField(
        max_length=240,
        blank=True,
        default="Thanks for your response.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    starts_at = models.DateTimeField(blank=True, null=True)
    ends_at = models.DateTimeField(blank=True, null=True)
    allow_multiple_responses = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SurveyQuerySet.as_manager()

    class Meta:
        ordering = ["-updated_at", "title"]

    def __str__(self) -> str:
        return self.title

    def clean(self):
        if self.starts_at and self.ends_at and self.starts_at >= self.ends_at:
            raise ValidationError("The survey start time must be before the end time.")

    def accepts_responses(self):
        now = timezone.now()
        if self.status != self.Status.PUBLISHED:
            return False, "Survey is not published."
        if self.starts_at and self.starts_at > now:
            return False, "Survey has not started yet."
        if self.ends_at and self.ends_at < now:
            return False, "Survey has ended."
        return True, ""


class SurveyQuestion(models.Model):
    class Type(models.TextChoices):
        SHORT_TEXT = "short_text", "Short text"
        LONG_TEXT = "long_text", "Long text"
        SINGLE_CHOICE = "single_choice", "Single choice"
        MULTIPLE_CHOICE = "multiple_choice", "Multiple choice"
        RATING = "rating", "Rating"
        YES_NO = "yes_no", "Yes/No"

    survey = models.ForeignKey(Survey, related_name="questions", on_delete=models.CASCADE)
    prompt = models.CharField(max_length=280)
    slug = models.SlugField(max_length=140, blank=True)
    help_text = models.CharField(max_length=240, blank=True)
    type = models.CharField(
        max_length=30,
        choices=Type.choices,
        default=Type.SHORT_TEXT,
    )
    is_required = models.BooleanField(default=True)
    position = models.PositiveIntegerField(default=0)
    min_value = models.IntegerField(default=1, blank=True, null=True)
    max_value = models.IntegerField(default=5, blank=True, null=True)

    class Meta:
        ordering = ["position", "id"]
        unique_together = ("survey", "slug")

    def __str__(self) -> str:
        return self.prompt

    def clean(self):
        if self.type == self.Type.RATING:
            if self.min_value is None or self.max_value is None:
                raise ValidationError("Rating questions need minimum and maximum values.")
            if self.min_value >= self.max_value:
                raise ValidationError("The rating minimum must be lower than the maximum.")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._build_unique_slug()
        super().save(*args, **kwargs)

    def _build_unique_slug(self):
        base = slugify(self.prompt)[:120] or "question"
        candidate = base
        suffix = 2
        while (
            SurveyQuestion.objects.filter(survey_id=self.survey_id, slug=candidate)
            .exclude(pk=self.pk)
            .exists()
        ):
            candidate = f"{base[:110]}-{suffix}"
            suffix += 1
        return candidate


class SurveyChoice(models.Model):
    question = models.ForeignKey(
        SurveyQuestion,
        related_name="choices",
        on_delete=models.CASCADE,
    )
    label = models.CharField(max_length=180)
    value = models.SlugField(max_length=140, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]
        unique_together = ("question", "value")

    def __str__(self) -> str:
        return self.label

    def save(self, *args, **kwargs):
        if not self.value:
            self.value = self._build_unique_value()
        super().save(*args, **kwargs)

    def _build_unique_value(self):
        base = slugify(self.label)[:120] or "choice"
        candidate = base
        suffix = 2
        while (
            SurveyChoice.objects.filter(question_id=self.question_id, value=candidate)
            .exclude(pk=self.pk)
            .exists()
        ):
            candidate = f"{base[:110]}-{suffix}"
            suffix += 1
        return candidate


class SurveyResponse(models.Model):
    survey = models.ForeignKey(Survey, related_name="responses", on_delete=models.CASCADE)
    respondent_email = models.EmailField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=255, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self) -> str:
        return f"{self.survey} response #{self.pk}"


class SurveyAnswer(models.Model):
    response = models.ForeignKey(
        SurveyResponse,
        related_name="answers",
        on_delete=models.CASCADE,
    )
    question = models.ForeignKey(
        SurveyQuestion,
        related_name="answers",
        on_delete=models.PROTECT,
    )
    value = models.JSONField(default=dict, blank=True)
    selected_choices = models.ManyToManyField(
        SurveyChoice,
        related_name="answers",
        blank=True,
    )

    class Meta:
        ordering = ["question__position", "id"]
        unique_together = ("response", "question")

    def __str__(self) -> str:
        return f"{self.question}: {self.value}"
