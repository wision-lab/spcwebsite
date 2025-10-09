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

    def handle(self, *args, **options):
        with open(conf_path := options["config"], "r") as f:
            config = json.load(f)

        with self.get_user() as user:
            for submission in track(config):
                path = Path(conf_path).parent / submission.pop("path")
                entry = ReconstructionEntry(
                    creator=user, pub_date=timezone.now(), process_status=EntryStatus.WAIT_PROC, **submission
                )
                shutil.copy(path, entry.upload_path)
                entry.save()
