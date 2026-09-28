#!/usr/bin/env python3
"""Extract plain text from a .docx's word/document.xml (no python-docx dependency —
just zipfile + regex, matching the ad hoc heredoc that got rewritten from scratch
several times in one session) and optionally diff two .docx files' text.

Usage:
    python docx_extract_text.py file.docx                 # print extracted text
    python docx_extract_text.py file_a.docx file_b.docx    # unified diff of extracted text
"""
import re
import sys
import zipfile
import difflib
from pathlib import Path

TAG_RE = re.compile(r"<[^>]+>")
PARA_BREAK_RE = re.compile(r"</w:p>", re.IGNORECASE)


def extract_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    # Insert a newline at paragraph boundaries before stripping tags, so output is readable.
    xml = PARA_BREAK_RE.sub("</w:p>\n", xml)
    text = TAG_RE.sub("", xml)
    # Collapse XML entity leftovers and excess blank lines.
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'")
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


def main():
    if len(sys.argv) not in (2, 3):
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) == 2:
        path = Path(sys.argv[1])
        print(extract_docx_text(path))
        return

    path_a, path_b = Path(sys.argv[1]), Path(sys.argv[2])
    text_a = extract_docx_text(path_a).splitlines()
    text_b = extract_docx_text(path_b).splitlines()
    diff = difflib.unified_diff(text_a, text_b, fromfile=str(path_a), tofile=str(path_b), lineterm="")
    diff_lines = list(diff)
    if not diff_lines:
        print(f"No text differences between {path_a} and {path_b}.")
    else:
        print("\n".join(diff_lines))


if __name__ == "__main__":
    main()
