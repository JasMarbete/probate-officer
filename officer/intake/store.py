"""Read and write case files, which are JSON files in data/cases/.

This is the only place that touches case files on disk. Everything else asks
the store for a Case object, so file handling stays in one module.
"""

import json
import shutil

from pydantic import ValidationError

import config
from officer.models import Case


def _case_path(case_id, directory):
    # A case lives in <directory>/<case_id>.json.
    return directory / f"{case_id}.json"


def load_case(case_id, directory=None):
    """Load and validate one case. Raises FileNotFoundError or ValueError with a clear message."""
    # The default is read at call time, not at import time, so tests can point the store elsewhere.
    directory = directory or config.CASES_DIR
    path = _case_path(case_id, directory)
    if not path.exists():
        raise FileNotFoundError(f"no case {case_id} in {directory}")
    try:
        return Case.model_validate_json(path.read_text())
    except ValidationError as error:
        # Re-raise with the case ID, so the owner knows which file to fix.
        raise ValueError(f"case {case_id} is invalid: {error}") from error


def save_case(case, directory=None):
    """Write a case back to disk as indented JSON."""
    directory = directory or config.CASES_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = _case_path(case.case_id, directory)
    # model_dump(mode="json") turns the date into a string that JSON can hold.
    path.write_text(json.dumps(case.model_dump(mode="json"), indent=2) + "\n")


def list_cases(directory=None):
    """Return the sorted IDs of every case file in the folder."""
    directory = directory or config.CASES_DIR
    return sorted(path.stem for path in directory.glob("*.json"))


def reset_case(case_id):
    """Copy a clean golden case over the working copy, so an eval run starts from known data."""
    source = _case_path(case_id, config.GOLDEN_DIR)
    if not source.exists():
        raise FileNotFoundError(f"no case {case_id} in {config.GOLDEN_DIR}")
    config.CASES_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, _case_path(case_id, config.CASES_DIR))
