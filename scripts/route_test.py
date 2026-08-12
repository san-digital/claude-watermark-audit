#!/usr/bin/env python3
"""Phase 4: pass fixed control text through every ACCESSIBLE presentation route and hash it.

The purpose is to find out which layer, if any, introduces or alters Unicode
INDEPENDENTLY of any language model. If the macOS clipboard or a terminal mangles
text on its own, then a character observed after copying tells you nothing about
the model that produced it.

Two probes are used:

  ascii_control    Printable ASCII only (U+0020..U+007E) plus tab, LF and one CRLF
                   line. Anything non-ASCII appearing downstream was introduced by
                   the route, not by a model.

  unicode_probe    Deliberately contains one of every flagged category (zero-width,
                   bidi, tag characters, variation selectors, combining marks,
                   homoglyphs, typographic punctuation). Tests whether a route
                   silently STRIPS or NORMALIZES hidden characters. A route that
                   destroys them would hide model-level marking from us, which is
                   just as important to know as a route that adds them.

Routes exercised here are the locally accessible ones only. Routes requiring
claude.ai, the Anthropic HTTP API, an official SDK, or a cloud provider are
recorded as unavailable by the caller, not silently skipped.

Stdlib only. Writes to evidence/routes/. Never touches evidence/raw/corpus/.
"""

from __future__ import annotations

import hashlib
import json
import os
import pty
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ROUTES = BASE / "evidence" / "routes"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# --------------------------------------------------------------------------
# Probe construction. Built from explicit code points so provenance is exact.
# --------------------------------------------------------------------------

def build_ascii_control() -> bytes:
    lines = [
        "ASCII-CONTROL-V1 claude-watermark-audit",
        "Straight quotes: 'single' and \"double\" and it's a contraction.",
        "Dashes: hyphen - and double-hyphen -- and triple---hyphen.",
        "Dots: three dots ... and a full stop.",
        "Symbols: !#$%&()*+,./:;<=>?@[\\]^_`{|}~",
        "Digits: 0123456789",
        "A tab follows:\tafter the tab.",
        "Spacing: single space, then two  spaces, then three   spaces.",
        "The quick brown fox jumps over the lazy dog. 0123456789.",
    ]
    body = "\n".join(lines) + "\n"
    # One deliberate CRLF line so line-ending rewriting is detectable.
    body += "This line ends with CRLF.\r\n"
    body += "This line ends with LF.\n"
    return body.encode("ascii")


def build_unicode_probe() -> bytes:
    cp = chr
    # Built from code points so this probe does not depend on the encoding of
    # this source file, nor on how any model emitted the literal characters.
    _ACCENTED_WORDS = (
        "caf" + cp(0x00E9) + " na" + cp(0x00EF) + "ve "
        "Dvo" + cp(0x0159) + cp(0x00E1) + "k " + cp(0x00C9) + "mile"
    )
    parts = [
        "UNICODE-PROBE-V1 claude-watermark-audit",
        # Invisible / zero-width
        "ZWSP[" + cp(0x200B) + "] ZWNJ[" + cp(0x200C) + "] ZWJ[" + cp(0x200D) + "]"
        " WJ[" + cp(0x2060) + "] BOM[" + cp(0xFEFF) + "] SHY[" + cp(0x00AD) + "]",
        # Space variants
        "NBSP[" + cp(0x00A0) + "] NNBSP[" + cp(0x202F) + "] ENSP[" + cp(0x2002) + "]"
        " EMSP[" + cp(0x2003) + "] THINSP[" + cp(0x2009) + "] IDSP[" + cp(0x3000) + "]",
        # Bidi controls and isolates
        "LRM[" + cp(0x200E) + "] RLM[" + cp(0x200F) + "] LRI[" + cp(0x2066) + "]"
        " RLI[" + cp(0x2067) + "] PDI[" + cp(0x2069) + "] RLO[" + cp(0x202E) + "] PDF[" + cp(0x202C) + "]",
        # Variation selectors
        "VS15[" + cp(0xFE0E) + "] VS16[" + cp(0xFE0F) + "] VS17[" + cp(0xE0100) + "]",
        # Unicode tag characters spelling "HI" invisibly (the canonical smuggling vector)
        "TAGS[" + cp(0xE0001) + cp(0xE0048) + cp(0xE0049) + cp(0xE007F) + "]",
        # Combining marks (decomposed e-acute, then a stacked example)
        "COMBINING[e" + cp(0x0301) + " a" + cp(0x0308) + cp(0x0327) + "]",
        # Homoglyphs: Cyrillic a/e/o and Greek omicron inside Latin words
        "HOMOGLYPH[p" + cp(0x0430) + "yp" + cp(0x0430) + "l s" + cp(0x0435) + "cur"
        + cp(0x0435) + " b" + cp(0x03BF) + "dy]",
        # Typographic punctuation (legitimate; must be bucketed separately)
        "TYPOGRAPHIC[" + cp(0x2018) + "single" + cp(0x2019) + " " + cp(0x201C) + "double"
        + cp(0x201D) + " en" + cp(0x2013) + "dash em" + cp(0x2014) + "dash ell" + cp(0x2026) + "]",
        # Legitimate accented letters, explicitly precomposed (NFC).
        "ACCENTED-NFC[" + unicodedata.normalize("NFC", _ACCENTED_WORDS) + "]",
        # The SAME words explicitly decomposed (NFD). Normalizing here rather than
        # trusting however this source file happens to be encoded is deliberate: it
        # guarantees the probe really does contain mixed normalization forms.
        "ACCENTED-NFD[" + unicodedata.normalize("NFD", _ACCENTED_WORDS) + "]",
        # Miscellaneous
        "NOBREAK-HYPHEN[" + cp(0x2011) + "] FIGDASH[" + cp(0x2012) + "] MINUS[" + cp(0x2212) + "]",
        "LINESEP-NEXT-LINE_ends_here",
    ]
    body = "\n".join(parts) + "\n"
    return body.encode("utf-8")


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

def route_python_binary(src: bytes, out: Path) -> dict:
    """Baseline. Binary write straight from the generating process."""
    out.write_bytes(src)
    return {"ok": True, "note": "baseline; binary write, no encoding layer"}


def route_bash_heredoc(src: bytes, out: Path) -> dict:
    """Shell heredoc via a quoted delimiter (no expansion) then redirection."""
    tmp = out.with_suffix(".in")
    tmp.write_bytes(src)
    proc = subprocess.run(["bash", "-c", f"cat < {tmp!s} > {out!s}"],
                          capture_output=True, timeout=60)
    tmp.unlink(missing_ok=True)
    return {"ok": proc.returncode == 0, "returncode": proc.returncode,
            "note": "bash cat + stdout redirection to file"}


def route_clipboard(src: bytes, out: Path) -> dict:
    """macOS system clipboard round-trip: pbcopy then pbpaste.

    NOTE: this is the OS clipboard, NOT the claude.ai web interface Copy button.
    It cannot answer whether Claude's web Copy handler alters text.
    """
    if not (shutil.which("pbcopy") and shutil.which("pbpaste")):
        return {"ok": False, "note": "pbcopy/pbpaste unavailable"}
    p1 = subprocess.run(["pbcopy"], input=src, capture_output=True, timeout=60)
    if p1.returncode != 0:
        return {"ok": False, "returncode": p1.returncode, "note": "pbcopy failed"}
    p2 = subprocess.run(["pbpaste"], capture_output=True, timeout=60)
    if p2.returncode != 0:
        return {"ok": False, "returncode": p2.returncode, "note": "pbpaste failed"}
    out.write_bytes(p2.stdout)
    return {"ok": True, "note": "macOS NSPasteboard round-trip via pbcopy/pbpaste"}


def route_pty(src: bytes, out: Path) -> dict:
    """Round-trip through a real pseudo-terminal, approximating terminal rendering.

    Uses the stdlib pty module rather than script(1). script(1) needs a controlling
    terminal on stdin and fails with "tcgetattr/ioctl: Operation not supported on
    socket" under an agent harness, which made this route pass or fail depending on
    how the script happened to be invoked. Opening our own pty removes that
    dependency and makes the route deterministic.

    The tty line discipline applies ONLCR, translating LF to CRLF on output. Any
    added CR bytes are therefore a terminal artefact and must never be attributed
    to a model.
    """
    tmp = out.with_suffix(".in")
    tmp.write_bytes(src)
    master, slave = pty.openpty()
    chunks: list[bytes] = []
    try:
        proc = subprocess.Popen(["cat", str(tmp)], stdin=slave, stdout=slave,
                                stderr=slave, close_fds=True)
        os.close(slave)
        slave = -1
        while True:
            try:
                data = os.read(master, 65536)
            except OSError:
                break  # EIO on macOS when the last slave fd closes: normal EOF
            if not data:
                break
            chunks.append(data)
        rc = proc.wait(timeout=60)
    except Exception as exc:  # noqa: BLE001 - record, never mask
        return {"ok": False, "note": f"{type(exc).__name__}: {exc}"}
    finally:
        if slave != -1:
            os.close(slave)
        os.close(master)
        tmp.unlink(missing_ok=True)
    out.write_bytes(b"".join(chunks))
    return {"ok": rc == 0, "returncode": rc,
            "note": "pty capture via stdlib pty.openpty(); LF->CRLF translation by "
                    "the tty line discipline is EXPECTED and is a terminal artefact, "
                    "not model output"}


def route_utf8_decode_encode(src: bytes, out: Path) -> dict:
    """Decode to str and re-encode, as a naive text-mode tool would."""
    try:
        text = src.decode("utf-8")
    except UnicodeDecodeError as exc:
        return {"ok": False, "note": f"decode failed: {exc}"}
    with out.open("w", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return {"ok": True, "note": "python text-mode write, newline='' (no translation)"}


def route_json_roundtrip(src: bytes, out: Path) -> dict:
    """Serialize through JSON and back, as the agent/tool transport does."""
    try:
        text = src.decode("utf-8")
    except UnicodeDecodeError as exc:
        return {"ok": False, "note": f"decode failed: {exc}"}
    encoded = json.dumps({"content": text}, ensure_ascii=False)
    back = json.loads(encoded)["content"]
    out.write_bytes(back.encode("utf-8"))
    return {"ok": True, "note": "json.dumps(ensure_ascii=False) -> json.loads; "
                                "models the tool-call transport layer"}


def route_json_roundtrip_ascii(src: bytes, out: Path) -> dict:
    """Same, but with ensure_ascii=True (\\uXXXX escaping), the other common setting."""
    try:
        text = src.decode("utf-8")
    except UnicodeDecodeError as exc:
        return {"ok": False, "note": f"decode failed: {exc}"}
    encoded = json.dumps({"content": text}, ensure_ascii=True)
    back = json.loads(encoded)["content"]
    out.write_bytes(back.encode("utf-8"))
    return {"ok": True, "note": "json.dumps(ensure_ascii=True) -> json.loads"}


ROUTE_FUNCS = [
    ("R1_python_binary_write", route_python_binary),
    ("R2_bash_redirect", route_bash_heredoc),
    ("R3_macos_clipboard", route_clipboard),
    ("R4_pty_terminal", route_pty),
    ("R5_python_text_write", route_utf8_decode_encode),
    ("R6_json_transport_unicode", route_json_roundtrip),
    ("R7_json_transport_escaped", route_json_roundtrip_ascii),
]


def main() -> int:
    ROUTES.mkdir(parents=True, exist_ok=True)
    results = {"generated_utc": utc_now(), "generator": "scripts/route_test.py",
               "platform": sys.platform, "probes": {}}

    for probe_name, builder in (("ascii_control", build_ascii_control),
                                ("unicode_probe", build_unicode_probe)):
        src = builder()
        src_path = ROUTES / f"{probe_name}__R0_source.txt"
        src_path.write_bytes(src)
        probe = {
            "source_path": str(src_path.relative_to(BASE)),
            "source_sha256": sha(src),
            "source_bytes": len(src),
            "routes": {},
        }
        print(f"\n=== {probe_name}  ({len(src)} bytes, sha {sha(src)[:16]}...) ===")
        for rname, fn in ROUTE_FUNCS:
            out = ROUTES / f"{probe_name}__{rname}.txt"
            try:
                meta = fn(src, out)
            except Exception as exc:  # noqa: BLE001 - record, never mask
                meta = {"ok": False, "note": f"{type(exc).__name__}: {exc}"}
            entry = dict(meta)
            if meta.get("ok") and out.exists():
                got = out.read_bytes()
                entry.update({
                    "path": str(out.relative_to(BASE)),
                    "bytes": len(got),
                    "sha256": sha(got),
                    "identical_to_source": sha(got) == sha(src),
                    "byte_delta": len(got) - len(src),
                })
                flag = "IDENTICAL" if entry["identical_to_source"] else "DIFFERS"
                print(f"  {rname:<28} {flag:<10} {len(got):>7} bytes "
                      f"(delta {entry['byte_delta']:+d})")
            else:
                entry["identical_to_source"] = None
                print(f"  {rname:<28} UNAVAILABLE  {meta.get('note','')}")
            probe["routes"][rname] = entry
        results["probes"][probe_name] = probe

    out_json = ROUTES / "route_results.json"
    with out_json.open("w", encoding="utf-8") as fh:
        json.dump(results, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"\nWrote {out_json.relative_to(BASE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
