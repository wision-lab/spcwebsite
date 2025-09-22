from django.contrib.auth import get_user_model
from django.db import models

from .constants import RESULTENTRY_NAME_MAX_LENGTH, UPLOAD_DIRECTORY


class EntryVisibility(models.TextChoices):
    PUBL = "PUBL", "Public"
    PRIV = "PRIV", "Private"
    ANON = "ANON", "Anonymous"


class EntryStatus(models.TextChoices):
    SUCCESS = "SUCCESS", "Success"
    WAIT_UPL = "WAIT_UPL", "Waiting for upload..."
    WAIT_PROC = "WAIT_PROC", "Waiting for evaluation..."
    FAIL = "FAIL", "There was a problem with the submission."


class ResultEntry(models.Model):
    name = models.CharField(max_length=RESULTENTRY_NAME_MAX_LENGTH)
    creator = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    pub_date = models.DateTimeField("date published")
    visibility = models.CharField(
        max_length=4, choices=EntryVisibility, blank=False, default=EntryVisibility.PRIV
    )
    citation = models.CharField(max_length=500, blank=True)
    process_status = models.CharField(
        max_length=9, choices=EntryStatus, blank=False, null=False
    )
    code_url = models.URLField("Link to code", blank=True, null=True)

    class Meta:
        abstract = True

    @property
    def upload_path(self):
        return (
            UPLOAD_DIRECTORY / self.PREFIX / f"upload_{self.creator.id}_{self.id}.zip"
        )


class ReconstructionEntry(ResultEntry):
    # Upload directory prefix
    PREFIX = "reconstruction"
    (UPLOAD_DIRECTORY / PREFIX).mkdir(exist_ok=True)

    # Evaluation fields
    psnr_mean = models.FloatField("Mean\nPSNR ↑", default=-1)
    ssim_mean = models.FloatField("Mean\nSSIM ↑", default=-1)
    lpips_mean = models.FloatField("Mean\nLPIPS ↓", default=-1)

    psnr_5p = models.FloatField("5% Low\nPSNR ↑", default=-1)
    ssim_5p = models.FloatField("5% Low\nSSIM ↑", default=-1)
    lpips_5p = models.FloatField("5% Low\nLPIPS ↓", default=-1)

    psnr_1p = models.FloatField("1% Low\nPSNR ↑", default=-1)
    ssim_1p = models.FloatField("1% Low\nSSIM ↑", default=-1)
    lpips_1p = models.FloatField("1% Low\nLPIPS ↓", default=-1)

    metric_fields = [
        psnr_mean,
        psnr_5p,
        psnr_1p,
        ssim_mean,
        ssim_5p,
        ssim_1p,
        lpips_mean,
        lpips_5p,
        lpips_1p,
    ]

    @property
    def metrics(self):
        return [getattr(self, m.name) for m in self.metric_fields]

    def __str__(self):
        return self.name
