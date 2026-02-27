import hashlib
import random
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.db.models import Case, Count, F, OuterRef, Q, Subquery, Value, When
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
        collapse_users = request.GET.get("collapse", "0") == "1"
        creator_id = request.GET.get("creator")
        sortby_col = sortby.removeprefix("-")
        direction = not sortby.startswith("-")

        if sortby_col not in self.VALID_KEYS:
            sortby = ReconstructionEntry.metric_fields[0].name
            sortby_col = sortby.removeprefix("-")

        # Flip direction if metric if higher-is-better
        if "↑" in self.VALID_KEYS[sortby_col]:
            sortby = f"-{sortby}" if direction else sortby.removeprefix("-")

        # Base query: SUCCESS and active entries
        entries = ReconstructionEntry.objects.filter(
            process_status=EntryStatus.SUCCESS, is_active=True
        ).exclude(**{sortby_col: -1.0})

        # Base visibility filter
        visible_q = Q(visibility__in=[EntryVisibility.PUBL, EntryVisibility.ANON])
        if request.user.is_authenticated:
            visible_q |= Q(creator=request.user)

        if not request.user.is_superuser:
            entries = entries.filter(visible_q)

        # Filter by creator if requested
        if creator_id is not None:
            entries = entries.filter(creator_id=creator_id)
            collapse_users = False

        # Order by selected metric, respect higher-is-better or not
        entries = entries.order_by(sortby)

        if collapse_users:
            if request.user.is_authenticated:
                if request.user.is_superuser:
                    # Superusers see everything grouped by user
                    group_field = "creator_id"
                else:
                    # Anonymous entries are treated as their own group (not collapsed), unless they are the user's own
                    # entry, in which case they are collapsed with the user's other entries (including private entries)
                    entries = entries.annotate(
                        grouping_key=Case(
                            When(
                                Q(visibility=EntryVisibility.ANON)
                                & ~Q(creator_id=request.user),
                                then=F("id"),
                            ),
                            default=F("creator_id"),
                        )
                    )
                    group_field = "grouping_key"
            else:
                # Anonymous entries are treated as their own group when not logged in.
                entries = entries.annotate(
                    grouping_key=Case(
                        When(Q(visibility=EntryVisibility.ANON), then=F("id")),
                        default=F("creator_id"),
                    )
                )
                group_field = "grouping_key"

            # Annotate with the count of entries in this participant's group
            # We reuse the existing 'entries' queryset (which has visibility/status filters) for the subquery
            count_subquery = (
                entries.filter(**{group_field: OuterRef(group_field)})
                .values(group_field)
                .order_by()
                .annotate(c=Count("id"))
                .values("c")
            )

            # Identify the best entry per group
            best_id_subquery = entries.filter(
                **{group_field: OuterRef(group_field)}
            ).values("id")[:1]

            # To show the "best of N" indicator, we count how many entries exist for this user in the visible set
            entries = entries.annotate(collapsed_count=Subquery(count_subquery)).filter(
                id=Subquery(best_id_subquery)
            )
        else:
            entries = entries.annotate(collapsed_count=Value(1))

        paginator = Paginator(entries, 25)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context = {
            "page_obj": page_obj,
            "sortby": sortby_col,
            "direction": direction,
            "collapse": collapse_users,
            "creator": creator_id,
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
                SAMPLE_FRAMES_DIRECTORY
                / self.model.PREFIX
                / subpath.with_suffix(".webp"),
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
                        for entry in self.model.objects.exclude(
                            visibility=EntryVisibility.PRIV
                        ).filter(
                            is_active=True,
                            process_status=EntryStatus.SUCCESS,
                        )
                    ],
                    2,
                )
                return redirect("eval:compare", pk1=pk1, pk2=pk2)
            except ValueError:
                # If there's not enough entries, redirect to leaderboard
                return redirect("eval:reconstruction")

        entry_1 = get_object_or_404(
            self.model, pk=pk1, is_active=True, process_status=EntryStatus.SUCCESS
        )
        entry_2 = get_object_or_404(
            self.model, pk=pk2, is_active=True, process_status=EntryStatus.SUCCESS
        )

        if not self.test_func([entry_1, entry_2]):
            # If user cannot see the entries, send them back to the leaderboard
            return redirect("eval:reconstruction")
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
        image_subpaths = [
            (
                entry_1.sample_directory.relative_to(MEDIA_DIRECTORY) / subpath,
                entry_2.sample_directory.relative_to(MEDIA_DIRECTORY) / subpath,
                SAMPLE_FRAMES_DIRECTORY
                / self.model.PREFIX
                / subpath.with_suffix(".webp"),
            )
            for subpath in sorted(list(subpaths))
        ]
        context = {
            "entry_1": entry_1,
            "entry_2": entry_2,
            "emphasis": emphasis,
            "image_subpaths": image_subpaths,
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
        if self.object.process_status == EntryStatus.SUCCESS:
            return reverse_lazy("eval:detail", kwargs={"pk": self.object.id})
        else:
            return reverse_lazy("core:user")
