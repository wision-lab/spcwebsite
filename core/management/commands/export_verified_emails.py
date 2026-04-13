import csv
import sys

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Export active and verified user emails as a CSV."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            type=str,
            help="Path to the output CSV file (default: stdout)",
        )

    def handle(self, *args, **options):
        output_file = options.get("output")
        users = User.objects.filter(is_active=True, is_verified=True)

        if output_file:
            try:
                with open(output_file, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Email"])
                    for user in users:
                        writer.writerow([user.email])
                self.stdout.write(self.style.SUCCESS(f"Successfully exported {users.count()} emails to {output_file}"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error writing to file: {e}"))
        else:
            writer = csv.writer(sys.stdout)
            writer.writerow(["Email"])
            for user in users:
                writer.writerow([user.email])
