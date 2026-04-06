import csv
import json
import os

from django.core.management.base import BaseCommand, CommandError
from django.urls import reverse

from ...models import EntryStatus, ReconstructionEntry


class Command(BaseCommand):
    help = """
    Rank submissions based on metrics and output to CSV.
    This is *not* what determines the official ranking of competition entries.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--weights", type=str, required=True, help="Path to JSON file with weights"
        )
        parser.add_argument(
            "--min_psnr", type=float, required=True, help="Minimum PSNR for scaling"
        )
        parser.add_argument(
            "--max_psnr", type=float, required=True, help="Maximum PSNR for scaling"
        )
        parser.add_argument(
            "--output", type=str, default="rankings.csv", help="Output CSV filename"
        )
        parser.add_argument(
            "--base_url",
            type=str,
            default="https://singlephotonchallenge.com",
            help="Base URL for eval links",
        )

    def handle(self, *args, **options):
        # Metrics we require in the weights file
        metrics = [
            "psnr_mean",
            "psnr_5p",
            "psnr_1p",
            "ssim_mean",
            "ssim_5p",
            "ssim_1p",
            "lpips_mean",
            "lpips_5p",
            "lpips_1p",
        ]

        min_p = options["min_psnr"]
        max_p = options["max_psnr"]

        entries = ReconstructionEntry.objects.filter(
            process_status=EntryStatus.SUCCESS, is_active=True
        )

        # Load and validate weights
        if not os.path.exists(options["weights"]):
            raise CommandError(f"Weights file {options['weights']} does not exist.")

        try:
            with open(options["weights"], "r") as f:
                weights = json.load(f)
        except json.JSONDecodeError:
            raise CommandError(
                f"Weights file {options['weights']} is not a valid JSON file."
            )

        total_weight = sum(weights.values())
        if total_weight <= 0:
            raise CommandError("Sum of weights must be positive.")

        # Check for missing metrics
        missing = [m for m in metrics if m not in weights]
        if missing:
            raise CommandError(f"Missing weights for metrics: {', '.join(missing)}")

        def scale_psnr(val):
            if val is None or val < 0:
                return 0.0
            return max(0.0, min(1.0, (val - min_p) / (max_p - min_p)))

        def norm_val(val):
            if val is None or val < 0:
                return 0.0
            return max(0.0, min(1.0, val))

        def norm_lpips(val):
            if val is None or val < 0:
                return 0.0
            return max(0.0, min(1.0, 1.0 - val))

        def score_entry(entry):
            score = (
                weights["psnr_mean"] * scale_psnr(entry.psnr_mean)
                + weights["psnr_5p"] * scale_psnr(entry.psnr_5p)
                + weights["psnr_1p"] * scale_psnr(entry.psnr_1p)
                + weights["ssim_mean"] * norm_val(entry.ssim_mean)
                + weights["ssim_5p"] * norm_val(entry.ssim_5p)
                + weights["ssim_1p"] * norm_val(entry.ssim_1p)
                + weights["lpips_mean"] * norm_lpips(entry.lpips_mean)
                + weights["lpips_5p"] * norm_lpips(entry.lpips_5p)
                + weights["lpips_1p"] * norm_lpips(entry.lpips_1p)
            )
            eval_link = f"{options['base_url']}{reverse('eval:detail', args=[entry.pk])}"

            return {
                "Account email": entry.creator.email,
                "Submission id": str(entry.uuid),
                "Evaluation link": eval_link,
                "Final score": score / total_weight,
            }

        # Sort by score descending and save to CSV
        rankings = [score_entry(entry) for entry in entries]
        rankings.sort(key=lambda x: x["Final score"], reverse=True)

        with open(options["output"], "w", newline="") as csvfile:
            fieldnames = ["Account email", "Submission id", "Evaluation link", "Final score"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for rank in rankings:
                writer.writerow(rank)

        self.stdout.write(self.style.SUCCESS(f"Rankings saved to {options['output']}"))
