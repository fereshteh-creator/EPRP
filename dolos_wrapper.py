import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List


# ---------- Docker basics ----------

def _resolve_docker() -> str:
    """
    Find the docker binary.
    """
    for key in ("DOLOS_DOCKER_BIN", "DOCKER_BIN"):
        val = os.environ.get(key)
        if val and Path(val).exists():
            return val
    return shutil.which("docker") or "docker"


DOCKER_BIN = _resolve_docker()


def _docker_image() -> str:
    """
    Name of the Dolos Docker image to use.

    Default set to your working image name.
    You can override with env var: DOLOS_DOCKER_IMAGE
    """
    return os.environ.get("DOLOS_DOCKER_IMAGE", "copyleft-guard-data")


def _docker_available() -> bool:
    if not DOCKER_BIN:
        return False
    try:
        pr = subprocess.run(
            [DOCKER_BIN, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return pr.returncode == 0
    except Exception:
        return False


# ---------- Language -> file extension mapping ----------

LANG_EXT = {
    "assembly": ".s",      
    "c": ".c",
    "fortran": ".f90",       
    "go": ".go",
    "haskell": ".hs",
    "java": ".java",
    "javascript": ".js",
    "julia": ".jl",
    "lua": ".lua",
    "perl": ".pl",
    "python": ".py",
    "ruby": ".rb",
    "rust": ".rs",
    "scala": ".scala",
    "sql": ".sql",
}


def _ext_for_language(language: str) -> str:
    return LANG_EXT.get((language or "").lower(), ".txt")


# ---------- Path helpers (Windows-friendly) ----------

def _docker_host_path(p: Path) -> str:
    """
    Convert a local host path into a Docker-friendly volume mount string.

    On Windows, Docker prefers forward slashes.
    Example: C:\\Users\\Me\\AppData\\Local\\Temp\\x -> C:/Users/Me/AppData/Local/Temp/x
    """
    return str(p).replace("\\", "/")


# ---------- Core helpers ----------

def _run_dolos_pair(
    code1: str,
    code2: str,
    language: str = "python",
) -> float:
    """
    Run Dolos (via Docker) on two code snippets and return the similarity score.

    - Writes both snippets to a temp dir.
    - Mounts that dir as /workspace in the container.
    - Calls: dolos run -V -l <language> /workspace/orig.ext /workspace/gen.ext
    - Parses the "Similarity score: X" line from stdout.

    Notes:
    - Perl requires explicit language flag (Dolos can't auto-detect .pl), we always pass -l anyway.
    - Git Bash/MSYS path conversion can break /workspace/... args; we set MSYS env vars defensively.
    """
    if not _docker_available():
        return 0.0

    docker_image = _docker_image()
    ext = _ext_for_language(language)

    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        file1 = tmpdir / f"orig{ext}"
        file2 = tmpdir / f"gen{ext}"

        file1.write_text(code1 or "", encoding="utf-8")
        file2.write_text(code2 or "", encoding="utf-8")

        host_mount = _docker_host_path(tmpdir)

        cmd = [
            DOCKER_BIN,
            "run",
            "--rm",
            "-v",
            f"{host_mount}:/workspace",
            docker_image,
            "run",
            "-V",
            "-l",
            language,
            f"/workspace/orig{ext}",
            f"/workspace/gen{ext}",
        ]

        env = os.environ.copy()
        # Defensive: avoid MSYS/Git Bash path mangling if notebook is launched from Git Bash
        env["MSYS_NO_PATHCONV"] = "1"
        env["MSYS2_ARG_CONV_EXCL"] = "*"

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )

        if proc.returncode != 0:
            # Uncomment for debugging:
            print("DOLOS STDOUT:\n", proc.stdout)
            print("DOLOS STDERR:\n", proc.stderr)
            return 0.0

        m = re.search(r"Similarity score:\s*([0-9]*\.?[0-9]+)", proc.stdout or "")
        if not m:
            return 0.0

        try:
            return float(m.group(1))
        except Exception:
            return 0.0


# ---------- Public API used by your notebook ----------

def dolos_compare(code1: str, code2: str, language: str = "python") -> float:
    """
    Compare two snippets with Dolos via Docker and return a similarity score.

    Your notebook calls: dolos_compare(original_code, generated_code, language=LANGUAGE)
    """
    if not code1 or not code2:
        return 0.0
    return _run_dolos_pair(code1, code2, language)


def dolos_compare_many(
    query_code: str,
    candidate_codes: List[str],
    language: str = "python",
) -> List[float]:
    """
    Many-to-one comparison:
    - runs dolos_compare(query_code, candidate, language) for each candidate
    - returns a list of similarity scores.
    """
    if not query_code:
        return [0.0 for _ in candidate_codes]

    sims: List[float] = []
    for cand in candidate_codes:
        sims.append(dolos_compare(query_code, cand, language=language))
    return sims
