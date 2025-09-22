from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.models import Group

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
        ("Status", {"fields": ("is_verified", "is_active")}),
        ("Permissions", {"fields": ("is_superuser",)}),
    )
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


admin.site.register(User, UserAdmin)

admin.site.unregister(Group)
