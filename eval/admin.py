from django import forms
from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.utils.safestring import mark_safe
from django_admin_action_forms import (
    AdminActionForm,
    AdminActionFormsMixin,
    action_with_form,
)

from .models import EntryVisibility, ReconstructionEntry, ResultSample


class ChangeVisibilityForm(AdminActionForm):
    visibility = forms.ChoiceField(choices=EntryVisibility.choices, required=True)


class ChangeMetricsForm(AdminActionForm, forms.ModelForm):
    class Meta:
        model = ReconstructionEntry
        fields = [f.name for f in ReconstructionEntry.metric_fields]
        help_text = mark_safe("""
            <b style='color:red'>
                This will overwrite all metrics that you set a value for, for all selected users. 
                </br>
                This action cannot be undone. Proceed with caution!
            </b>""")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.keys():
            self.fields[field].initial = None
            self.fields[field].required = False


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
    list_filter = ("visibility", "process_status", "creator", "pub_date")

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
            f"Visibility changed to {data['visibility']} for {queryset.count()} entries.",
        )

    @action_with_form(
        ChangeMetricsForm,
        description="Bulk edit metrics for selected entries",
    )
    def change_metrics_action(self, request, queryset, data):
        filtered_data = {k: v for k, v in data.items() if v is not None}

        if filtered_data:
            for entry in queryset:
                for field, value in filtered_data.items():
                    setattr(entry, field, value)
                entry.save()

            self.message_user(
                request,
                f"Changed metrics {filtered_data} for {queryset.count()} entries.",
            )
        else:
            self.message_user(request, f"No data has been changed.")

    actions = [change_visibility_action, change_metrics_action]


admin.site.register(ReconstructionEntry, ResultEntryAdmin)
