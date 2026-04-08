from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils.html import format_html
from django.db.models import Count

from eval.models import ReconstructionEntry

from .forms import UserCreationForm
from .models import User


class UserChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    disabled password hash display field.
    """

    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ("email", "password", "is_verified", "is_active", "is_superuser")


class UserAdmin(BaseUserAdmin):
    # The forms to add and change user instances
    form = UserChangeForm
    add_form = UserCreationForm

    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    list_display = (
        "email",
        "num_entries",
        "maildomain",
        "university",
        "is_verified",
        "is_active",
        "is_superuser",
    )
    list_filter = ("university", "is_verified", "is_active", "is_superuser")
    fieldsets = (
        (
            "Information",
            {"fields": ("email", "password", "university", "website", "description")},
        ),
        ("Result Entries", {"fields": ("entries",)}),
        ("Status", {"fields": ("is_verified", "is_active")}),
        ("Permissions", {"fields": ("is_superuser",)}),
    )
    readonly_fields = ("entries",)
    # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
    # overrides get_fieldsets to use this attribute when creating a user.
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "university", "website"),
            },
        ),
    )
    search_fields = ("email", "university")
    ordering = ("email",)
    filter_horizontal = ()

    def num_entries(self, obj):
        return obj.num_entries

    num_entries.admin_order_field = "num_entries"
    num_entries.short_description = "Number of entries"

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(num_entries=Count("entries"))
        return queryset

    def entries(self, obj):
        entries_list = []

        for entry in obj.entries.all().order_by("-pub_date"):
            change_url = reverse(
                f"admin:{ReconstructionEntry._meta.db_table}_change", args=(entry.id,)
            )
            detail_url = reverse("eval:detail", args=(entry.id,))

            entries_list.append(
                format_html(
                    '<a href="{}">{}</a> <a href="{}" title="View details">🔍</a>',
                    change_url,
                    entry.name,
                    detail_url,
                )
            )

        return format_html(", ".join(entries_list))


admin.site.register(User, UserAdmin)

admin.site.unregister(Group)
