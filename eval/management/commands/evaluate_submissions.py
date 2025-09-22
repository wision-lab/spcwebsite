import traceback
from zipfile import ZipFile

import imageio.v3 as iio
import numpy as np
import torch
from django.core.management.base import BaseCommand
from rich.progress import track
from torchmetrics.image import (
    LearnedPerceptualImagePatchSimilarity,
    PeakSignalNoiseRatio,
    StructuralSimilarityIndexMeasure,
)

from ...constants import EVAL_DIRECTORY, UPLOAD_DIRECTORY
from ...models import EntryStatus, ReconstructionEntry

PSNR = PeakSignalNoiseRatio(data_range=(0, 1))
SSIM = StructuralSimilarityIndexMeasure(data_range=(0, 1))
LPIPS = LearnedPerceptualImagePatchSimilarity()


class Command(BaseCommand):
    help = "Compute metrics for all pending submissions"

    @staticmethod
    def load_img(path):
        # Load and normalize a PNG image
        im = iio.imread(path)[..., :3]
        im = torch.tensor(im).permute(2, 0, 1)
        return im[None].float() / 255

    def evaluate_single(self, submission):
        metrics = []

        with ZipFile(submission.upload_path) as zipf:
            files = list(filter(lambda name: name.endswith(".png"), zipf.namelist()))

            for p in track(files):
                with zipf.open(p) as f:
                    pred = self.load_img(f)
                    target = self.load_img(EVAL_DIRECTORY / p)

                metrics.append(
                    [
                        PSNR(pred, target),
                        SSIM(pred, target),
                        LPIPS(pred, target),
                    ]
                )

        metrics = np.array(metrics)
        submission.psnr_mean, submission.ssim_mean, submission.lpips_mean = (
            metrics.mean(axis=0)
        )
        submission.psnr_5p, submission.ssim_5p, _ = np.percentile(metrics, 0.05, axis=0)
        submission.psnr_1p, submission.ssim_1p, _ = np.percentile(metrics, 0.01, axis=0)
        _, _, submission.lpips_5p = np.percentile(metrics, 0.95, axis=0)
        _, _, submission.lpips_1p = np.percentile(metrics, 0.99, axis=0)
        return metrics

    def handle(self, *args, **options):
        submissions = ReconstructionEntry.objects.filter(
            process_status=EntryStatus.WAIT_PROC
        )
        submission_ids = set(submissions.values_list("id", flat=True))
        archives = UPLOAD_DIRECTORY.glob("*.zip")

        if set(sub.upload_path for sub in submissions) != set(archives):
            self.stdout.write(
                self.style.WARNING(
                    "Found mismatch between uploaded archives and database entries waiting for processing!"
                )
            )

        for submission in submissions:
            try:
                self.evaluate_single(submission)
                submission.process_status = EntryStatus.SUCCESS
                submission.save()
            except Exception:
                self.stdout.write(self.style.ERROR(traceback.format_exc()))
                submission.process_status = EntryStatus.FAIL
                submission.save()

        # Delete all successful uploads
        for submission in ReconstructionEntry.objects.filter(
            process_status=EntryStatus.SUCCESS
        ):
            if submission.upload_path.exists():
                if submission.id not in submission_ids:
                    self.stdout.write(
                        self.style.NOTICE(
                            f"Deleting upload for previously successfully submission (id #{submission.id})."
                        )
                    )
                submission.upload_path.unlink(missing_ok=True)

        # Output stats only for those we've evaluated
        # Note: We need to re-fetch all submissions as they have potentially changed!
        successful = ReconstructionEntry.objects.filter(
            id__in=submission_ids, process_status=EntryStatus.SUCCESS
        )
        failures = ReconstructionEntry.objects.filter(
            id__in=submission_ids, process_status=EntryStatus.FAIL
        )

        if successful:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully evaluated {len(successful)} submissions."
                )
            )

        if failures:
            self.stdout.write(
                self.style.ERROR(
                    f"Evaluation errors found for {len(failures)} submissions."
                )
            )
