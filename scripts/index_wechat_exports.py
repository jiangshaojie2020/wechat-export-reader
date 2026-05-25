#!/usr/bin/env python3
"""Build a compact index for user-exported WeChat material.

This script is intentionally conservative: it only scans a user-provided folder
and never attempts to read WeChat databases, credentials, or app containers.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import mimetypes
import re
import zipfile
from dataclasses import dataclass, asdict
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree


DEFAULT_INPUT = Path("/Volumes/T7/AI/微信导出")
INDEX_DIR_NAME = ".codex-wechat-index"
TEXT_EXTS = {".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".log"}
DOCX_EXTS = {".docx"}
PDF_EXTS = {".pdf"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".tif", ".tiff"}
MAX_TEXT_CHARS = 120_000
SNIPPET_CHARS = 700


@dataclass
class Record:
    path: str
    relpath: str
    kind: str
    suffix: str
    size_bytes: int
    modified: str
    sha256_12: str
    title: str
    text_chars: int
    line_count: int
    date_hits: list[str]
    keyword_hits: list[str]
    snippet: str


def sha256_12(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def clean_text(text: str) -> str:
    text = unescape(text)
    text = text.replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def read_text_file(path: Path) -> str:
    data = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gb18030", "big5", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def read_csv_file(path: Path) -> str:
    raw = read_text_file(path)
    dialect = csv.excel_tab if path.suffix.lower() == ".tsv" else csv.excel
    rows: list[str] = []
    try:
        reader = csv.reader(raw.splitlines(), dialect=dialect)
        for i, row in enumerate(reader):
            rows.append(" | ".join(cell.strip() for cell in row if cell.strip()))
            if i >= 400:
                break
    except csv.Error:
        return raw
    return "\n".join(row for row in rows if row)


def read_docx(path: Path) -> str:
    parts: list[str] = []
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path) as zf:
        for name in ("word/document.xml",):
            if name not in zf.namelist():
                continue
            root = ElementTree.fromstring(zf.read(name))
            for para in root.findall(".//w:p", ns):
                texts = [t.text or "" for t in para.findall(".//w:t", ns)]
                if texts:
                    parts.append("".join(texts))
    return "\n".join(parts)


def classify(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in TEXT_EXTS:
        return "text"
    if suffix in DOCX_EXTS:
        return "docx"
    if suffix in PDF_EXTS:
        return "pdf"
    if suffix in IMAGE_EXTS:
        return "image"
    mime, _ = mimetypes.guess_type(path.name)
    if mime:
        return mime.split("/")[0]
    return "attachment"


def extract_text(path: Path, kind: str) -> str:
    suffix = path.suffix.lower()
    try:
        if kind == "text" and suffix in {".csv", ".tsv"}:
            return read_csv_file(path)
        if kind == "text":
            return read_text_file(path)
        if kind == "docx":
            return read_docx(path)
    except Exception as exc:  # Keep indexing robust for mixed export folders.
        return f"[unreadable text: {type(exc).__name__}: {exc}]"
    if kind == "pdf":
        return "[pdf attachment: text extraction not enabled in this lightweight indexer]"
    if kind == "image":
        return "[image attachment]"
    return "[attachment]"


def title_from_text(path: Path, text: str) -> str:
    for line in text.splitlines():
        line = line.strip("#：: \t")
        if line:
            return line[:120]
    return path.stem[:120]


def date_hits(text: str) -> list[str]:
    patterns = [
        r"\b20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}日?\b",
        r"\b\d{1,2}[-/.月]\d{1,2}日?\b",
        r"\b\d{1,2}:\d{2}(?::\d{2})?\b",
    ]
    found: list[str] = []
    for pat in patterns:
        found.extend(re.findall(pat, text))
    return list(dict.fromkeys(found))[:20]


def keyword_hits(text: str) -> list[str]:
    keywords = [
        "待办",
        "明天",
        "今天",
        "会议",
        "纪要",
        "截止",
        "deadline",
        "todo",
        "安排",
        "报告",
        "论文",
        "数据",
        "附件",
        "确认",
        "回复",
    ]
    low = text.lower()
    return [kw for kw in keywords if kw.lower() in low]


def iter_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if INDEX_DIR_NAME in path.parts:
            continue
        if path.name.startswith("."):
            continue
        yield path


def build_record(path: Path, root: Path) -> Record:
    kind = classify(path)
    text = clean_text(extract_text(path, kind))[:MAX_TEXT_CHARS]
    stat = path.stat()
    return Record(
        path=str(path),
        relpath=str(path.relative_to(root)),
        kind=kind,
        suffix=path.suffix.lower(),
        size_bytes=stat.st_size,
        modified=datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        sha256_12=sha256_12(path),
        title=title_from_text(path, text),
        text_chars=len(text),
        line_count=text.count("\n") + (1 if text else 0),
        date_hits=date_hits(text),
        keyword_hits=keyword_hits(text),
        snippet=text[:SNIPPET_CHARS],
    )


def write_outputs(root: Path, records: list[Record]) -> Path:
    out = root / INDEX_DIR_NAME
    out.mkdir(parents=True, exist_ok=True)

    with (out / "index.jsonl").open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")

    by_kind: dict[str, int] = {}
    for rec in records:
        by_kind[rec.kind] = by_kind.get(rec.kind, 0) + 1

    lines = [
        "# WeChat Export Index",
        "",
        f"- Source folder: `{root}`",
        f"- Generated: `{datetime.now().isoformat(timespec='seconds')}`",
        f"- Files indexed: `{len(records)}`",
        "",
        "## File Types",
        "",
    ]
    for kind, count in sorted(by_kind.items()):
        lines.append(f"- `{kind}`: {count}")

    lines.extend(["", "## High-Signal Records", ""])
    scored = sorted(
        records,
        key=lambda r: (len(r.keyword_hits), len(r.date_hits), r.text_chars),
        reverse=True,
    )
    for rec in scored[:80]:
        keys = ", ".join(rec.keyword_hits[:8]) if rec.keyword_hits else "none"
        dates = ", ".join(rec.date_hits[:5]) if rec.date_hits else "none"
        lines.extend(
            [
                f"### {rec.relpath}",
                "",
                f"- Kind: `{rec.kind}`; size: `{rec.size_bytes}` bytes; modified: `{rec.modified}`",
                f"- Title: {rec.title}",
                f"- Keyword hits: {keys}",
                f"- Date hits: {dates}",
                "",
                "```text",
                rec.snippet[:500],
                "```",
                "",
            ]
        )

    (out / "index_summary.md").write_text("\n".join(lines), encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Index user-exported WeChat files for Codex.")
    parser.add_argument("folder", nargs="?", default=str(DEFAULT_INPUT), help="WeChat export folder")
    args = parser.parse_args(argv)

    root = Path(args.folder).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)

    records = [build_record(path, root) for path in iter_files(root)]
    out = write_outputs(root, records)
    print(f"Indexed {len(records)} files")
    print(f"Summary: {out / 'index_summary.md'}")
    print(f"JSONL: {out / 'index.jsonl'}")
    if not records:
        print("No export files found yet. Put WeChat exports into the source folder and rerun.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
