#!/usr/bin/env python3
"""scan_unicode.py -- Unicode / byte forensics scanner for the watermark audit.

Stdlib only (Python 3.11, unicodedata UCD 14.0.0). Read-only: input files are
opened in binary mode and are NEVER modified. Normalization comparisons are
computed in memory only.

Usage:
    python3 scan_unicode.py [--json | --text] FILE [FILE ...]

Buckets (each distinct code point is assigned to exactly ONE primary bucket,
by the priority order in classify_codepoint; "typographic" and benign letters
are NEVER merged with invisible/hidden counts):

  tag_characters        U+E0000..U+E007F (invisible text smuggling channel)
  variation_selectors   U+FE00..U+FE0F, U+E0100..U+E01EF
  bidi_controls         U+202A..U+202E, U+2066..U+2069, U+200E, U+200F
  invisible_zero_width  U+200B/C/D, U+2060, U+FEFF, U+00AD, U+180E, U+061C,
                        U+2061..U+2064
  space_variants        Zs/Zl/Zp other than U+0020 (incl. U+00A0, U+202F,
                        U+2000..U+200A, U+205F, U+3000, U+1680, U+2028, U+2029)
  control_characters    Cc other than TAB/LF/CR; any other Cf; Co; Cs
  combining_marks       Mn / Mc / Me
  confusable_homoglyph  homoglyph punctuation + Cyrillic/Greek letters found
                        inside otherwise-Latin words
  typographic           smart quotes, en/em dashes, ellipsis, and legitimate
                        non-ASCII letters (e.g. accented Latin) -- BENIGN
  other_non_ascii       any other non-ASCII code point (benign by default)

Exit code: always 0 unless a file cannot be read (then 2).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata

UNNAMED = "<unnamed / not in UCD %s>" % unicodedata.unidata_version

POSITION_CAP = 200          # max stored positions per distinct code point
CONTEXT_CAP = 20            # max stored escaped contexts per distinct code point
CONTEXT_RADIUS = 30         # chars either side of a flagged occurrence

# ---------------------------------------------------------------- code point sets

INVISIBLE_SET = {
    0x200B,  # ZERO WIDTH SPACE
    0x200C,  # ZERO WIDTH NON-JOINER
    0x200D,  # ZERO WIDTH JOINER
    0x2060,  # WORD JOINER
    0xFEFF,  # ZERO WIDTH NO-BREAK SPACE / BOM
    0x00AD,  # SOFT HYPHEN
    0x180E,  # MONGOLIAN VOWEL SEPARATOR
    0x061C,  # ARABIC LETTER MARK
    0x2061,  # FUNCTION APPLICATION
    0x2062,  # INVISIBLE TIMES
    0x2063,  # INVISIBLE SEPARATOR
    0x2064,  # INVISIBLE PLUS
}

BIDI_SET = set(range(0x202A, 0x202F)) | set(range(0x2066, 0x206A)) | {0x200E, 0x200F}

VARIATION_SELECTOR_SET = set(range(0xFE00, 0xFE10)) | set(range(0xE0100, 0xE01F0))

TAG_SET = set(range(0xE0000, 0xE0080))

SPACE_EXPLICIT = (
    {0x00A0, 0x202F, 0x205F, 0x3000, 0x1680, 0x2028, 0x2029}
    | set(range(0x2000, 0x200B))
)

EXPECTED_CONTROLS = {0x09, 0x0A, 0x0D}  # TAB, LF, CR

TYPOGRAPHIC_PUNCT = {
    0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015,   # hyphens/dashes/horizontal bar
    0x2018, 0x2019, 0x201A, 0x201B,                    # single quotes/apostrophe
    0x201C, 0x201D, 0x201E, 0x201F,                    # double quotes
    0x2026,                                            # horizontal ellipsis
}

CONFUSABLE_PUNCT = {
    0x00B4,  # ACUTE ACCENT (apostrophe lookalike)
    0x02BC,  # MODIFIER LETTER APOSTROPHE
    0x037E,  # GREEK QUESTION MARK (looks like ;)
    0x0589,  # ARMENIAN FULL STOP (looks like :)
    0x05C3,  # HEBREW PUNCTUATION SOF PASUQ (looks like :)
    0x2032,  # PRIME
    0x2033,  # DOUBLE PRIME
    0x2044,  # FRACTION SLASH
    0x2215,  # DIVISION SLASH
}

# Cyrillic / Greek letters that are visual homoglyphs of ASCII Latin letters.
HOMOGLYPH_LETTERS = {
    # Cyrillic lower
    0x0430: "a", 0x0435: "e", 0x043E: "o", 0x0440: "p", 0x0441: "c",
    0x0443: "y", 0x0445: "x", 0x0455: "s", 0x0456: "i", 0x0458: "j",
    0x04BB: "h", 0x0501: "d", 0x051B: "q", 0x051D: "w",
    # Cyrillic upper
    0x0410: "A", 0x0412: "B", 0x0415: "E", 0x041A: "K", 0x041C: "M",
    0x041D: "H", 0x041E: "O", 0x0420: "P", 0x0421: "C", 0x0422: "T",
    0x0425: "X", 0x0405: "S", 0x0406: "I", 0x0408: "J",
    # Greek lower
    0x03B1: "a", 0x03B9: "i", 0x03BA: "k", 0x03BD: "v", 0x03BF: "o",
    0x03C1: "p", 0x03C5: "u", 0x03C7: "x",
    # Greek upper
    0x0391: "A", 0x0392: "B", 0x0395: "E", 0x0396: "Z", 0x0397: "H",
    0x0399: "I", 0x039A: "K", 0x039C: "M", 0x039D: "N", 0x039F: "O",
    0x03A1: "P", 0x03A4: "T", 0x03A5: "Y", 0x03A7: "X",
}

# Nearest plain-ASCII equivalents for the comparison column.
ASCII_EQUIV = {
    0x2018: "'", 0x2019: "'", 0x201A: "'", 0x201B: "'",
    0x201C: '"', 0x201D: '"', 0x201E: '"', 0x201F: '"',
    0x2010: "-", 0x2011: "-", 0x2012: "-", 0x2013: "-",
    0x2014: "--", 0x2015: "--",
    0x2026: "...",
    0x00A0: " ", 0x202F: " ", 0x205F: " ", 0x3000: " ", 0x1680: " ",
    0x2028: "\n", 0x2029: "\n",
    0x2032: "'", 0x2033: '"', 0x00B4: "'", 0x02BC: "'",
    0x037E: ";", 0x0589: ":", 0x05C3: ":",
    0x2044: "/", 0x2215: "/",
    0x00AD: "-",  # soft hyphen renders as hyphen when it renders at all
}
ASCII_EQUIV.update({cp: " " for cp in range(0x2000, 0x200B)})
ASCII_EQUIV.update(HOMOGLYPH_LETTERS)

BUCKET_ORDER = [
    "tag_characters",
    "variation_selectors",
    "bidi_controls",
    "invisible_zero_width",
    "space_variants",
    "control_characters",
    "combining_marks",
    "confusable_homoglyph",
    "typographic",
    "other_non_ascii",
]

SUSPICIOUS_BUCKETS = {
    "tag_characters", "variation_selectors", "bidi_controls",
    "invisible_zero_width", "space_variants", "control_characters",
    "confusable_homoglyph",
}

# ---------------------------------------------------------------- helpers


def cp_label(cp: int) -> str:
    return "U+%04X" % cp


def cp_name(cp: int) -> str:
    try:
        return unicodedata.name(chr(cp))
    except ValueError:
        return UNNAMED


def utf8_hex(cp: int) -> str:
    return " ".join("%02X" % b for b in chr(cp).encode("utf-8"))


def escape_text(s: str) -> str:
    """Render text with every non-printable / non-ASCII char as an escape.

    The result is safe to print in any terminal: only U+0020..U+007E survive
    literally (backslash is doubled to keep escapes unambiguous).
    """
    out = []
    for ch in s:
        o = ord(ch)
        if ch == "\\":
            out.append("\\\\")
        elif 0x20 <= o <= 0x7E:
            out.append(ch)
        elif o <= 0xFFFF:
            out.append("\\u%04X" % o)
        else:
            out.append("\\U%08X" % o)
    return "".join(out)


def ascii_equivalent(cp: int) -> str | None:
    """Nearest plain-ASCII equivalent, or None when there is no sensible one."""
    if cp < 0x80:
        return None  # already ASCII
    if cp in ASCII_EQUIV:
        return ASCII_EQUIV[cp]
    ch = chr(cp)
    # fullwidth/halfwidth forms and many compatibility chars fold via NFKC
    nfkc = unicodedata.normalize("NFKC", ch)
    if nfkc != ch and all(ord(c) < 0x80 for c in nfkc):
        return nfkc
    # accented letters: strip combining marks
    nfkd = unicodedata.normalize("NFKD", ch)
    stripped = "".join(c for c in nfkd if not unicodedata.combining(c))
    if stripped and stripped != ch and all(ord(c) < 0x80 for c in stripped):
        return stripped
    return None


def is_latin_letter(cp: int) -> bool:
    if cp < 0x80:
        return chr(cp).isalpha()
    if unicodedata.category(chr(cp))[0] != "L":
        return False
    return cp_name(cp).startswith("LATIN")


def classify_codepoint(cp: int, category: str, confusable_letter: bool = False) -> str | None:
    """Assign one primary bucket, or None for unremarkable ASCII."""
    if cp in TAG_SET:
        return "tag_characters"
    if cp in VARIATION_SELECTOR_SET:
        return "variation_selectors"
    if cp in BIDI_SET:
        return "bidi_controls"
    if cp in INVISIBLE_SET:
        return "invisible_zero_width"
    if cp != 0x20 and (category in ("Zs", "Zl", "Zp") or cp in SPACE_EXPLICIT):
        return "space_variants"
    if category == "Cc" and cp not in EXPECTED_CONTROLS:
        return "control_characters"
    if category in ("Cf", "Co", "Cs"):
        return "control_characters"
    if category in ("Mn", "Mc", "Me"):
        return "combining_marks"
    if cp in CONFUSABLE_PUNCT or (0xFF01 <= cp <= 0xFF5E) or (0xFFE0 <= cp <= 0xFFE6):
        return "confusable_homoglyph"
    if cp in TYPOGRAPHIC_PUNCT:
        return "typographic"
    if cp < 0x80:
        return None
    if category[0] == "L":
        if confusable_letter:
            return "confusable_homoglyph"
        if is_latin_letter(cp):
            return "typographic"  # legitimate accented Latin letters: benign
        return "other_non_ascii"
    return "other_non_ascii"


def find_mixed_script_homoglyphs(text: str) -> dict[int, list[int]]:
    """Positions of Cyrillic/Greek homoglyph letters inside otherwise-Latin words.

    A "word" is a maximal run of letters and combining marks. A homoglyph is
    flagged only when its word also contains at least one Latin letter; fully
    Cyrillic/Greek words are legitimate text and are NOT flagged.
    """
    flagged: dict[int, list[int]] = {}
    word: list[tuple[int, int]] = []  # (position, codepoint)

    def close_word() -> None:
        if not word:
            return
        has_latin = any(is_latin_letter(cp) for _, cp in word)
        if has_latin:
            for pos, cp in word:
                if cp in HOMOGLYPH_LETTERS:
                    flagged.setdefault(cp, []).append(pos)
        word.clear()

    for pos, ch in enumerate(text):
        if unicodedata.category(ch)[0] in ("L", "M"):
            word.append((pos, ord(ch)))
        else:
            close_word()
    close_word()
    return flagged


def make_context(text: str, pos: int) -> str:
    cp = ord(text[pos])
    before = escape_text(text[max(0, pos - CONTEXT_RADIUS):pos])
    after = escape_text(text[pos + 1:pos + 1 + CONTEXT_RADIUS])
    return "%s[[%s]]%s" % (before, cp_label(cp), after)


def decode_tag_runs(text: str) -> list[str]:
    """Decode runs of Unicode tag characters into their hidden ASCII payload."""
    runs: list[str] = []
    current: list[str] = []
    for ch in text:
        cp = ord(ch)
        if cp in TAG_SET:
            if cp == 0xE0001:
                current.append("[TAG-LANG]")
            elif cp == 0xE007F:
                current.append("[TAG-END]")
            else:
                v = cp - 0xE0000
                current.append(chr(v) if 0x20 <= v <= 0x7E else "[TAG-%02X]" % v)
        else:
            if current:
                runs.append("".join(current))
                current = []
    if current:
        runs.append("".join(current))
    return runs


def normalization_report(text: str, original_bytes: bytes) -> dict:
    forms = {}
    for form in ("NFC", "NFD", "NFKC", "NFKD"):
        norm = unicodedata.normalize(form, text)
        norm_bytes = norm.encode("utf-8")
        forms[form] = {
            "is_normalized": unicodedata.is_normalized(form, text),
            "char_count": len(norm),
            "byte_count": len(norm_bytes),
            "sha256": hashlib.sha256(norm_bytes).hexdigest(),
            "differs_from_original": norm != text,
        }
    # Mixture: some sequences composed, some decomposed -- the text is then in
    # neither pure NFC nor pure NFD form.
    mixed = (not forms["NFC"]["is_normalized"]) and (not forms["NFD"]["is_normalized"])
    return {
        "original_sha256": hashlib.sha256(original_bytes).hexdigest(),
        "forms": forms,
        "mixed_normalization": mixed,
    }


# ---------------------------------------------------------------- core scan


def scan_bytes(data: bytes, path: str = "<memory>") -> dict:
    sha256 = hashlib.sha256(data).hexdigest()
    notes: list[str] = []
    utf8_valid = True
    decode_error = None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        utf8_valid = False
        decode_error = {
            "byte_offset": exc.start,
            "reason": exc.reason,
            "bad_bytes_hex": " ".join("%02X" % b for b in data[exc.start:exc.end]),
        }
        notes.append(
            "FILE IS NOT VALID UTF-8 at byte offset %d (%s); analysis continues "
            "on a lossy errors='replace' decode." % (exc.start, exc.reason)
        )
        text = data.decode("utf-8", errors="replace")

    if text.startswith("\ufeff"):
        notes.append("Leading U+FEFF byte-order mark present.")

    mixed_homoglyphs = find_mixed_script_homoglyphs(text)

    # inventory: distinct code point -> positions
    positions: dict[int, list[int]] = {}
    counts: dict[int, int] = {}
    capped: dict[int, bool] = {}
    for pos, ch in enumerate(text):
        cp = ord(ch)
        counts[cp] = counts.get(cp, 0) + 1
        plist = positions.setdefault(cp, [])
        if len(plist) < POSITION_CAP:
            plist.append(pos)
        else:
            capped[cp] = True

    buckets: dict[str, list[dict]] = {name: [] for name in BUCKET_ORDER}
    inventory: list[dict] = []

    for cp in sorted(counts):
        category = unicodedata.category(chr(cp))
        confusable_letter = cp in mixed_homoglyphs
        bucket = classify_codepoint(cp, category, confusable_letter)
        equiv = ascii_equivalent(cp)
        entry = {
            "codepoint": cp_label(cp),
            "decimal": cp,
            "name": cp_name(cp),
            "category": category,
            "utf8_hex": utf8_hex(cp),
            "count": counts[cp],
            "positions": positions[cp],
            "positions_capped": capped.get(cp, False),
            "position_cap": POSITION_CAP,
            "bucket": bucket,
            "ascii_equivalent": equiv,
            "differs_from_ascii": equiv is not None,
        }
        if bucket is not None:
            ctx_positions = positions[cp]
            if bucket == "confusable_homoglyph" and cp in mixed_homoglyphs:
                entry["mixed_script_word_positions"] = mixed_homoglyphs[cp][:POSITION_CAP]
                entry["mixed_script_word_occurrences"] = len(mixed_homoglyphs[cp])
                ctx_positions = mixed_homoglyphs[cp]
            entry["contexts"] = [make_context(text, p) for p in ctx_positions[:CONTEXT_CAP]]
            entry["contexts_capped"] = len(ctx_positions) > CONTEXT_CAP
            buckets[bucket].append(entry)
        inventory.append(entry)

    tag_payloads = decode_tag_runs(text) if buckets["tag_characters"] else []
    if tag_payloads:
        notes.append(
            "UNICODE TAG CHARACTERS PRESENT - hidden ASCII payload decoded: %r"
            % tag_payloads
        )

    summary = {
        "has_invisible_characters": bool(buckets["invisible_zero_width"]),
        "has_bidi_controls": bool(buckets["bidi_controls"]),
        "has_tag_characters": bool(buckets["tag_characters"]),
        "has_variation_selectors": bool(buckets["variation_selectors"]),
        "has_unexpected_controls": bool(buckets["control_characters"]),
        "has_space_variants": bool(buckets["space_variants"]),
        "has_combining_marks": bool(buckets["combining_marks"]),
        "has_confusable_homoglyphs": bool(buckets["confusable_homoglyph"]),
        "has_typographic_characters": bool(buckets["typographic"]),
        "is_pure_ascii": all(b < 0x80 for b in data),
        "is_printable_ascii_plus_newline_tab": all(
            (0x20 <= ord(c) <= 0x7E) or ord(c) in (0x09, 0x0A, 0x0D) for c in text
        ) and utf8_valid,
        "any_suspicious": any(bool(buckets[b]) for b in SUSPICIOUS_BUCKETS),
    }
    norm = normalization_report(text, data)
    summary["has_mixed_normalization"] = norm["mixed_normalization"]

    ascii_comparison = [
        {
            "codepoint": e["codepoint"],
            "name": e["name"],
            "bucket": e["bucket"],
            "ascii_equivalent": e["ascii_equivalent"],
        }
        for e in inventory
        if e["bucket"] is not None and e["ascii_equivalent"] is not None
    ]

    return {
        "path": path,
        "sha256_original_bytes": sha256,
        "utf8_bytes": len(data),
        "char_count": len(text),
        "utf8_valid": utf8_valid,
        "decode_error": decode_error,
        "summary": summary,
        "buckets": buckets,
        "hidden_tag_payloads": tag_payloads,
        "distinct_codepoints": inventory,
        "ascii_comparison": ascii_comparison,
        "normalization": norm,
        "notes": notes,
    }


def scan_file(path: str) -> dict:
    with open(path, "rb") as fh:  # binary + read-only: evidence is immutable
        data = fh.read()
    return scan_bytes(data, path)


# ---------------------------------------------------------------- text renderer


def render_text(report: dict) -> str:
    lines: list[str] = []
    a = lines.append
    a("=" * 78)
    a("FILE: %s" % report["path"])
    a("sha256(original bytes): %s" % report["sha256_original_bytes"])
    a("bytes: %d   characters (Unicode scalars): %d   valid UTF-8: %s"
      % (report["utf8_bytes"], report["char_count"], report["utf8_valid"]))
    for note in report["notes"]:
        a("NOTE: %s" % note)
    a("-" * 78)
    a("SUMMARY FLAGS:")
    for key, val in report["summary"].items():
        a("  %-40s %s" % (key, val))
    a("-" * 78)
    a("FLAGGED BUCKETS (invisible/hidden classes are reported separately from")
    a("ordinary typographic punctuation; their counts are never merged):")
    for bucket in BUCKET_ORDER:
        entries = report["buckets"][bucket]
        if not entries:
            continue
        total = sum(e["count"] for e in entries)
        marker = "SUSPICIOUS" if bucket in SUSPICIOUS_BUCKETS else "benign"
        a("")
        a("  [%s] %s -- %d distinct code point(s), %d occurrence(s)"
          % (marker, bucket, len(entries), total))
        for e in entries:
            a("    %s %s (%s) utf8=%s count=%d%s"
              % (e["codepoint"], e["name"], e["category"], e["utf8_hex"],
                 e["count"], " [positions capped at %d]" % POSITION_CAP
                 if e["positions_capped"] else ""))
            a("      positions: %s" % e["positions"][:20])
            if e.get("ascii_equivalent") is not None:
                a("      nearest ASCII equivalent: %r" % e["ascii_equivalent"])
            if "mixed_script_word_occurrences" in e:
                a("      occurrences inside mixed-script (Latin) words: %d of %d"
                  % (e["mixed_script_word_occurrences"], e["count"]))
            for ctx in e.get("contexts", [])[:5]:
                a("      context: %s" % ctx)
    if report["hidden_tag_payloads"]:
        a("")
        a("  DECODED HIDDEN TAG-CHARACTER PAYLOAD(S): %r" % report["hidden_tag_payloads"])
    a("-" * 78)
    a("NORMALIZATION (computed in memory; the source file is never modified):")
    for form, f in report["normalization"]["forms"].items():
        a("  %-5s is_normalized=%-5s chars=%-8d bytes=%-8d differs=%-5s sha256=%s"
          % (form, f["is_normalized"], f["char_count"], f["byte_count"],
             f["differs_from_original"], f["sha256"]))
    a("  mixed NFC/NFD normalization detected: %s"
      % report["normalization"]["mixed_normalization"])
    a("=" * 78)
    return "\n".join(lines)


# ---------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("files", nargs="+", help="files to scan (opened read-only, binary)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--json", action="store_true", help="machine-readable JSON output")
    group.add_argument("--text", action="store_true", help="human-readable output (default)")
    args = parser.parse_args(argv)

    reports = []
    for path in args.files:
        try:
            reports.append(scan_file(path))
        except OSError as exc:
            print("ERROR reading %s: %s" % (path, exc), file=sys.stderr)
            return 2

    if args.json:
        doc = {
            "generator": "scan_unicode.py",
            "python_version": sys.version.split()[0],
            "unicodedata_version": unicodedata.unidata_version,
            "position_cap": POSITION_CAP,
            "files": reports,
        }
        print(json.dumps(doc, indent=2, ensure_ascii=True))
    else:
        for report in reports:
            print(render_text(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
