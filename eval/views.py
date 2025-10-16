import hashlib
import random
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.html import format_html
from django.views import View, generic

from .constants import EVAL_FILES, MEDIA_DIRECTORY, SAMPLE_FRAMES_DIRECTORY
from .forms import EditResultEntryForm, UploadFileForm
from .models import EntryStatus, EntryVisibility, ReconstructionEntry


class ReconstructionEntriesView(View):
    VALID_KEYS = {m.name: m.verbose_name for m in ReconstructionEntry.metric_fields}

    def get(self, request):
        sortby = request.GET.get("sortby", "")

        if sortby.removeprefix("-") not in self.VALID_KEYS:
            sortby = ReconstructionEntry.metric_fields[0].name

        if request.user.is_authenticated:
            my_entries = (
                ReconstructionEntry.objects.filter(creator__exact=request.user.pk)
                .filter(process_status=EntryStatus.SUCCESS)
                .filter(is_active=True)
            )
        else:
            my_entries = ReconstructionEntry.objects.none()

        entries = (
            ReconstructionEntry.objects.exclude(visibility=EntryVisibility.PRIV)
            .filter(process_status=EntryStatus.SUCCESS)
            .filter(is_active=True)
            .union(my_entries)
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


class DeleteEntryView(LoginRequiredMixin, UserPassesTestMixin, generic.DeleteView):
    model = ReconstructionEntry
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("core:user")

    def test_func(self):
        return self.request.user.pk == self.get_object().creator.pk

    def get_object(self, queryset=None):
        pk = self.kwargs.get(self.pk_url_kwarg)
        return get_object_or_404(self.model, pk=pk, is_active=True)

    def form_valid(self, form):
        # Don't actually delete the entry, just mark as inactive
        # Do delete the submission file though
        entry = self.get_object()
        entry.upload_path.unlink(missing_ok=True)
        entry.is_active = False
        entry.save()

        return redirect(self.success_url)


class SubmitView(LoginRequiredMixin, UserPassesTestMixin, generic.edit.FormView):
    template_name = "submit.html"
    success_url = reverse_lazy("core:user")
    form_class = UploadFileForm

    def test_func(self):
        return self.request.user.can_upload()

    def handle_no_permission(self):
        # If user cannot upload, send them back to the user page
        return redirect("core:user")

    def form_valid(self, form):
        entry = form.save(commit=False)
        entry.pub_date = timezone.now()
        entry.creator = self.request.user
        upload = self.request.FILES["submission"]
        md5sum = hashlib.md5()

        # Write uploaded file to disk, return server error (500) if failed
        # Ensure no half written submission files exist
        try:
            with open(entry.upload_path, "wb+") as f:
                for chunk in upload.chunks():
                    md5sum.update(chunk)
                    f.write(chunk)
        except IOError:
            entry.upload_path.unlink(missing_ok=True)
            return HttpResponse(status=500)

        # Validate that submission contains all files
        try:
            with ZipFile(entry.upload_path) as zipf:
                upload_files = set(
                    filter(lambda name: name.endswith(".png"), zipf.namelist())
                )
                if len(upload_files) < len(EVAL_FILES):
                    entry.upload_path.unlink(missing_ok=True)
                    form.add_error(
                        "submission",
                        format_html(
                            "{}</br>{}",
                            "Some test files appear to be missing! Please ensure that format is correct.",
                            f'Example of missing file: "{next(iter(EVAL_FILES - upload_files))}"',
                        ),
                    )
                    return super().form_invalid(form)
                elif len(upload_files) > len(EVAL_FILES):
                    entry.upload_path.unlink(missing_ok=True)
                    form.add_error(
                        "submission",
                        format_html(
                            "{}</br>{}",
                            "Unexpected additional files found:",
                            f'Example of missing file: "{next(iter(upload_files - EVAL_FILES))}"',
                        ),
                    )
                    return super().form_invalid(form)
                elif EVAL_FILES != upload_files:
                    entry.upload_path.unlink(missing_ok=True)
                    form.add_error(
                        "submission",
                        format_html(
                            "{}</br>{}</br>{}",
                            "Submission does not follow correct directory structure.",
                            "Expected structure: <SCENE-NAME>/<FRAME-IDX>.png",
                            f'Instead got frames such as "{next(iter(upload_files))}"',
                        ),
                    )
                    return super().form_invalid(form)
        except (BadZipFile, RuntimeError):
            entry.upload_path.unlink(missing_ok=True)
            form.add_error("submission", "Malformed ZIP file.")
            return super().form_invalid(form)

        # Mark the entry for later processing
        entry.process_status = EntryStatus.WAIT_PROC
        entry.md5sum = md5sum.hexdigest()
        entry.save()

        return super().form_valid(form)


class DetailView(UserPassesTestMixin, generic.DetailView):
    model = ReconstructionEntry
    template_name = "detail.html"
    context_object_name = "entry"

    def test_func(self):
        return self.get_object().can_be_seen_by(self.request.user)

    def get_object(self, queryset=None):
        pk = self.kwargs.get(self.pk_url_kwarg)
        return get_object_or_404(
            self.model, pk=pk, is_active=True, process_status=EntryStatus.SUCCESS
        )

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        entry = self.get_object()
        context = super().get_context_data(**kwargs)
        subpaths = sorted(
            Path(s.file.path).relative_to(entry.sample_directory.resolve())
            for s in entry.samples.all()
        )
        context["image_paths"] = [
            (
                SAMPLE_FRAMES_DIRECTORY / self.model.PREFIX / subpath,
                entry.sample_directory.relative_to(MEDIA_DIRECTORY) / subpath,
            )
            for subpath in subpaths
        ]
        return context


class CompareView(View):
    model = ReconstructionEntry
    template_name = "compare.html"

    def dispatch(self, request, *args, pk1=None, pk2=None, **kwargs):
        # Directly do UserPassesTestMixin check here instead of
        # inheriting from mixin in order to pass the pks around
        if pk1 is None and pk2 is None:
            try:
                # Select random pks and redirect
                pk1, pk2 = random.sample(
                    [
                        entry.pk
                        for entry in self.model.objects.filter(
                            is_active=True,
                            process_status=EntryStatus.SUCCESS,
                            visibility=EntryVisibility.PUBL,
                        )
                    ],
                    2,
                )
                return redirect("eval:compare", pk1=pk1, pk2=pk2)
            except ValueError:
                # If there's not enough entries, redirect to leaderboard
                return redirect('eval:reconstruction')

        entry_1 = get_object_or_404(
            self.model, pk=pk1, is_active=True, process_status=EntryStatus.SUCCESS
        )
        entry_2 = get_object_or_404(
            self.model, pk=pk2, is_active=True, process_status=EntryStatus.SUCCESS
        )

        if not self.test_func([entry_1, entry_2]):
            return self.handle_no_permission()
        return super().dispatch(
            request, *args, entry_1=entry_1, entry_2=entry_2, **kwargs
        )

    def test_func(self, objects):
        return all(obj.can_be_seen_by(self.request.user) for obj in objects)

    def get(self, request, entry_1=None, entry_2=None):
        if entry_1 is None or entry_2 is None:
            # This should never happen as we directly pass the entries from dispatch
            return HttpResponse(status=500)

        emphasis = [
            m1 > m2 if "↑" in name.verbose_name else m1 <= m2
            for m1, m2, name in zip(
                entry_1.metrics, entry_2.metrics, entry_1.metric_fields
            )
        ]
        subpaths = set(
            Path(s.file.path).relative_to(entry_1.sample_directory.resolve())
            for s in entry_1.samples.all()
        ).intersection(
            Path(s.file.path).relative_to(entry_2.sample_directory.resolve())
            for s in entry_2.samples.all()
        )
        context = {
            "entry_1": entry_1,
            "entry_2": entry_2,
            "emphasis": emphasis,
            "samples_dir_1": entry_1.sample_directory.relative_to(MEDIA_DIRECTORY),
            "samples_dir_2": entry_2.sample_directory.relative_to(MEDIA_DIRECTORY),
            "image_subpaths": sorted(list(subpaths)),
        }
        return render(request, self.template_name, context=context)


class EditView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = ReconstructionEntry
    form_class = EditResultEntryForm
    template_name = "resultentry_form.html"

    def test_func(self):
        obj = self.get_object()
        return self.request.user == obj.creator

    def get_object(self, queryset=None):
        pk = self.kwargs.get(self.pk_url_kwarg)
        return get_object_or_404(self.model, pk=pk, is_active=True)

    def get_success_url(self):
        return reverse_lazy("eval:detail", kwargs={"pk": self.object.id})
