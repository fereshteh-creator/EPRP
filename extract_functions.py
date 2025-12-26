# Entry point: extract code snippets from downloaded repos and store in corpus_functions.jsonl
from __future__ import annotations
import ast
import json
import hashlib
import os
import sys
from pathlib import Path
from typing import Iterable, List, Set

from utils.normalize import normalize_code
from utils.io_utils import DATA_DIR, log

RAW_DIR = DATA_DIR / "raw_repos"
OUT_PATH = DATA_DIR / "corpus_functions.jsonl"

# Supported languages and their file extensions (case-insensitive)
LANGUAGE_EXTS = {
    "python": [".py"],
    "java": [".java"],
    "javascript": [".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx"],
    "go": [".go"],
    "ruby": [".rb"],
    "scala": [".scala"],
    "lua": [".lua"],
    "perl": [".pl", ".pm"],
    "sql": [".sql"],
    "haskell": [".hs"],
    "rust": [".rs"],
    "fortran": [".f", ".for", ".f90"],
    "assembly": [".s", ".asm"],
    "c":[".c", ".h"],
    "julia": [".jl"],
    # Directory marker only; we still treat .ts/.tsx as javascript in EXT_TO_LANGUAGE
    "typescript": [],
}
EXT_TO_LANGUAGE = {
    ext.lower(): lang
    for lang, exts in LANGUAGE_EXTS.items()
    for ext in exts
}

BUILTINS = set(dir(__builtins__))


def _read_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()


def _segment_python(code: str, node: ast.AST) -> str:
    """Return the source segment for ast node, with a safe fallback."""
    try:
        if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
            lines = code.splitlines()
            return "\n".join(lines[node.lineno - 1: node.end_lineno])
    except Exception:
        pass
    return code


def _attach_parents(tree: ast.AST):
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            setattr(child, "parent", parent)


def _qualified_name(node: ast.AST) -> str:
    parts = []
    cur = node
    while cur is not None:
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            parts.append(cur.name)
        elif isinstance(cur, ast.ClassDef):
            parts.append(cur.name)
        cur = getattr(cur, "parent", None)
    return "::".join(reversed(parts))


class _NameCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.loads: Set[str] = set()
        self.stores: Set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.loads.add(node.id)
        elif isinstance(node.ctx, (ast.Store, ast.Param)):
            self.stores.add(node.id)
        self.generic_visit(node)


def _is_standalone_python(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    # Skip typical methods
    if node.args.args:
        first = node.args.args[0].arg
        if first in ("self", "cls"):
            return False
    collector = _NameCollector()
    collector.visit(node)
    allowed = set(collector.stores)
    allowed.update(arg.arg for arg in node.args.args)
    allowed.update(BUILTINS)
    for name in collector.loads:
        if name in allowed:
            continue
        return False
    return True


def _extract_python_file(path: Path, lic: str, repo_dir: Path, rel_path: str, min_lines: int) -> List[dict]:
    code = _read_text(path)
    if not code.strip():
        return []

    try:
        tree = ast.parse(code)
    except Exception:
        return []

    _attach_parents(tree)

    out = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        original = _segment_python(code, node)
        if original.count("\n") + 1 < min_lines:
            continue
        norm = normalize_code(original, language="python")
        if not norm.strip():
            continue
        standalone = _is_standalone_python(node)
        obj = {
            "license": lic,
            "repo_dir": str(repo_dir.name),
            "filepath": rel_path,
            "qualified_name": _qualified_name(node),
            "language": "python",
            "n_lines": original.count("\n") + 1,
            "sha256_original": _hash(original),
            "sha256_normalized": _hash(norm),
            "code_original": original,
            "code_normalized": norm,
            "standalone": standalone,
        }
        out.append(obj)
    return out


def _extract_file_blob(path: Path, lic: str, repo_dir: Path, rel_path: str, language: str, min_lines: int) -> List[dict]:
    """
    Fallback extractor for languages where we do not have structured parsing.
    Treat the entire file as a snippet if it is large enough.
    """
    code = _read_text(path)
    if not code.strip():
        return []
    n_lines = code.count("\n") + 1
    if n_lines < min_lines:
        return []
    norm = normalize_code(code, language=language)
    if not norm.strip():
        return []
    qualified = f"{rel_path.replace(os.sep, '::')}"
    obj = {
        "license": lic,
        "repo_dir": str(repo_dir.name),
        "filepath": rel_path,
        "qualified_name": qualified,
        "language": language,
        "n_lines": n_lines,
        "sha256_original": _hash(code),
        "sha256_normalized": _hash(norm),
        "code_original": code,
        "code_normalized": norm,
        "standalone": False,
    }
    return [obj]


def _iter_source_files(repo_dir: Path) -> Iterable[tuple[Path, str]]:
    for path in repo_dir.rglob("*"):
        if not path.is_file():
            continue
        language = EXT_TO_LANGUAGE.get(path.suffix.lower())
        if language:
            yield path, language


def _iter_repo_dirs(license_filter: Set[str] | None = None) -> Iterable[tuple[str, Path]]:
    for lic_dir in sorted(RAW_DIR.iterdir()):
        if not lic_dir.is_dir():
            continue
        lic = lic_dir.name
        if license_filter and lic.lower() not in license_filter:
            continue
        for child in sorted(lic_dir.iterdir()):
            if not child.is_dir():
                continue
            child_lower = child.name.lower()
            if child_lower in LANGUAGE_EXTS:
                for repo_dir in sorted(child.iterdir()):
                    if repo_dir.is_dir():
                        yield lic, repo_dir
            else:
                yield lic, child


def walk_and_extract(
    min_lines: int = 6,
    languages: Iterable[str] | None = None,
    licenses: Iterable[str] | None = None,
    out_path: Path | None = None,
):
    lang_filter = {l.lower() for l in languages} if languages else None
    license_filter = {l.lower() for l in licenses} if licenses else None
    target_path = out_path or OUT_PATH
    count_files = 0
    count_snippets = 0
    seen_hashes: Set[str] = set()
    with target_path.open("a", encoding="utf-8") as fout:
        for lic, repo_dir in _iter_repo_dirs(license_filter=license_filter):
            for src_path, language in _iter_source_files(repo_dir):
                if lang_filter and language.lower() not in lang_filter:
                    continue
                rel_path = str(src_path.relative_to(repo_dir))
                if language == "python":
                    snippets = _extract_python_file(src_path, lic, repo_dir, rel_path, min_lines)
                else:
                    snippets = _extract_file_blob(src_path, lic, repo_dir, rel_path, language, min_lines)
                count_files += 1
                for snip in snippets:
                    sha = snip.get("sha256_normalized")
                    if sha and sha in seen_hashes:
                        continue
                    if sha:
                        seen_hashes.add(sha)
                    fout.write(json.dumps(snip, ensure_ascii=False) + "\n")
                    count_snippets += 1
                if count_files % 50 == 0:
                    log(f"Processed {count_files} files / {count_snippets} snippets...")
    log(f"Done. Files processed: {count_files}, snippets extracted: {count_snippets}")
    log(f"Output -> {target_path}")


if __name__ == "__main__":
    args = sys.argv[1:]
    min_lines = 6
    languages: List[str] | None = None
    licenses: List[str] | None = None
    out_path: Path | None = None
    if args:
        try:
            min_lines = int(args[0])
            args = args[1:]
        except Exception:
            pass
    for a in args:
        if a.startswith("--languages="):
            langs = a.split("=", 1)[1]
            languages = [s.strip().lower() for s in langs.split(",") if s.strip()]
        elif a.startswith("--licenses="):
            lic_str = a.split("=", 1)[1]
            licenses = [s.strip().lower() for s in lic_str.split(",") if s.strip()]
        elif a.startswith("--out="):
            out_path = Path(a.split("=", 1)[1]).expanduser().resolve()
    walk_and_extract(min_lines=min_lines, languages=languages, licenses=licenses, out_path=out_path)
