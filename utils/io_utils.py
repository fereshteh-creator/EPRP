# Utility functions for file IO and logging
import os
import pathlib
from datetime import datetime

# Resolve base dirs relative to this file:
# src/utils/io_utils.py -> src/utils -> src -> copyleft-guard
BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw_repos"
LOG_DIR = DATA_DIR / "logs"
LOG_FILE = LOG_DIR / "fetch.log"


def ensure_dirs():
    """
    Make sure data directories exist before we start writing.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def safe_repo_dir(license_spdx: str, owner: str, repo: str, language: str = None) -> pathlib.Path:
    """
    Create/return the directory where we'll store code for a given repo
    under a given license (and optionally language).

    Example:
    data/raw_repos/GPL-3.0/python/thealgorithms_python/
    """
    repo_dir_name = f"{owner}_{repo}"
    out_dir = RAW_DIR / license_spdx
    if language:
        out_dir = out_dir / language
    out_dir = out_dir / repo_dir_name
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def save_code_file(base_dir: pathlib.Path, rel_path: str, content: str):
    """
    Save a code file under the base_dir, preserving subfolders.
    """
    out_path = base_dir / rel_path
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8", errors="ignore")
    except OSError as e:
        # e.g. Windows MAX_PATH (WinError 206) on very deep trees like node_modules
        msg = f"[WARN] Skipping file with too-long/invalid path: {out_path} ({e})"
        print(msg)
        try:
            log(msg)
        except Exception:
            pass


def log(msg: str):
    """
    Append a log line to data/logs/fetch.log and also print it.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().isoformat()
    line = f"[{timestamp}] {msg}"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
    print(line)
