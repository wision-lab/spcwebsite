import uuid

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models

from .constants import MEDIA_DIRECTORY, RESULTENTRY_NAME_MAX_LENGTH, UPLOAD_DIRECTORY


class EntryVisibility(models.TextChoices):
    PUBL = "PUBL", "Public"
    PRIV = "PRIV", "Private"
    ANON = "ANON", "Anonymous"


class EntryStatus(models.TextChoices):
    SUCCESS = "SUCCESS", "Success"
    WAIT_UPL = "WAIT_UPL", "Waiting for upload..."
    WAIT_PROC = "WAIT_PROC", "Waiting for evaluation..."
    FAIL = "FAIL", "There was a problem with the submission."


class ResultSample(models.Model):
    object_id = models.PositiveBigIntegerField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    entry = GenericForeignKey("content_type", "object_id")
    file = models.ImageField(unique=True)

    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def __str__(self):
        return self.file.path


class ResultEntry(models.Model):
    # Managed / Auto generated fields
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    creator = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    pub_date = models.DateTimeField("date published")
    process_status = models.CharField(
        max_length=9, choices=EntryStatus, blank=False, null=False
    )
    samples = GenericRelation(ResultSample)
    md5sum = models.CharField(max_length=32)
    is_active = models.BooleanField(default=True)

    # User editable fields
    name = models.CharField(max_length=RESULTENTRY_NAME_MAX_LENGTH)
    visibility = models.CharField(
        max_length=4, choices=EntryVisibility, blank=False, default=EntryVisibility.PRIV
    )
    citation = models.CharField(max_length=500, blank=True)
    code_url = models.URLField("Link to code", blank=True, null=True)

    class Meta:
        abstract = True

    @property
    def upload_path(self):
        return (
            UPLOAD_DIRECTORY
            / self.PREFIX
            / f"upload_{self.creator.id:06}_{self.uuid}.zip"
        )

    @property
    def sample_directory(self):
        return MEDIA_DIRECTORY / self.PREFIX / f"{self.creator.id:06}" / f"{self.uuid}"

    def can_be_seen_by(self, user):
        return (self.visibility != EntryVisibility.PRIV) or (
            user.is_authenticated and user.pk == self.creator.pk
        )


class ReconstructionEntry(ResultEntry):
    # Upload directory prefix
    PREFIX = "reconstruction"
    (UPLOAD_DIRECTORY / PREFIX).mkdir(exist_ok=True)

    # Evaluation fields
    psnr_mean = models.FloatField("Mean\nPSNR ↑", default=-1)
    ssim_mean = models.FloatField("Mean\nMS-SSIM ↑", default=-1)
    lpips_mean = models.FloatField("Mean\nLPIPS ↓", default=-1)

    psnr_5p = models.FloatField("5% Low\nPSNR ↑", default=-1)
    ssim_5p = models.FloatField("5% Low\nMS-SSIM ↑", default=-1)
    lpips_5p = models.FloatField("5% Low\nLPIPS ↓", default=-1)

    psnr_1p = models.FloatField("1% Low\nPSNR ↑", default=-1)
    ssim_1p = models.FloatField("1% Low\nMS-SSIM ↑", default=-1)
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
