import os
from pathlib import Path

from django.conf import settings

RESULTENTRY_NAME_MAX_LENGTH = 100
MAX_UPLOAD_SIZE = 50 * 1024 * 1024
MAX_UPLOAD_SIZE_STR = "50MB"

EVAL_DIRECTORY = Path(os.environ["SPC_EVALDIR"])
EVAL_FILES = set(
    str(p.relative_to(EVAL_DIRECTORY)) for p in EVAL_DIRECTORY.glob("**/*.png")
)
SAMPLE_FRAMES_DIRECTORY = settings.BASE_DIR / "static" / "samples"

UPLOAD_DIRECTORY = Path(os.environ["SPC_UPLOADDIR"])
UPLOAD_DIRECTORY.mkdir(exist_ok=True, parents=True)

MEDIA_DIRECTORY = Path(settings.MEDIA_ROOT)
MEDIA_DIRECTORY.mkdir(exist_ok=True, parents=True)
