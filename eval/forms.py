from django import forms

from .constants import MAX_UPLOAD_SIZE, MAX_UPLOAD_SIZE_STR, RESULTENTRY_NAME_MAX_LENGTH
from .models import ResultEntry


def validate_zip(data):
    if not data.name.endswith(".zip"):
        raise forms.ValidationError("Submission file must be a zip file.")
    if data.content_type != "application/zip":
        raise forms.ValidationError("Incorrect content type found.")


def validate_size(data):
    if data.size > MAX_UPLOAD_SIZE:
        raise forms.ValidationError(
            f"Submission file must be smaller than {MAX_UPLOAD_SIZE_STR}."
        )


class UploadFileForm(forms.Form):
    required_css_class = "required"

    name = forms.CharField(
        max_length=RESULTENTRY_NAME_MAX_LENGTH,
        required=True,
        help_text="Submission or method name",
        widget=forms.TextInput,
    )
    submission = forms.FileField(
        label="Submission file",
        required=True,
        help_text="Your zipped submission file, see FAQ for more.",
        widget=forms.ClearableFileInput,
        validators=[validate_zip, validate_size],
    )


class EditResultEntryForm(forms.ModelForm):
    class Meta:
        model = ResultEntry
        fields = ["name", "visibility", "citation", "code_url"]
