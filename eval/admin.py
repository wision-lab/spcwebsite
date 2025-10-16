from django.contrib import admin
from django.contrib.contenttypes.admin import GenericTabularInline

from .models import ReconstructionEntry, ResultSample


class ResultSamplesInline(GenericTabularInline):
    model = ResultSample
    extra = 0


class ResultEntryAdmin(admin.ModelAdmin):
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


admin.site.register(ReconstructionEntry, ResultEntryAdmin)
