#!/usr/bin/env python3
"""compare_bytes.py -- byte- and character-level comparison of two files.

Stdlib only. This is the instrument for detecting whether a presentation
layer (clipboard, terminal, editor, file write) altered content in transit.
Both files are opened read-only in binary mode and are never modified.

Usage:
    python3 compare_bytes.py [--json] FILE_A FILE_B

Each detected difference is classified as one of:
    line-ending               CRLF/LF/CR conversion
    trailing-whitespace       spaces/tabs added or removed before a newline/EOF
    invisible-character       insertion/removal of zero-width, bidi, tag,
                              variation-selector or other format characters
    typographic-substitution  e.g. ' -> U+2019, " -> U+201C, - -> U+2014
    normalization             NFC/NFD re-composition (same text, different bytes)
    other                     anything else

Exit codes: 0 = byte-identical, 1 = files differ, 2 = error.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import sys
import unicodedata

# Shared code point sets live in scan_unicode.py (same directory).
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import scan_unicode  # noqa: E402

INVISIBLE_ALL = (
    scan_unicode.INVISIBLE_SET
    | scan_unicode.BIDI_SET
    | scan_unicode.TAG_SET
    | scan_unicode.VARIATION_SELECTOR_SET
)

MAX_REPORTED_DIFFS = 500
MAX_SEGMENT_BYTES = 64      # hex display cap per differing byte segment
MAX_SEGMENT_CHARS = 50      # code point list cap per differing char segment
CONTEXT_RADIUS = 30


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cps(segment: str) -> list[dict]:
    return [
        {"codepoint": scan_unicode.cp_label(ord(c)), "name": scan_unicode.cp_name(ord(c))}
        for c in segment[:MAX_SEGMENT_CHARS]
    ]


def map_typographic(segment: str) -> str:
    """Fold typographic/confusable characters to their nearest ASCII form."""
    return "".join(scan_unicode.ASCII_EQUIV.get(ord(c), c) for c in segment)


def classify_difference(a_seg: str, b_seg: str, a_text: str, b_text: str,
                        a_end: int, b_end: int) -> str:
    """Classify one non-equal difflib opcode between decoded texts."""
    line_chars = {"\r", "\n"}
    ws_chars = {" ", "\t"}

    a_set = set(a_seg)
    b_set = set(b_seg)

    # 1. line-ending change: both sides consist only of CR/LF characters
    if (a_set or b_set) and a_set <= line_chars and b_set <= line_chars:
        return "line-ending"

    # 2. trailing-whitespace: pure space/tab change immediately before a
    #    line break or end-of-file on both sides
    def at_line_end(text: str, idx: int) -> bool:
        return idx >= len(text) or text[idx] in ("\n", "\r")

    if a_set <= ws_chars and b_set <= ws_chars and (a_set or b_set):
        if at_line_end(a_text, a_end) and at_line_end(b_text, b_end):
            return "trailing-whitespace"

    # 3. invisible-character insertion/removal: the changed characters are
    #    all zero-width / bidi / tag / variation-selector / format chars
    def all_invisible(segment: str) -> bool:
        return bool(segment) and all(
            ord(c) in INVISIBLE_ALL or unicodedata.category(c) == "Cf"
            for c in segment
        )

    if (not a_seg and all_invisible(b_seg)) or (not b_seg and all_invisible(a_seg)):
        return "invisible-character"
    if a_seg and b_seg:
        # replace where the only change is invisible chars appearing/vanishing
        a_vis = "".join(c for c in a_seg if not all_invisible(c))
        b_vis = "".join(c for c in b_seg if not all_invisible(c))
        if a_vis == b_vis and a_seg != b_seg:
            return "invisible-character"

    # 4. typographic substitution: segments equal after folding smart
    #    punctuation to nearest ASCII
    if a_seg != b_seg and map_typographic(a_seg) == map_typographic(b_seg):
        return "typographic-substitution"

    # 5. normalization: same text under NFC (or NFD) -- recomposition only.
    #    Include one preceding char of context so an inserted combining mark
    #    can recompose with its base letter.
    a_ctx = a_text[max(0, a_end - len(a_seg) - 1):a_end]
    b_ctx = b_text[max(0, b_end - len(b_seg) - 1):b_end]
    for form in ("NFC", "NFD"):
        if unicodedata.normalize(form, a_ctx) == unicodedata.normalize(form, b_ctx):
            return "normalization"
        if a_seg and b_seg and unicodedata.normalize(form, a_seg) == unicodedata.normalize(form, b_seg):
            return "normalization"

    return "other"


def byte_level_diff(data_a: bytes, data_b: bytes) -> list[dict]:
    sm = difflib.SequenceMatcher(None, data_a, data_b, autojunk=False)
    diffs = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if len(diffs) >= MAX_REPORTED_DIFFS:
            diffs.append({"truncated": True,
                          "note": "diff list capped at %d entries" % MAX_REPORTED_DIFFS})
            break
        a_seg = data_a[i1:i2]
        b_seg = data_b[j1:j2]
        a_ctx = data_a[max(0, i1 - CONTEXT_RADIUS):i2 + CONTEXT_RADIUS]
        b_ctx = data_b[max(0, j1 - CONTEXT_RADIUS):j2 + CONTEXT_RADIUS]
        diffs.append({
            "op": tag,
            "a_byte_range": [i1, i2],
            "b_byte_range": [j1, j2],
            "a_bytes_hex": a_seg[:MAX_SEGMENT_BYTES].hex(" ").upper()
                           + (" ..." if len(a_seg) > MAX_SEGMENT_BYTES else ""),
            "b_bytes_hex": b_seg[:MAX_SEGMENT_BYTES].hex(" ").upper()
                           + (" ..." if len(b_seg) > MAX_SEGMENT_BYTES else ""),
            "a_decoded": scan_unicode.escape_text(
                a_seg[:MAX_SEGMENT_BYTES].decode("utf-8", errors="replace")),
            "b_decoded": scan_unicode.escape_text(
                b_seg[:MAX_SEGMENT_BYTES].decode("utf-8", errors="replace")),
            "a_context": scan_unicode.escape_text(a_ctx.decode("utf-8", errors="replace")),
            "b_context": scan_unicode.escape_text(b_ctx.decode("utf-8", errors="replace")),
        })
    return diffs


def char_level_diff(text_a: str, text_b: str) -> list[dict]:
    sm = difflib.SequenceMatcher(None, text_a, text_b, autojunk=False)
    diffs = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        if len(diffs) >= MAX_REPORTED_DIFFS:
            diffs.append({"truncated": True,
                          "note": "diff list capped at %d entries" % MAX_REPORTED_DIFFS})
            break
        a_seg = text_a[i1:i2]
        b_seg = text_b[j1:j2]
        classification = classify_difference(a_seg, b_seg, text_a, text_b, i2, j2)
        diffs.append({
            "op": tag,
            "a_char_range": [i1, i2],
            "b_char_range": [j1, j2],
            "a_codepoints": cps(a_seg),
            "b_codepoints": cps(b_seg),
            "a_escaped": scan_unicode.escape_text(a_seg[:MAX_SEGMENT_CHARS]),
            "b_escaped": scan_unicode.escape_text(b_seg[:MAX_SEGMENT_CHARS]),
            "a_context": scan_unicode.escape_text(
                text_a[max(0, i1 - CONTEXT_RADIUS):i2 + CONTEXT_RADIUS]),
            "b_context": scan_unicode.escape_text(
                text_b[max(0, j1 - CONTEXT_RADIUS):j2 + CONTEXT_RADIUS]),
            "classification": classification,
        })
    return diffs


def compare_bytes_data(data_a: bytes, data_b: bytes,
                       path_a: str = "<a>", path_b: str = "<b>") -> dict:
    identical = data_a == data_b
    result = {
        "file_a": {"path": path_a, "sha256": sha256_hex(data_a), "bytes": len(data_a)},
        "file_b": {"path": path_b, "sha256": sha256_hex(data_b), "bytes": len(data_b)},
        "byte_identical": identical,
        "byte_diffs": [],
        "char_diffs": [],
        "classifications": [],
    }
    if identical:
        return result

    result["byte_diffs"] = byte_level_diff(data_a, data_b)

    text_a = data_a.decode("utf-8", errors="replace")
    text_b = data_b.decode("utf-8", errors="replace")
    result["char_diffs"] = char_level_diff(text_a, text_b)
    result["classifications"] = sorted(
        {d["classification"] for d in result["char_diffs"] if "classification" in d}
    )
    return result


def compare_files(path_a: str, path_b: str) -> dict:
    with open(path_a, "rb") as fh:  # read-only, binary: files are never modified
        data_a = fh.read()
    with open(path_b, "rb") as fh:
        data_b = fh.read()
    return compare_bytes_data(data_a, data_b, path_a, path_b)


def render_text(result: dict) -> str:
    lines: list[str] = []
    a = lines.append
    a("=" * 78)
    for key in ("file_a", "file_b"):
        f = result[key]
        a("%s: %s" % (key, f["path"]))
        a("  sha256: %s" % f["sha256"])
        a("  bytes:  %d" % f["bytes"])
    a("byte-identical: %s" % result["byte_identical"])
    if result["byte_identical"]:
        a("=" * 78)
        return "\n".join(lines)
    a("difference classifications present: %s" % ", ".join(result["classifications"]))
    a("-" * 78)
    a("BYTE-LEVEL DIFFERENCES (%d):" % len(result["byte_diffs"]))
    for d in result["byte_diffs"]:
        if d.get("truncated"):
            a("  ... %s" % d["note"])
            break
        a("  [%s] a[%d:%d] b[%d:%d]" % (d["op"], *d["a_byte_range"], *d["b_byte_range"]))
        a("    a bytes: %s   (%s)" % (d["a_bytes_hex"] or "<none>", d["a_decoded"] or "empty"))
        a("    b bytes: %s   (%s)" % (d["b_bytes_hex"] or "<none>", d["b_decoded"] or "empty"))
        a("    a context: %s" % d["a_context"])
        a("    b context: %s" % d["b_context"])
    a("-" * 78)
    a("CHARACTER-LEVEL DIFFERENCES (%d):" % len(result["char_diffs"]))
    for d in result["char_diffs"]:
        if d.get("truncated"):
            a("  ... %s" % d["note"])
            break
        a("  [%s] a[%d:%d] b[%d:%d]  classification: %s"
          % (d["op"], *d["a_char_range"], *d["b_char_range"], d["classification"]))
        a("    a: %s  %s" % (d["a_escaped"] or "<empty>",
                             ["%s %s" % (c["codepoint"], c["name"]) for c in d["a_codepoints"]]))
        a("    b: %s  %s" % (d["b_escaped"] or "<empty>",
                             ["%s %s" % (c["codepoint"], c["name"]) for c in d["b_codepoints"]]))
        a("    a context: %s" % d["a_context"])
        a("    b context: %s" % d["b_context"])
    a("=" * 78)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file_a")
    parser.add_argument("file_b")
    parser.add_argument("--json", action="store_true", help="machine-readable JSON output")
    args = parser.parse_args(argv)

    try:
        result = compare_files(args.file_a, args.file_b)
    except OSError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=True))
    else:
        print(render_text(result))
    return 0 if result["byte_identical"] else 1


if __name__ == "__main__":
    sys.exit(main())
