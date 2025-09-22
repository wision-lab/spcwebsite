import random
import string

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.utils import timezone

from ...models import EntryStatus, EntryVisibility, ReconstructionEntry


class Command(BaseCommand):
    help = "Creates Users and Random Entries"

    def add_arguments(self, parser):
        parser.add_argument("count", type=int)

    def handle(self, *args, **options):
        mails = ["user1@test.test", "user2@test.test", "user3@test.test"]
        for usermail in mails:
            try:
                get_user_model().objects.get(email=usermail)
            except ObjectDoesNotExist:
                get_user_model().objects.create_user(
                    email=usermail,
                    university="University of Testing",
                    password="singlephotoncameras!",
                )
                self.stdout.write(f"Created user {usermail}")
        users = get_user_model().objects.filter(email__in=mails)

        for _ in range(options["count"]):
            creator = random.choice(users)
            methodname = "".join(random.choices(string.ascii_uppercase, k=20))
            entry = ReconstructionEntry.objects.create(
                creator=creator,
                name=methodname,
                pub_date=timezone.now(),
                visibility=random.choice(EntryVisibility.choices)[0],
                process_status=random.choice(EntryStatus.choices)[0],
                psnr_mean=random.uniform(0, 50),
                ssim_mean=random.uniform(0, 1),
                lpips_mean=random.uniform(0, 1),
            )
            entry.save()
