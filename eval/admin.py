from django import forms
from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django_admin_action_forms import (
    AdminActionForm,
    AdminActionFormsMixin,
    action_with_form,
)

from .models import EntryVisibility, ReconstructionEntry, ResultSample


class ChangeVisibilityForm(AdminActionForm):
    visibility = forms.ChoiceField(choices=EntryVisibility.choices, required=True)


class ResultSamplesInline(GenericTabularInline):
    model = ResultSample
    extra = 0


class ResultEntryAdmin(AdminActionFormsMixin, admin.ModelAdmin):
    list_display = [
        "name",
        "pub_date",
        "visibility",
        "process_status",
        "creator",
    ]
    inlines = [
        ResultSamplesInline,
    ]
    ordering = ("pub_date",)

    @action_with_form(
        ChangeVisibilityForm,
        description="Change visibility for selected entries",
    )
    def change_visibility_action(self, request, queryset, data):
        for entry in queryset:
            entry.visibility = data["visibility"]
            entry.save()
        self.message_user(
            request,
            f"Visibility changed to {data['visibility']} for {queryset.count()} orders.",
        )

    actions = [change_visibility_action]


admin.site.register(ReconstructionEntry, ResultEntryAdmin)
