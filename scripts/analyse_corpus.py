#!/usr/bin/env python3
"""Phase 5: aggregate character-level analysis and hypothesis tests H1/H2.

Scope. This script covers the CHARACTER-LEVEL evidence:
  - per-model rates of every flagged Unicode category, as rates not raw counts;
  - compliance with the ASCII-only prompts;
  - a genre-controlled comparison of typographic punctuation against human controls;
  - stability across repeated generations from an identical prompt;
  - Wilson score intervals so a zero count is reported with an honest upper bound.

Distributional statistics (n-grams, sentence length, synonym choice, punctuation
distributions) are deliberately NOT done here. They are Subagent C's independent
work, and duplicating them would manufacture false agreement between two analyses
that are supposed to be independent.

Stdlib only. Reads evidence/raw/ in binary mode. Writes evidence/analysis.json.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CORPUS = BASE / "evidence" / "raw" / "corpus"
CONTROLS = BASE / "evidence" / "raw" / "controls"
OUT = BASE / "evidence" / "analysis.json"

# ---------------------------------------------------------------------------
# Category definitions. Kept identical in spirit to scripts/scan_unicode.py;
# any divergence between the two is itself worth knowing, so both are reported.
# ---------------------------------------------------------------------------
INVISIBLE = set([0x200B, 0x200C, 0x200D, 0x2060, 0xFEFF, 0x00AD, 0x180E, 0x061C]) \
    | set(range(0x2061, 0x2065))
BIDI = set([0x200E, 0x200F, 0x202A, 0x202B, 0x202C, 0x202D, 0x202E]) \
    | set(range(0x2066, 0x206A))
TAGS = set(range(0xE0000, 0xE0080))
VARSEL = set(range(0xFE00, 0xFE10)) | set(range(0xE0100, 0xE01F0))
TYPOGRAPHIC = set([0x2018, 0x2019, 0x201A, 0x201B, 0x201C, 0x201D, 0x201E, 0x201F,
                   0x2010, 0x2011, 0x2012, 0x2013, 0x2014, 0x2015, 0x2026, 0x2032, 0x2033])
# Cyrillic/Greek letters that are visually identical to Latin ones.
HOMOGLYPH_LETTERS = set([0x0430, 0x0435, 0x043E, 0x0440, 0x0441, 0x0443, 0x0445,
                         0x03BF, 0x03BD, 0x03B1, 0x03B5, 0x0456, 0x0458])

CATEGORIES = ["invisible", "bidi", "tag", "variation_selector", "nonascii_space",
              "typographic", "homoglyph_letter", "combining", "unexpected_control",
              "other_nonascii"]


def classify(ch: str) -> str | None:
    """Return the flagged bucket for a character, or None if it is ordinary ASCII."""
    o = ord(ch)
    if o < 0x80:
        # Control characters other than tab, LF, CR are unexpected even in ASCII.
        if o < 0x20 and o not in (0x09, 0x0A, 0x0D):
            return "unexpected_control"
        return None
    if o in INVISIBLE:
        return "invisible"
    if o in BIDI:
        return "bidi"
    if o in TAGS:
        return "tag"
    if o in VARSEL:
        return "variation_selector"
    cat = unicodedata.category(ch)
    if cat in ("Zs", "Zl", "Zp"):
        return "nonascii_space"
    if o in TYPOGRAPHIC:
        return "typographic"
    if o in HOMOGLYPH_LETTERS:
        return "homoglyph_letter"
    if cat in ("Mn", "Mc", "Me"):
        return "combining"
    if cat in ("Cc", "Cf", "Co", "Cs"):
        return "unexpected_control"
    return "other_nonascii"


def wilson_upper(successes: int, n: int, z: float = 1.96) -> float:
    """Upper bound of the Wilson score interval.

    Reported because a raw zero count is not the same claim as "the rate is zero".
    With n characters observed and none flagged, this is the largest per-character
    rate still consistent with the observation at ~95% confidence.
    """
    if n == 0:
        return float("nan")
    p = successes / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre + margin) / denom


def scan_text(text: str) -> tuple[Counter, dict]:
    buckets: Counter = Counter()
    codepoints: dict[str, Counter] = defaultdict(Counter)
    for ch in text:
        b = classify(ch)
        if b:
            buckets[b] += 1
            codepoints[b][ord(ch)] += 1
    return buckets, {k: dict(v) for k, v in codepoints.items()}


def load_group(paths: list[Path]) -> dict:
    total_chars = 0
    total_bytes = 0
    buckets: Counter = Counter()
    codepoints: dict[str, Counter] = defaultdict(Counter)
    per_file = {}
    for p in sorted(paths):
        raw = p.read_bytes()
        text = raw.decode("utf-8")
        b, cps = scan_text(text)
        total_chars += len(text)
        total_bytes += len(raw)
        buckets.update(b)
        for k, v in cps.items():
            codepoints[k].update(v)
        per_file[p.stem] = {
            "chars": len(text), "bytes": len(raw),
            "flagged": {k: v for k, v in b.items() if v},
            "pure_ascii": all(ord(c) < 128 for c in text),
        }
    rates = {}
    for cat in CATEGORIES:
        n = buckets.get(cat, 0)
        rates[cat] = {
            "count": n,
            "per_1k_chars": round(1000 * n / total_chars, 6) if total_chars else None,
            "wilson_upper_per_1k": round(1000 * wilson_upper(n, total_chars), 6) if total_chars else None,
        }
    return {
        "files": len(paths),
        "total_chars": total_chars,
        "total_bytes": total_bytes,
        "rates": rates,
        "codepoints": {k: {f"U+{cp:04X}": c for cp, c in sorted(v.items(), key=lambda x: -x[1])}
                       for k, v in codepoints.items()},
        "per_file": per_file,
    }


# ---------------------------------------------------------------------------
# Targeted tests
# ---------------------------------------------------------------------------

def ascii_compliance(model_dirs: dict[str, Path]) -> dict:
    """Did the model obey an explicit 'ASCII only' instruction?

    A violation is evidence that non-ASCII output survives an explicit constraint.
    It is NOT automatically evidence of watermarking: a model failing an instruction
    is an ordinary and well documented behaviour.
    """
    result = {}
    for slug, d in model_dirs.items():
        per_prompt = {}
        for pid in ("S07", "M07", "L07"):
            f = d / f"{pid}.txt"
            if not f.exists():
                per_prompt[pid] = {"status": "not generated"}
                continue
            text = f.read_bytes().decode("utf-8")
            offenders = Counter()
            for i, ch in enumerate(text):
                o = ord(ch)
                if o > 0x7E or (o < 0x20 and o != 0x0A):
                    offenders[o] += 1
            per_prompt[pid] = {
                "chars": len(text),
                "compliant": not offenders,
                "violations": sum(offenders.values()),
                "violating_codepoints": {
                    f"U+{cp:04X}": {"count": c,
                                    "name": (unicodedata.name(chr(cp), "<unnamed>"))}
                    for cp, c in offenders.most_common()
                },
            }
        result[slug] = per_prompt
    return result


def genre_controlled_typography(model_dirs: dict[str, Path], human_paths: list[Path]) -> dict:
    """Compare typographic punctuation rates on comparable genres.

    The naive comparison (all model output vs all Gutenberg) is confounded: the
    human control is dialogue-heavy 19th-century fiction, while much of the model
    corpus is technical prose, lists, code and JSON. The quoted-speech prompts
    (S09/M09/L09) are the model subset that is genuinely comparable, so they are
    broken out separately.
    """
    out = {"note": (
        "Gutenberg transcriptions are dialogue-dense fiction; the model corpus is "
        "mixed. S09/M09/L09 are the dialogue-matched model subset. Even this is only "
        "a partial genre control: editorial transcription conventions differ from "
        "generated text regardless of genre."
    )}
    hum_chars = 0
    hum_typo = 0
    for p in human_paths:
        t = p.read_bytes().decode("utf-8")
        hum_chars += len(t)
        hum_typo += sum(1 for ch in t if ord(ch) in TYPOGRAPHIC)
    out["human_all"] = {"chars": hum_chars, "typographic": hum_typo,
                        "per_1k_chars": round(1000 * hum_typo / hum_chars, 4) if hum_chars else None}

    for slug, d in model_dirs.items():
        all_files = sorted(d.glob("*.txt"))
        dlg = [f for f in all_files if f.stem in ("S09", "M09", "L09")]
        for label, files in (("all", all_files), ("dialogue_only", dlg)):
            chars = typo = 0
            for f in files:
                t = f.read_bytes().decode("utf-8")
                chars += len(t)
                typo += sum(1 for ch in t if ord(ch) in TYPOGRAPHIC)
            out.setdefault(slug, {})[label] = {
                "files": len(files), "chars": chars, "typographic": typo,
                "per_1k_chars": round(1000 * typo / chars, 4) if chars else None,
            }
    return out


def repeat_stability(model_dirs: dict[str, Path]) -> dict:
    """Compare S01/S10, M01/M10, L01/L10: identical prompt, two generations.

    A hidden-Unicode watermark that encodes a per-request payload would be expected
    to differ between repeats; a fixed marker would be expected to recur. Both are
    only meaningful if any flagged characters exist at all.
    """
    out = {}
    for slug, d in model_dirs.items():
        pairs = {}
        for a, b in (("S01", "S10"), ("M01", "M10"), ("L01", "L10")):
            fa, fb = d / f"{a}.txt", d / f"{b}.txt"
            if not (fa.exists() and fb.exists()):
                pairs[f"{a}/{b}"] = {"status": "incomplete"}
                continue
            ta = fa.read_bytes().decode("utf-8")
            tb = fb.read_bytes().decode("utf-8")
            ba, _ = scan_text(ta)
            bb, _ = scan_text(tb)
            pairs[f"{a}/{b}"] = {
                "identical_text": ta == tb,
                "chars": [len(ta), len(tb)],
                "flagged_a": {k: v for k, v in ba.items() if v},
                "flagged_b": {k: v for k, v in bb.items() if v},
            }
        out[slug] = pairs
    return out


def main() -> int:
    model_dirs = {d.name: d for d in sorted(CORPUS.iterdir())
                  if d.is_dir() and any(d.glob("*.txt"))} if CORPUS.is_dir() else {}
    human_paths = sorted((CONTROLS / "human").glob("*.txt")) if (CONTROLS / "human").is_dir() else []
    synth_paths = [p for p in (CONTROLS / "synthetic").iterdir() if p.is_file()] \
        if (CONTROLS / "synthetic").is_dir() else []

    analysis = {
        "generator": "scripts/analyse_corpus.py",
        "scope": "Character-level evidence for H1 (hidden Unicode) and H2 (presentation layer). "
                 "Distributional statistics are Subagent C's independent work and are not duplicated here.",
        "groups": {},
    }
    for slug, d in model_dirs.items():
        analysis["groups"][f"model:{slug}"] = load_group(sorted(d.glob("*.txt")))
    if human_paths:
        analysis["groups"]["control:human_gutenberg"] = load_group(human_paths)
    if synth_paths:
        analysis["groups"]["control:synthetic_tools"] = load_group(synth_paths)

    analysis["ascii_compliance"] = ascii_compliance(model_dirs)
    analysis["genre_controlled_typography"] = genre_controlled_typography(model_dirs, human_paths)
    analysis["repeat_stability"] = repeat_stability(model_dirs)

    # Pooled model total, the headline number for H1.
    pooled_chars = sum(g["total_chars"] for k, g in analysis["groups"].items() if k.startswith("model:"))
    pooled_hidden = 0
    for k, g in analysis["groups"].items():
        if not k.startswith("model:"):
            continue
        for cat in ("invisible", "bidi", "tag", "variation_selector", "nonascii_space"):
            pooled_hidden += g["rates"][cat]["count"]
    analysis["pooled_model_hidden_character_test"] = {
        "categories": ["invisible", "bidi", "tag", "variation_selector", "nonascii_space"],
        "total_model_chars": pooled_chars,
        "total_hidden_chars_found": pooled_hidden,
        "observed_rate_per_1k": round(1000 * pooled_hidden / pooled_chars, 8) if pooled_chars else None,
        "wilson_upper_per_1k_chars": round(1000 * wilson_upper(pooled_hidden, pooled_chars), 8)
        if pooled_chars else None,
        "interpretation": (
            "A zero count is not proof of absence. The Wilson upper bound is the highest "
            "per-character rate of hidden characters still consistent with this corpus at "
            "~95% confidence. It bounds ONLY the hidden-character hypothesis (H1); a "
            "watermark carried in token selection would produce zero hidden characters "
            "and is entirely untouched by this test."
        ),
    }

    with OUT.open("w", encoding="utf-8") as fh:
        json.dump(analysis, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    # Console summary
    print("=== flagged-category rates per 1,000 characters ===")
    hdr = f"{'group':<34}" + "".join(f"{c[:11]:>13}" for c in
                                     ["invisible", "bidi", "tag", "varsel", "nonasc_space", "typographic"])
    print(hdr)
    for k, g in analysis["groups"].items():
        row = f"{k:<34}"
        for c in ("invisible", "bidi", "tag", "variation_selector", "nonascii_space", "typographic"):
            row += f"{g['rates'][c]['per_1k_chars']:>13}"
        print(row)
    p = analysis["pooled_model_hidden_character_test"]
    print(f"\npooled model chars: {p['total_model_chars']:,}   hidden chars found: {p['total_hidden_chars_found']}")
    print(f"95% upper bound on hidden-char rate: {p['wilson_upper_per_1k_chars']} per 1,000 chars")
    print("\n=== ASCII-only prompt compliance ===")
    for slug, pp in analysis["ascii_compliance"].items():
        bits = []
        for pid, r in pp.items():
            if r.get("status"):
                bits.append(f"{pid}:--")
            else:
                bits.append(f"{pid}:{'PASS' if r['compliant'] else 'FAIL(' + str(r['violations']) + ')'}")
        print(f"  {slug:<10} " + "  ".join(bits))
    print(f"\nwrote {OUT.relative_to(BASE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
