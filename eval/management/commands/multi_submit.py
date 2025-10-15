import hashlib
import json
import shutil
from contextlib import contextmanager
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.utils import timezone
from rich.progress import track

from ...models import EntryStatus, ReconstructionEntry


class Command(BaseCommand):
    help = "A batch submit utility"

    def add_arguments(self, parser):
        parser.add_argument("config", type=str)

    @contextmanager
    def get_user(self, email="uploader@test.test"):
        # Make user that is not verified and only temporarily active
        # such that it cannot be logged into from the server
        try:
            user = get_user_model().objects.get(email=email)
        except ObjectDoesNotExist:
            self.stdout.write(f"Created user {email}")
            user = get_user_model().objects.create_user(
                email=email,
                university="University of Baselines",
                password="singlephotoncameras!",
                is_active=True,
            )
        user.is_active = True
        yield user
        user.is_active = False
        user.save()

    @staticmethod
    def md5sum(path):
        with open(path, "rb") as f:
            file_hash = hashlib.md5()
            while chunk := f.read(8192):
                file_hash.update(chunk)
        return file_hash.hexdigest()

    def handle(self, *args, **options):
        with open(conf_path := options["config"], "r") as f:
            config = json.load(f)

        with self.get_user() as user:
            for submission in track(config):
                path = Path(conf_path).parent / submission.pop("path")
                entry = ReconstructionEntry(
                    creator=user,
                    pub_date=timezone.now(),
                    process_status=EntryStatus.WAIT_PROC,
                    md5sum=self.md5sum(path),
                    **submission,
                )
                shutil.copy(path, entry.upload_path)
                entry.save()
