import os
from pathlib import Path

RESULTENTRY_NAME_MAX_LENGTH = 100
MAX_UPLOAD_SIZE = 50 * 1024 * 1024
MAX_UPLOAD_SIZE_STR = "50MB"

EVAL_DIRECTORY = Path(os.environ["SPC_EVALDIR"])
EVAL_FILES = set(
    str(p.relative_to(EVAL_DIRECTORY)) for p in EVAL_DIRECTORY.glob("**/*.png")
)

UPLOAD_DIRECTORY = Path(os.environ["SPC_UPLOADDIR"])
UPLOAD_DIRECTORY.mkdir(exist_ok=True, parents=True)
