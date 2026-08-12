#!/usr/bin/env python3
"""make_fixtures.py -- deterministic generator for the scanner test fixtures.

Every fixture is built from explicit backslash-u code point escapes (never
hand-typed invisible characters) and written in binary mode, so fixture
provenance is exact and reproducible. This source file is pure ASCII; the
test suite enforces that. Running the script twice produces byte-identical
files.

Usage:
    python3 make_fixtures.py [OUTPUT_DIR]     # default: <this dir>/fixtures
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.join(HERE, "fixtures")

# The invisible / zero-width set under test, one fixture each.
INVISIBLE_CODEPOINTS = {
    0x200B: "zwsp",
    0x200C: "zwnj",
    0x200D: "zwj",
    0x2060: "word_joiner",
    0xFEFF: "bom",
    0x00AD: "soft_hyphen",
    0x180E: "mongolian_vowel_sep",
    0x061C: "arabic_letter_mark",
    0x2061: "function_application",
    0x2062: "invisible_times",
    0x2063: "invisible_separator",
    0x2064: "invisible_plus",
}


def fixtures() -> dict[str, str]:
    """Return {filename: text}. Text is encoded to UTF-8 at write time."""
    fx: dict[str, str] = {}

    # --- positive controls: one per invisible character -------------------
    for cp, slug in INVISIBLE_CODEPOINTS.items():
        body = "The audit text continues" + chr(cp) + " with a hidden character.\n"
        if cp == 0xFEFF:
            # BOM fixture carries both a leading BOM and a mid-text FEFF.
            body = chr(cp) + body
        fx["positive_invisible_%04X_%s.txt" % (cp, slug)] = body

    # --- bidi controls and isolates ---------------------------------------
    # RLO/PDF, LRI/PDI, LRM/RLM, LRE/RLE, LRO, RLI, FSI
    fx["positive_bidi.txt"] = (
        "Attachment: \u202Egpj.exe\u202C\n"
        "Isolate: \u2066abc\u2069\n"
        "Marks: \u200Eleft\u200Fright\n"
        "Embed: \u202Ax\u202By\u202C\n"
        "Override+FSI: \u202Dz\u202C\u2067q\u2068r\u2069\n"
    )

    # --- Unicode tag characters spelling a hidden ASCII message -----------
    hidden = "HIDDEN WATERMARK"
    fx["positive_tags.txt"] = (
        "This sentence looks perfectly normal to a human reader.\n"
        + "\U000E0001"                                    # LANGUAGE TAG
        + "".join(chr(0xE0000 + ord(c)) for c in hidden)  # tag-char payload
        + "\U000E007F"                                    # CANCEL TAG
        + "Nothing to see here.\n"
    )

    # --- variation selectors ------------------------------------------------
    # U+2714 HEAVY CHECK MARK + VS16, letter a + plane-14 VS17,
    # U+2764 HEAVY BLACK HEART + VS15 (text style)
    fx["positive_variation_selectors.txt"] = (
        "Checked \u2714\uFE0F done, plane-14 selector a\U000E0100 here, "
        "text style \u2764\uFE0E too.\n"
    )

    # --- combining marks (Mn, Mc, Me) ----------------------------------------
    # e + COMBINING ACUTE (Mn), o + COMBINING DIAERESIS (Mn),
    # A + COMBINING ENCLOSING CIRCLE (Me), KA + VOWEL SIGN AA (Mc)
    fx["positive_combining.txt"] = (
        "Acute (Mn): e\u0301 diaeresis (Mn): o\u0308 "
        "enclosing circle (Me): A\u20DD "
        "Devanagari vowel sign (Mc): \u0915\u093E done.\n"
    )

    # --- Cyrillic/Greek homoglyphs inside Latin words -------------------------
    # Cyrillic a (U+0430) / o (U+043E) inside "pay", "invoice", "PayPal",
    # "support"; Greek omicron (U+03BF) in "money", Greek nu (U+03BD) in
    # "event". The pure-Cyrillic words must NOT be flagged.
    fx["positive_homoglyphs.txt"] = (
        "Please p\u0430y your inv\u043Eice at P\u0430yP\u0430l "
        "supp\u043Ert now.\n"
        "Greek mix: m\u03BFney and e\u03BDent inside Latin words.\n"
        "Pure Cyrillic (legitimate): \u043F\u0440\u0438\u0432\u0435\u0442 "
        "\u0417\u0434\u0440\u0430\u0432\u0441\u0442\u0432\u0443\u0439\u0442\u0435.\n"
    )

    # --- typographic-only positive control (MUST NOT flag as invisible) ------
    # curly quotes, apostrophe, en/em dash, ellipsis, hyphen forms
    fx["positive_typographic.txt"] = (
        "It\u2019s a \u201Cfine\u201D day \u2014 truly\u2026 "
        "\u2018quoted\u2019 words, an en\u2013dash, "
        "hyphen forms \u2010\u2011\u2012\u2015 and nothing hidden at all.\n"
    )

    # --- mixed NFC/NFD normalization ------------------------------------------
    # NFC e-acute (U+00E9) and NFD e + U+0301 in the same file
    fx["positive_mixed_normalization.txt"] = (
        "caf\u00E9 precomposed here, cafe\u0301 decomposed there.\n"
    )

    # --- position-cap exercise: >200 occurrences of one code point -------------
    fx["positive_position_cap.txt"] = ("a" * 250) + "\n"

    # --- negative control: printable ASCII + tab + LF + one CRLF line ----------
    fx["negative_control.txt"] = (
        "Plain ASCII line one.\n"
        "\tTabbed line two with punctuation: !\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~\n"
        "Digits 0123456789 and letters AZaz.\n"
        "CRLF line three.\r\n"
        "End.\n"
    )

    # --- legitimately accented text (French/Czech), all NFC, no anomalies ------
    fx["negative_accented_text.txt"] = (
        "Le gar\u00E7on pr\u00E9f\u00E9r\u00E9 a d\u00E9j\u00E0 vu la "
        "fa\u00E7ade na\u00EFve.\n"
        "P\u0159\u00EDli\u0161 \u017Elu\u0165ou\u010Dk\u00FD k\u016F\u0148 "
        "\u00FAp\u011Bl \u010F\u00E1belsk\u00E9 \u00F3dy.\n"
    )

    # --- pairs for compare_bytes.py ---------------------------------------------
    base = "Don't stop the audit now.\nThe quick brown fox jumps over the lazy dog.\n"
    fx["cmp_base.txt"] = base
    fx["cmp_identical.txt"] = base
    fx["cmp_zwsp.txt"] = base.replace("fox", "fox\u200B", 1)
    fx["cmp_crlf.txt"] = base.replace("\n", "\r\n")
    fx["cmp_curly.txt"] = base.replace("Don't", "Don\u2019t", 1)
    fx["cmp_nfc_base.txt"] = "one caf\u00E9 please\n"
    fx["cmp_nfd.txt"] = "one cafe\u0301 please\n"

    return fx


def build_all(out_dir: str = DEFAULT_DIR) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for name, text in sorted(fixtures().items()):
        path = os.path.join(out_dir, name)
        with open(path, "wb") as fh:  # binary mode: exact bytes, no translation
            fh.write(text.encode("utf-8"))
        written.append(path)
    return written


def main(argv: list[str]) -> int:
    out_dir = argv[1] if len(argv) > 1 else DEFAULT_DIR
    for path in build_all(out_dir):
        print("wrote %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
