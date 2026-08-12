#!/usr/bin/env python3
"""Positive- and negative-control tests for scan_unicode.py and compare_bytes.py.

Run with:
    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
SCRIPTS = os.path.join(BASE, "scripts")
FIXTURES = os.path.join(HERE, "fixtures")

sys.path.insert(0, SCRIPTS)
sys.path.insert(0, HERE)

import make_fixtures  # noqa: E402
import scan_unicode  # noqa: E402
import compare_bytes  # noqa: E402


def setUpModule() -> None:
    # Regenerate fixtures deterministically so the suite is self-contained.
    make_fixtures.build_all(FIXTURES)


def fx(name: str) -> str:
    return os.path.join(FIXTURES, name)


def scan(name: str) -> dict:
    return scan_unicode.scan_file(fx(name))


def bucket_cps(report: dict, bucket: str) -> set[int]:
    return {e["decimal"] for e in report["buckets"][bucket]}


class TestFixtureProvenance(unittest.TestCase):
    def test_generator_source_is_pure_ascii(self):
        """Invisible chars must come from explicit escapes, not literals."""
        with open(os.path.join(HERE, "make_fixtures.py"), "rb") as fh:
            data = fh.read()
        self.assertTrue(all(b < 0x80 for b in data),
                        "make_fixtures.py must be pure ASCII")

    def test_generator_is_deterministic(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            make_fixtures.build_all(d1)
            make_fixtures.build_all(d2)
            for name in sorted(make_fixtures.fixtures()):
                with open(os.path.join(d1, name), "rb") as f1, \
                        open(os.path.join(d2, name), "rb") as f2:
                    self.assertEqual(f1.read(), f2.read(), name)


class TestNegativeControl(unittest.TestCase):
    def test_negative_control_is_completely_clean(self):
        r = scan("negative_control.txt")
        s = r["summary"]
        self.assertFalse(s["has_invisible_characters"])
        self.assertFalse(s["has_bidi_controls"])
        self.assertFalse(s["has_tag_characters"])
        self.assertFalse(s["has_variation_selectors"])
        self.assertFalse(s["has_unexpected_controls"])
        self.assertFalse(s["has_space_variants"])
        self.assertFalse(s["has_combining_marks"])
        self.assertFalse(s["has_confusable_homoglyphs"])
        self.assertFalse(s["has_typographic_characters"])
        self.assertFalse(s["has_mixed_normalization"])
        self.assertFalse(s["any_suspicious"])
        self.assertTrue(s["is_pure_ascii"])
        self.assertTrue(s["is_printable_ascii_plus_newline_tab"])
        for bucket in scan_unicode.BUCKET_ORDER:
            self.assertEqual(r["buckets"][bucket], [], bucket)

    def test_hash_and_counts_match_raw_bytes(self):
        path = fx("negative_control.txt")
        with open(path, "rb") as fh:
            data = fh.read()
        r = scan_unicode.scan_file(path)
        self.assertEqual(r["sha256_original_bytes"],
                         hashlib.sha256(data).hexdigest())
        self.assertEqual(r["utf8_bytes"], len(data))
        self.assertEqual(r["char_count"], len(data.decode("utf-8")))

    def test_scanner_never_modifies_input(self):
        path = fx("negative_control.txt")
        with open(path, "rb") as fh:
            before = fh.read()
        scan_unicode.scan_file(path)
        with open(path, "rb") as fh:
            after = fh.read()
        self.assertEqual(before, after)


class TestInvisibleCharacters(unittest.TestCase):
    def test_every_invisible_codepoint_lands_in_invisible_bucket(self):
        for cp, slug in make_fixtures.INVISIBLE_CODEPOINTS.items():
            name = "positive_invisible_%04X_%s.txt" % (cp, slug)
            with self.subTest(codepoint="U+%04X" % cp):
                r = scan(name)
                self.assertTrue(r["summary"]["has_invisible_characters"], name)
                self.assertIn(cp, bucket_cps(r, "invisible_zero_width"), name)
                # never merged into the typographic bucket
                self.assertNotIn(cp, bucket_cps(r, "typographic"), name)
                # entry detail: context, utf8 hex, positions
                entry = next(e for e in r["buckets"]["invisible_zero_width"]
                             if e["decimal"] == cp)
                self.assertTrue(entry["contexts"])
                self.assertIn("[[U+%04X]]" % cp, entry["contexts"][0])
                self.assertTrue(entry["utf8_hex"])
                self.assertTrue(entry["positions"])
                self.assertFalse(r["summary"]["is_pure_ascii"])

    def test_leading_bom_noted(self):
        r = scan("positive_invisible_FEFF_bom.txt")
        self.assertTrue(any("Leading U+FEFF" in n for n in r["notes"]))


class TestBidiControls(unittest.TestCase):
    def test_bidi_fixture_flags_all_controls(self):
        r = scan("positive_bidi.txt")
        self.assertTrue(r["summary"]["has_bidi_controls"])
        found = bucket_cps(r, "bidi_controls")
        expected = {0x202A, 0x202B, 0x202C, 0x202D, 0x202E,
                    0x2066, 0x2067, 0x2068, 0x2069, 0x200E, 0x200F}
        self.assertEqual(expected, found)
        # bidi controls are not counted as plain invisibles or typographic
        self.assertEqual(bucket_cps(r, "invisible_zero_width"), set())
        self.assertEqual(bucket_cps(r, "typographic"), set())


class TestTagCharacters(unittest.TestCase):
    def test_tag_smuggling_detected_and_payload_decoded(self):
        r = scan("positive_tags.txt")
        self.assertTrue(r["summary"]["has_tag_characters"])
        self.assertTrue(r["summary"]["any_suspicious"])
        self.assertTrue(bucket_cps(r, "tag_characters"))
        payloads = r["hidden_tag_payloads"]
        self.assertEqual(len(payloads), 1)
        self.assertIn("HIDDEN WATERMARK", payloads[0])
        self.assertIn("[TAG-LANG]", payloads[0])
        self.assertIn("[TAG-END]", payloads[0])


class TestVariationSelectors(unittest.TestCase):
    def test_variation_selectors_flagged(self):
        r = scan("positive_variation_selectors.txt")
        self.assertTrue(r["summary"]["has_variation_selectors"])
        found = bucket_cps(r, "variation_selectors")
        self.assertIn(0xFE0F, found)   # VS16 (emoji style)
        self.assertIn(0xFE0E, found)   # VS15 (text style)
        self.assertIn(0xE0100, found)  # plane-14 VS17
        # VS are Mn but must NOT be classified as ordinary combining marks
        self.assertNotIn(0xFE0F, bucket_cps(r, "combining_marks"))


class TestCombiningMarks(unittest.TestCase):
    def test_mn_mc_me_all_flagged(self):
        r = scan("positive_combining.txt")
        self.assertTrue(r["summary"]["has_combining_marks"])
        found = bucket_cps(r, "combining_marks")
        self.assertIn(0x0301, found)  # COMBINING ACUTE ACCENT (Mn)
        self.assertIn(0x0308, found)  # COMBINING DIAERESIS (Mn)
        self.assertIn(0x20DD, found)  # COMBINING ENCLOSING CIRCLE (Me)
        self.assertIn(0x093E, found)  # DEVANAGARI VOWEL SIGN AA (Mc)
        cats = {e["decimal"]: e["category"] for e in r["buckets"]["combining_marks"]}
        self.assertEqual(cats[0x0301], "Mn")
        self.assertEqual(cats[0x20DD], "Me")
        self.assertEqual(cats[0x093E], "Mc")


class TestHomoglyphs(unittest.TestCase):
    def test_homoglyphs_inside_latin_words_are_flagged(self):
        r = scan("positive_homoglyphs.txt")
        self.assertTrue(r["summary"]["has_confusable_homoglyphs"])
        found = bucket_cps(r, "confusable_homoglyph")
        self.assertIn(0x0430, found)  # CYRILLIC SMALL A in "pay"/"PayPal"
        self.assertIn(0x043E, found)  # CYRILLIC SMALL O in "invoice"/"support"
        self.assertIn(0x03BF, found)  # GREEK SMALL OMICRON in "money"
        self.assertIn(0x03BD, found)  # GREEK SMALL NU in "event"
        entry = next(e for e in r["buckets"]["confusable_homoglyph"]
                     if e["decimal"] == 0x0430)
        self.assertGreater(entry["mixed_script_word_occurrences"], 0)
        self.assertEqual(entry["ascii_equivalent"], "a")

    def test_pure_cyrillic_words_are_not_flagged(self):
        r = scan("positive_homoglyphs.txt")
        confusable = bucket_cps(r, "confusable_homoglyph")
        benign = bucket_cps(r, "other_non_ascii")
        # These occur ONLY in fully-Cyrillic words and must stay benign,
        # even though some are homoglyph-capable letters.
        for cp in (0x043F, 0x0440, 0x0438, 0x0432, 0x0435, 0x0442):
            self.assertNotIn(cp, confusable, "U+%04X" % cp)
            self.assertIn(cp, benign, "U+%04X" % cp)


class TestTypographicSeparation(unittest.TestCase):
    """CRITICAL: typographic punctuation is never merged with invisibles."""

    def test_typographic_fixture_is_typographic_not_invisible(self):
        r = scan("positive_typographic.txt")
        s = r["summary"]
        self.assertTrue(s["has_typographic_characters"])
        self.assertFalse(s["has_invisible_characters"])
        self.assertFalse(s["has_bidi_controls"])
        self.assertFalse(s["has_tag_characters"])
        self.assertFalse(s["has_variation_selectors"])
        self.assertFalse(s["has_unexpected_controls"])
        self.assertFalse(s["has_confusable_homoglyphs"])
        self.assertFalse(s["any_suspicious"])
        expected = {0x2018, 0x2019, 0x201C, 0x201D, 0x2013, 0x2014,
                    0x2026, 0x2010, 0x2011, 0x2012, 0x2015}
        self.assertEqual(expected, bucket_cps(r, "typographic"))
        for bucket in scan_unicode.SUSPICIOUS_BUCKETS:
            self.assertEqual(r["buckets"][bucket], [], bucket)

    def test_buckets_are_reported_separately(self):
        """Invisible and typographic counts live under distinct keys."""
        r = scan("positive_typographic.txt")
        self.assertIn("invisible_zero_width", r["buckets"])
        self.assertIn("typographic", r["buckets"])
        inv = sum(e["count"] for e in r["buckets"]["invisible_zero_width"])
        typo = sum(e["count"] for e in r["buckets"]["typographic"])
        self.assertEqual(inv, 0)
        self.assertGreater(typo, 0)

    def test_ascii_equivalents_reported(self):
        r = scan("positive_typographic.txt")
        equiv = {e["decimal"]: e["ascii_equivalent"]
                 for e in r["buckets"]["typographic"]}
        self.assertEqual(equiv[0x2019], "'")
        self.assertEqual(equiv[0x201C], '"')
        self.assertEqual(equiv[0x2014], "--")
        self.assertEqual(equiv[0x2026], "...")


class TestAccentedTextIsNormal(unittest.TestCase):
    def test_scanner_does_not_crash_or_mislabel_accents(self):
        r = scan("negative_accented_text.txt")  # must not raise
        s = r["summary"]
        self.assertFalse(s["any_suspicious"])
        self.assertFalse(s["has_invisible_characters"])
        self.assertFalse(s["has_unexpected_controls"])
        self.assertFalse(s["has_combining_marks"])  # fixture is pure NFC
        self.assertFalse(s["has_mixed_normalization"])
        # accented Latin letters are benign typographic entries, e.g. e-acute
        typo = bucket_cps(r, "typographic")
        self.assertIn(0x00E9, typo)
        entry = next(e for e in r["buckets"]["typographic"]
                     if e["decimal"] == 0x00E9)
        self.assertEqual(entry["ascii_equivalent"], "e")


class TestNormalization(unittest.TestCase):
    def test_mixed_nfc_nfd_detected(self):
        r = scan("positive_mixed_normalization.txt")
        self.assertTrue(r["summary"]["has_mixed_normalization"])
        forms = r["normalization"]["forms"]
        self.assertFalse(forms["NFC"]["is_normalized"])
        self.assertFalse(forms["NFD"]["is_normalized"])
        self.assertTrue(forms["NFC"]["differs_from_original"])
        self.assertTrue(forms["NFD"]["differs_from_original"])

    def test_all_four_forms_reported_with_hashes(self):
        r = scan("negative_control.txt")
        forms = r["normalization"]["forms"]
        self.assertEqual(set(forms), {"NFC", "NFD", "NFKC", "NFKD"})
        for f in forms.values():
            self.assertEqual(len(f["sha256"]), 64)
            self.assertFalse(f["differs_from_original"])  # pure ASCII


class TestPositionCap(unittest.TestCase):
    def test_positions_capped_at_200(self):
        r = scan("positive_position_cap.txt")
        entry = next(e for e in r["distinct_codepoints"] if e["decimal"] == 0x61)
        self.assertEqual(entry["count"], 250)
        self.assertEqual(len(entry["positions"]), 200)
        self.assertTrue(entry["positions_capped"])
        self.assertEqual(entry["position_cap"], 200)


class TestScanCLI(unittest.TestCase):
    def test_json_output_parses(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "scan_unicode.py"),
             "--json", fx("negative_control.txt")],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        doc = json.loads(proc.stdout)
        self.assertEqual(doc["unicodedata_version"], "14.0.0")
        self.assertTrue(doc["files"][0]["summary"]["is_pure_ascii"])

    def test_text_output_runs(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS, "scan_unicode.py"),
             "--text", fx("positive_tags.txt")],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("tag_characters", proc.stdout)
        self.assertIn("HIDDEN WATERMARK", proc.stdout)
        # output must be printable ASCII only (escapes, not raw invisibles)
        self.assertTrue(all(ord(c) < 0x80 for c in proc.stdout))


class TestCompareBytes(unittest.TestCase):
    def test_identical_files(self):
        r = compare_bytes.compare_files(fx("cmp_base.txt"), fx("cmp_identical.txt"))
        self.assertTrue(r["byte_identical"])
        self.assertEqual(r["byte_diffs"], [])
        self.assertEqual(r["char_diffs"], [])
        self.assertEqual(r["classifications"], [])
        with open(fx("cmp_base.txt"), "rb") as fh:
            data = fh.read()
        self.assertEqual(r["file_a"]["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(r["file_a"]["bytes"], len(data))

    def test_zwsp_insertion_classified_invisible(self):
        r = compare_bytes.compare_files(fx("cmp_base.txt"), fx("cmp_zwsp.txt"))
        self.assertFalse(r["byte_identical"])
        self.assertEqual(r["classifications"], ["invisible-character"])
        d = r["char_diffs"][0]
        self.assertEqual(d["b_codepoints"][0]["codepoint"], "U+200B")
        self.assertEqual(d["b_codepoints"][0]["name"], "ZERO WIDTH SPACE")

    def test_crlf_vs_lf_classified_line_ending(self):
        r = compare_bytes.compare_files(fx("cmp_base.txt"), fx("cmp_crlf.txt"))
        self.assertFalse(r["byte_identical"])
        self.assertEqual(r["classifications"], ["line-ending"])

    def test_curly_apostrophe_classified_typographic(self):
        r = compare_bytes.compare_files(fx("cmp_base.txt"), fx("cmp_curly.txt"))
        self.assertFalse(r["byte_identical"])
        self.assertEqual(r["classifications"], ["typographic-substitution"])
        d = r["char_diffs"][0]
        a_cps = {c["codepoint"] for c in d["a_codepoints"]}
        b_cps = {c["codepoint"] for c in d["b_codepoints"]}
        self.assertIn("U+0027", a_cps)
        self.assertIn("U+2019", b_cps)

    def test_nfc_vs_nfd_classified_normalization(self):
        r = compare_bytes.compare_files(fx("cmp_nfc_base.txt"), fx("cmp_nfd.txt"))
        self.assertFalse(r["byte_identical"])
        self.assertEqual(r["classifications"], ["normalization"])

    def test_byte_level_diff_reports_offsets_and_hex(self):
        r = compare_bytes.compare_files(fx("cmp_base.txt"), fx("cmp_zwsp.txt"))
        self.assertTrue(r["byte_diffs"])
        d = r["byte_diffs"][0]
        self.assertEqual(d["b_bytes_hex"], "E2 80 8B")  # UTF-8 of U+200B
        self.assertEqual(d["b_decoded"], "\\u200B")

    def test_cli_json_and_exit_codes(self):
        script = os.path.join(SCRIPTS, "compare_bytes.py")
        same = subprocess.run(
            [sys.executable, script, "--json", fx("cmp_base.txt"), fx("cmp_identical.txt")],
            capture_output=True, text=True)
        self.assertEqual(same.returncode, 0, same.stderr)
        self.assertTrue(json.loads(same.stdout)["byte_identical"])
        diff = subprocess.run(
            [sys.executable, script, "--json", fx("cmp_base.txt"), fx("cmp_crlf.txt")],
            capture_output=True, text=True)
        self.assertEqual(diff.returncode, 1, diff.stderr)
        self.assertFalse(json.loads(diff.stdout)["byte_identical"])


if __name__ == "__main__":
    unittest.main()
