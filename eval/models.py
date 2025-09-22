from django.contrib.auth import get_user_model
from django.db import models

from .constants import RESULTENTRY_NAME_MAX_LENGTH, UPLOAD_DIRECTORY


class ReconstructionEntry(models.Model):
    VISIBILITY_CHOICES = (
        ("PUBL", "Public"),
        ("PRIV", "Private"),
        ("ANON", "Anonymous"),
    )
    STATUS_CHOICES = (
        ("SUCCESS", "Success"),
        ("WAIT_UPL", "Waiting for upload..."),
        ("WAIT_PROC", "Waiting for evaluation..."),
        ("FAIL", "There was a problem with the submission."),
    )

    name = models.CharField(max_length=RESULTENTRY_NAME_MAX_LENGTH)
    creator = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    pub_date = models.DateTimeField("date published")
    visibility = models.CharField(
        max_length=4, choices=VISIBILITY_CHOICES, blank=False, default="PRIV"
    )
    citation = models.CharField(max_length=500, blank=True)
    process_status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, blank=False, null=False
    )
    code_url = models.URLField("Link to code", blank=True, null=True)

    # Evaluation fields
    mean_psnr = models.FloatField("Mean PSNR", default=-1)
    mean_ssim = models.FloatField("Mean SSIM", default=-1)
    mean_lpips = models.FloatField("Mean LPIPS", default=-1)

    @property
    def upload_path(self):
        return UPLOAD_DIRECTORY / f"upload_{self.creator.id}_{self.id}.zip"

    def __str__(self):
        return self.name
