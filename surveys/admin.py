from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import Survey, SurveyAnswer, SurveyChoice, SurveyQuestion, SurveyResponse


class SurveyAdminThemeMixin:
    class Media:
        css = {"all": ("surveys/admin.css",)}


class SurveyQuestionInline(SurveyAdminThemeMixin, admin.StackedInline):
    model = SurveyQuestion
    extra = 1
    show_change_link = True
    prepopulated_fields = {"slug": ("prompt",)}
    fields = (
        ("position", "type", "is_required"),
        "prompt",
        "slug",
        "help_text",
        ("min_value", "max_value"),
    )


class SurveyChoiceInline(SurveyAdminThemeMixin, admin.TabularInline):
    model = SurveyChoice
    extra = 2
    fields = ("position", "label", "value")
    prepopulated_fields = {"value": ("label",)}


class SurveyAnswerInline(admin.TabularInline):
    model = SurveyAnswer
    extra = 0
    can_delete = False
    fields = ("question", "value", "selected_choices_display")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="Selected choices")
    def selected_choices_display(self, obj):
        labels = [choice.label for choice in obj.selected_choices.all()]
        return ", ".join(labels) or "-"


@admin.register(Survey)
class SurveyAdmin(SurveyAdminThemeMixin, admin.ModelAdmin):
    list_display = (
        "title",
        "status",
        "starts_at",
        "ends_at",
        "response_count",
        "api_link",
    )
    list_filter = ("status", "starts_at", "ends_at")
    search_fields = ("title", "description", "slug")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at", "response_count", "api_link")
    inlines = [SurveyQuestionInline]
    actions = ("publish_surveys", "close_surveys")
    fieldsets = (
        (
            "Survey",
            {
                "fields": (
                    "title",
                    "slug",
                    "description",
                    "thank_you_message",
                )
            },
        ),
        (
            "Publishing",
            {
                "fields": (
                    "status",
                    "starts_at",
                    "ends_at",
                    "allow_multiple_responses",
                    "api_link",
                )
            },
        ),
        (
            "System",
            {
                "fields": ("response_count", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Responses")
    def response_count(self, obj):
        if not obj.pk:
            return 0
        return obj.responses.count()

    @admin.display(description="Public API")
    def api_link(self, obj):
        if not obj.pk:
            return "-"
        url = reverse("survey-detail", args=[obj.slug])
        return format_html('<a class="button" href="{}" target="_blank">Open API</a>', url)

    @admin.action(description="Publish selected surveys")
    def publish_surveys(self, request, queryset):
        queryset.update(status=Survey.Status.PUBLISHED)

    @admin.action(description="Close selected surveys")
    def close_surveys(self, request, queryset):
        queryset.update(status=Survey.Status.CLOSED)


@admin.register(SurveyQuestion)
class SurveyQuestionAdmin(SurveyAdminThemeMixin, admin.ModelAdmin):
    list_display = ("prompt", "survey", "type", "is_required", "position")
    list_filter = ("type", "is_required", "survey__status")
    search_fields = ("prompt", "slug", "survey__title")
    prepopulated_fields = {"slug": ("prompt",)}
    inlines = [SurveyChoiceInline]
    fieldsets = (
        (
            "Question",
            {
                "fields": (
                    "survey",
                    "prompt",
                    "slug",
                    "type",
                    "help_text",
                    "is_required",
                    "position",
                )
            },
        ),
        (
            "Rating Options",
            {
                "fields": ("min_value", "max_value"),
                "description": "Used only for rating questions.",
            },
        ),
    )


@admin.register(SurveyChoice)
class SurveyChoiceAdmin(SurveyAdminThemeMixin, admin.ModelAdmin):
    list_display = ("label", "question", "survey_title", "value", "position")
    list_filter = ("question__survey",)
    search_fields = ("label", "value", "question__prompt", "question__survey__title")
    prepopulated_fields = {"value": ("label",)}

    @admin.display(description="Survey")
    def survey_title(self, obj):
        return obj.question.survey.title


@admin.register(SurveyResponse)
class SurveyResponseAdmin(SurveyAdminThemeMixin, admin.ModelAdmin):
    list_display = ("survey", "respondent_email", "submitted_at", "ip_address")
    list_filter = ("survey", "submitted_at")
    search_fields = ("survey__title", "respondent_email", "ip_address")
    readonly_fields = (
        "survey",
        "respondent_email",
        "metadata",
        "ip_address",
        "user_agent",
        "submitted_at",
    )
    inlines = [SurveyAnswerInline]

    def has_add_permission(self, request):
        return False


admin.site.site_header = "Survey Studio"
admin.site.site_title = "Survey Studio"
admin.site.index_title = "Survey Management"
