from zipfile import ZipFile

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, UpdateView
from django.views.generic.edit import FormView

from .constants import EVAL_FILES, MAX_UPLOAD_SIZE, MAX_UPLOAD_SIZE_STR
from .forms import EditResultEntryForm, UploadFileForm
from .models import EntryStatus, EntryVisibility, ReconstructionEntry


class ReconstructionEntriesView(View):
    VALID_KEYS = {m.name: m.verbose_name for m in ReconstructionEntry.metric_fields}

    def get(self, request):
        sortby = request.GET.get("sortby", "")

        if sortby.removeprefix("-") not in self.VALID_KEYS:
            sortby = ReconstructionEntry.metric_fields[0].name

        entries = (
            ReconstructionEntry.objects.exclude(visibility=EntryVisibility.PRIV)
            .filter(process_status=EntryStatus.SUCCESS)
            .order_by(sortby)
        )

        if "↑" in self.VALID_KEYS[sortby.removeprefix("-")]:
            entries = entries.reverse()

        context = {
            "entries": entries,
            "sortby": sortby.removeprefix("-"),
            "direction": "-" not in sortby,
            "metric_fields": ReconstructionEntry.metric_fields,
        }
        return render(request, "reconstruction.html", context)


class SubmitView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = "submit.html"
    success_url = reverse_lazy("core:user")
    form_class = UploadFileForm

    def test_func(self):
        return self.request.user.can_upload()

    def handle_no_permission(self):
        # If user cannot upload, send them back to the user page
        return redirect("core:user")

    def form_valid(self, form):
        name = form.cleaned_data["name"]
        creator = self.request.user
        upload = self.request.FILES["submission"]
        entry = ReconstructionEntry.objects.create(
            name=name,
            creator=creator,
            pub_date=timezone.now(),
            process_status=EntryStatus.WAIT_UPL,
        )

        # Re-perform validation on server-side
        if not upload.name.endswith(".zip"):
            form.add_error("submission", "Submission file must be a zip file.")
            return super().form_invalid(form)
        elif upload.content_type != "application/zip":
            form.add_error("submission", f"Malformed ZIP file.")
            return super().form_invalid(form)
        elif upload.size > MAX_UPLOAD_SIZE:
            form.add_error(
                "submission",
                f"Submission file must be smaller than {MAX_UPLOAD_SIZE_STR}.",
            )
            return super().form_invalid(form)

        # Write uploaded file to disk
        with open(entry.upload_path, "wb+") as f:
            for chunk in upload.chunks():
                f.write(chunk)

        # Validate that submission contains all files
        with ZipFile(entry.upload_path) as zipf:
            upload_files = set(
                filter(lambda name: name.endswith(".png"), zipf.namelist())
            )
            if EVAL_FILES != upload_files:
                entry.upload_path.unlink(missing_ok=True)
                form.add_error(
                    "submission",
                    f"Some test files appear to be missing! Please ensure that format is correct.",
                )
                return super().form_invalid(form)

        # Mark the entry for later processing
        entry.process_status = EntryStatus.WAIT_PROC
        entry.save()

        return super().form_valid(form)


class DetailView(UserPassesTestMixin, DetailView):
    model = ReconstructionEntry
    template_name = "detail.html"
    context_object_name = "entry"

    def test_func(self):
        obj = self.get_object()
        if obj.visibility != EntryVisibility.PRIV:
            return True
        else:
            return (
                self.request.user.is_authenticated
                and self.request.user.pk == obj.creator.pk
            )

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        context["range"] = [f"{i:02d}" for i in range(10)]
        return context


class EditView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = ReconstructionEntry
    form_class = EditResultEntryForm
    template_name = "resultentry_form.html"

    def test_func(self):
        obj = self.get_object()
        return self.request.user == obj.creator

    def get_success_url(self):
        return reverse_lazy("eval:detail", kwargs={"pk": self.object.id})
