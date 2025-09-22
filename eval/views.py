from zipfile import ZipFile

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import DetailView, UpdateView
from django.views.generic.edit import FormView

from .constants import EVAL_FILES, MAX_UPLOAD_SIZE, MAX_UPLOAD_SIZE_STR
from .forms import UploadFileForm
from .models import ReconstructionEntry


class SubmitView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = "submit.html"
    success_url = "/accounts/user"
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
            process_status="WAIT_UPL",
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
        entry.process_status = "WAIT_PROC"
        entry.save()

        return super().form_valid(form)


class DetailView(UserPassesTestMixin, DetailView):
    model = ReconstructionEntry
    template_name = "detail.html"

    def test_func(self):
        obj = self.get_object()
        if obj.visibility in ["PUBL", "ANON"]:
            return True
        else:
            if not self.request.user.is_authenticated:
                return False
            return self.request.user.pk == obj.creator.pk

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
        context["range"] = [f"{i:02d}" for i in range(10)]
        return context


class EditView(UserPassesTestMixin, UpdateView):
    model = ReconstructionEntry
    # form_class = EditResultEntryForm
    # template_name = "springeval/resultentry_form.html"

    # def test_func(self):
    #     obj = self.get_object()
    #     return self.request.user.is_authenticated and (self.request.user == obj.creator)

    # def get_success_url(self):
    #     return reverse_lazy("springeval:detail", kwargs={"pk": self.object.id})

    # def form_valid(self, form):
    #     # First, let Django save the model fields (name, visibility, etc.)
    #     response = super().form_valid(form)
    #     entry = self.object
    #     mt = entry.method_type
    #     files = self.request.FILES

    #     # Only proceed if user checked the toggle
    #     if form.cleaned_data["evaluate_robustness"]:
    #         # disp1 robustness (for ST & SF)
    #         if mt in ["ST", "SF"] and files.get("robustness_disp1file"):
    #             f = files["robustness_disp1file"]
    #             path = os.path.join(
    #                 UPLOAD_DIRECTORY,
    #                 f"upload__{entry.id}__{entry.imghash.hex}__robust_disp1.hdf5",
    #             )
    #             with open(path, "wb+") as dest:
    #                 for chunk in f.chunks():
    #                     dest.write(chunk)

    #         # flow robustness (for FL & SF)
    #         if mt in ["FL", "SF"] and files.get("robustness_flowfile"):
    #             f = files["robustness_flowfile"]
    #             path = os.path.join(
    #                 UPLOAD_DIRECTORY,
    #                 f"upload__{entry.id}__{entry.imghash.hex}__robust_flow.hdf5",
    #             )
    #             with open(path, "wb+") as dest:
    #                 for chunk in f.chunks():
    #                     dest.write(chunk)

    #         # disp2 robustness (only for SF)
    #         if mt == "SF" and files.get("robustness_disp2file"):
    #             f = files["robustness_disp2file"]
    #             path = os.path.join(
    #                 UPLOAD_DIRECTORY,
    #                 f"upload__{entry.id}__{entry.imghash.hex}__robust_disp2.hdf5",
    #             )
    #             with open(path, "wb+") as dest:
    #                 for chunk in f.chunks():
    #                     dest.write(chunk)

    #         # After adding robustness files, re-queue for processing
    #         entry.process_status = "WAIT_PROC"
    #         entry.save()

    #     return response
