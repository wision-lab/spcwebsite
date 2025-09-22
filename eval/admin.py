from django.contrib import admin

from .models import ReconstructionEntry

class ResultEntryAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "pub_date",
        "visibility",
        "process_status",
        "creator",
    ]
    ordering = ("pub_date",)

admin.site.register(ReconstructionEntry, ResultEntryAdmin)
