#!/usr/bin/env python3
"""Build the human and synthetic control corpora for the Claude watermark audit.

Controls exist so that any Unicode finding in model output can be compared against
text of KNOWN provenance. Without them, "Claude uses curly quotes" is uninterpretable,
because human publishers use curly quotes too.

Three control classes are produced:

  human/      Public-domain human-authored prose, downloaded as raw bytes from
              Project Gutenberg. Written long before large language models existed.
              Downloaded with urllib and written in binary mode: the bytes on disk
              are the bytes on the wire. No decoding, no normalization, no rewriting.

  synthetic/  Deterministic machine-generated ASCII produced by tools that are not
              language models (a C compiler's assembler output, CPython's bytecode
              disassembler) plus seeded pseudo-random printable ASCII.

  provenance.json  URL, UTC retrieval timestamp, byte length and SHA-256 for every
              control file, so each one can be re-verified or re-fetched.

Stdlib only. Never modifies anything under evidence/raw/corpus/.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import string
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
HUMAN_DIR = BASE / "evidence" / "raw" / "controls" / "human"
SYNTH_DIR = BASE / "evidence" / "raw" / "controls" / "synthetic"
PROVENANCE = BASE / "evidence" / "raw" / "controls" / "provenance.json"

# Project Gutenberg plain-text UTF-8 editions. All are pre-20th-century works,
# transcribed and proofread by human volunteers. Their typography is therefore
# human/editorial in origin, which is exactly the comparison we need.
GUTENBERG = [
    ("pg1342_pride_and_prejudice", "https://www.gutenberg.org/cache/epub/1342/pg1342.txt",
     "Jane Austen, Pride and Prejudice (1813)"),
    ("pg11_alices_adventures", "https://www.gutenberg.org/cache/epub/11/pg11.txt",
     "Lewis Carroll, Alice's Adventures in Wonderland (1865)"),
    ("pg2701_moby_dick", "https://www.gutenberg.org/cache/epub/2701/pg2701.txt",
     "Herman Melville, Moby Dick (1851)"),
    ("pg74_tom_sawyer", "https://www.gutenberg.org/cache/epub/74/pg74.txt",
     "Mark Twain, The Adventures of Tom Sawyer (1876)"),
    ("pg84_frankenstein", "https://www.gutenberg.org/cache/epub/84/pg84.txt",
     "Mary Shelley, Frankenstein (1818)"),
]

# Seeded so the random ASCII control is exactly reproducible.
RANDOM_SEED = 20260812


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(entries: list, name: str, path: Path, source: str, kind: str,
           description: str, retrieved: str, extra: dict | None = None) -> None:
    entry = {
        "control_id": name,
        "class": kind,
        "path": str(path.relative_to(BASE)),
        "source": source,
        "description": description,
        "retrieved_utc": retrieved,
        "bytes": path.stat().st_size,
        "sha256": sha256_of(path),
    }
    if extra:
        entry.update(extra)
    entries.append(entry)


def fetch_human(entries: list) -> None:
    HUMAN_DIR.mkdir(parents=True, exist_ok=True)
    for name, url, desc in GUTENBERG:
        out = HUMAN_DIR / f"{name}.txt"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "claude-watermark-audit/1.0 (research; text-encoding study)"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()  # bytes on the wire, untouched
                status = resp.status
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            print(f"  FAILED {name}: {type(exc).__name__}: {exc}", file=sys.stderr)
            continue
        retrieved = utc_now()
        out.write_bytes(raw)  # binary write: no newline translation, no re-encoding
        record(entries, name, out, url, "human_public_domain", desc, retrieved,
               {"http_status": status})
        print(f"  ok {name}: {len(raw)} bytes")


def build_synthetic(entries: list) -> None:
    SYNTH_DIR.mkdir(parents=True, exist_ok=True)

    # 1. C compiler assembler output. A non-LLM tool emitting ASCII text.
    csrc = """#include <stdio.h>
#include <stdlib.h>

static int fib(int n) {
    if (n < 2) return n;
    return fib(n - 1) + fib(n - 2);
}

int main(int argc, char **argv) {
    int upto = (argc > 1) ? atoi(argv[1]) : 20;
    for (int i = 0; i < upto; i++) {
        printf("fib(%d) = %d\\n", i, fib(i));
    }
    return 0;
}
"""
    with tempfile.TemporaryDirectory() as td:
        cfile = Path(td) / "fib.c"
        cfile.write_text(csrc, encoding="ascii")
        out = SYNTH_DIR / "compiler_assembly_output.s"
        try:
            proc = subprocess.run(
                ["clang", "-S", "-O1", "-o", "-", str(cfile)],
                capture_output=True, timeout=120,
            )
            if proc.returncode == 0 and proc.stdout:
                out.write_bytes(proc.stdout)
                record(entries, "compiler_assembly_output", out,
                       "clang -S -O1 on a locally written C source file",
                       "synthetic_tool_ascii",
                       "Assembler output from the system C compiler. Deterministic tool output, not model output.",
                       utc_now(), {"generator": "clang", "returncode": 0})
                print(f"  ok compiler_assembly_output: {len(proc.stdout)} bytes")
            else:
                print(f"  FAILED clang: rc={proc.returncode} {proc.stderr[:200]!r}", file=sys.stderr)
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            print(f"  FAILED clang: {type(exc).__name__}: {exc}", file=sys.stderr)

        # Also keep the human/hand-written C source itself as a control.
        src_out = SYNTH_DIR / "handwritten_source.c"
        src_out.write_bytes(csrc.encode("ascii"))
        record(entries, "handwritten_source_c", src_out,
               "Written by hand inside scripts/make_controls.py",
               "synthetic_tool_ascii",
               "Hand-written ASCII C source embedded in this script. Provenance is this file.",
               utc_now(), {"generator": "literal in make_controls.py"})
        print(f"  ok handwritten_source_c: {src_out.stat().st_size} bytes")

    # 2. CPython bytecode disassembly. Another non-LLM ASCII text generator.
    out = SYNTH_DIR / "python_disassembly.txt"
    try:
        proc = subprocess.run(
            [sys.executable, "-c",
             "import dis, json, argparse, difflib, textwrap;\n"
             "mods = [json.decoder, argparse, difflib, textwrap]\n"
             "import io\n"
             "buf = io.StringIO()\n"
             "for m in mods:\n"
             "    print('==== ' + m.__name__ + ' ====', file=buf)\n"
             "    dis.dis(m, file=buf, depth=1)\n"
             "print(buf.getvalue())"],
            capture_output=True, timeout=120,
        )
        if proc.returncode == 0 and proc.stdout:
            out.write_bytes(proc.stdout)
            record(entries, "python_disassembly", out,
                   f"{sys.executable} -c 'dis.dis(...)' over stdlib modules",
                   "synthetic_tool_ascii",
                   "CPython bytecode disassembly. Deterministic tool output, not model output.",
                   utc_now(), {"generator": "python dis", "returncode": 0})
            print(f"  ok python_disassembly: {len(proc.stdout)} bytes")
        else:
            print(f"  FAILED dis: rc={proc.returncode}", file=sys.stderr)
    except subprocess.TimeoutExpired as exc:
        print(f"  FAILED dis: {exc}", file=sys.stderr)

    # 3. Seeded pseudo-random printable ASCII. Guaranteed clean negative control
    #    with an exactly reproducible seed.
    rng = random.Random(RANDOM_SEED)
    alphabet = string.printable[:95]  # U+0020..U+007E inclusive
    lines = []
    for _ in range(400):
        n = rng.randint(40, 100)
        lines.append("".join(rng.choice(alphabet) for _ in range(n)))
    blob = ("\n".join(lines) + "\n").encode("ascii")
    out = SYNTH_DIR / "random_printable_ascii.txt"
    out.write_bytes(blob)
    record(entries, "random_printable_ascii", out,
           f"random.Random(seed={RANDOM_SEED}), alphabet = string.printable[:95] (U+0020..U+007E)",
           "synthetic_random_ascii",
           "Seeded pseudo-random printable ASCII. Reproducible by re-running this script.",
           utc_now(), {"seed": RANDOM_SEED, "python": sys.version.split()[0],
                       "lines": 400})
    print(f"  ok random_printable_ascii: {len(blob)} bytes")

    # 4. Seeded pseudo-random ASCII shaped like English prose (word-like tokens,
    #    sentence punctuation). Controls for "does prose shape alone create anomalies".
    rng2 = random.Random(RANDOM_SEED + 1)
    vowels, consonants = "aeiou", "bcdfghjklmnpqrstvwxyz"
    def word() -> str:
        return "".join(
            rng2.choice(consonants) + rng2.choice(vowels)
            for _ in range(rng2.randint(1, 4))
        )
    sentences = []
    for _ in range(600):
        w = [word() for _ in range(rng2.randint(6, 20))]
        s = " ".join(w).capitalize() + rng2.choice([".", ".", ".", "?", "!"])
        sentences.append(s)
    prose = ""
    for i in range(0, len(sentences), 6):
        prose += " ".join(sentences[i:i + 6]) + "\n\n"
    out = SYNTH_DIR / "random_pseudo_prose_ascii.txt"
    out.write_bytes(prose.encode("ascii"))
    record(entries, "random_pseudo_prose_ascii", out,
           f"random.Random(seed={RANDOM_SEED + 1}), synthetic syllable words",
           "synthetic_random_ascii",
           "Seeded pseudo-random ASCII with prose-like shape and punctuation.",
           utc_now(), {"seed": RANDOM_SEED + 1, "sentences": 600})
    print(f"  ok random_pseudo_prose_ascii: {out.stat().st_size} bytes")


def main() -> int:
    entries: list = []
    print("Fetching human public-domain controls...")
    fetch_human(entries)
    print("Building synthetic controls...")
    build_synthetic(entries)

    PROVENANCE.parent.mkdir(parents=True, exist_ok=True)
    with PROVENANCE.open("w", encoding="utf-8") as fh:
        json.dump(
            {
                "generated_utc": utc_now(),
                "generator": "scripts/make_controls.py",
                "python": sys.version.split()[0],
                "note": (
                    "Human controls are raw bytes as served by Project Gutenberg. "
                    "They are NOT normalized, decoded or rewritten. Gutenberg transcriptions "
                    "are human-produced and may legitimately contain typographic punctuation; "
                    "that is the point of the control."
                ),
                "controls": entries,
            },
            fh, ensure_ascii=False, indent=2,
        )
        fh.write("\n")
    print(f"\nWrote {len(entries)} controls; provenance -> {PROVENANCE.relative_to(BASE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
