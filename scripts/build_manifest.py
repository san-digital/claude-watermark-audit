#!/usr/bin/env python3
"""Phase 3/7: freeze the evidence set into evidence/manifest.jsonl.

One JSON object per line, UTF-8, ensure_ascii=False so the decoded text is stored
as real characters rather than \\uXXXX escapes. Each record carries:

  sample_id, model, surface, provider, prompt_id, generation parameters,
  timestamp, stop reason / usage (where obtainable), the exact UTF-8 bytes as
  Base64, the decoded text, and the SHA-256 of the exact bytes.

The manifest is SELF-VERIFYING: for every record this script decodes the stored
Base64 and re-hashes it, asserting it reproduces the stored SHA-256 and the stored
decoded text. Any mismatch is a hard failure, not a warning.

Files are read in binary mode and never modified. This script only reads
evidence/raw/ and writes evidence/manifest.jsonl.
"""

from __future__ import annotations

import base64
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "evidence" / "raw"
OUT = BASE / "evidence" / "manifest.jsonl"

# Alias -> exact model identifier, as resolved by the harness. Recorded together
# with the verification caveat: these are ASSERTED, not measured from a response header.
MODEL_IDS = {
    "opus5": "claude-opus-5",
    "sonnet5": "claude-sonnet-5",
    "haiku45": "claude-haiku-4-5-20251001",
    "fable5": "claude-fable-5",
}

GENERATION_PARAMS = {
    "temperature": "not controllable via the Agent tool; harness default, value not observable",
    "top_p": "not controllable; not observable",
    "top_k": "not controllable; not observable",
    "max_tokens": "not controllable; not observable",
    "seed": "not supported by the Anthropic API",
    "system_prompt": "Claude Code subagent system prompt (harness-supplied) plus the audit's generator instructions",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def file_iso_mtime(p: Path) -> str:
    return datetime.fromtimestamp(p.stat().st_mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_record(sample_id: str, path: Path, **kw) -> dict:
    raw = path.read_bytes()
    rec = {
        "sample_id": sample_id,
        "path": str(path.relative_to(BASE)),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes_len": len(raw),
        "content_b64": base64.b64encode(raw).decode("ascii"),
        "recorded_utc": utc_now(),
        "file_mtime_utc": file_iso_mtime(path),
    }
    try:
        rec["text"] = raw.decode("utf-8")
        rec["decodes_as_utf8"] = True
    except UnicodeDecodeError as exc:
        rec["text"] = None
        rec["decodes_as_utf8"] = False
        rec["decode_error"] = str(exc)
    rec.update(kw)
    return rec


def verify(rec: dict) -> None:
    """Hard self-verification. Raises on any inconsistency."""
    raw = base64.b64decode(rec["content_b64"])
    if hashlib.sha256(raw).hexdigest() != rec["sha256"]:
        raise AssertionError(f"{rec['sample_id']}: base64 does not reproduce sha256")
    if len(raw) != rec["bytes_len"]:
        raise AssertionError(f"{rec['sample_id']}: base64 length mismatch")
    if rec.get("decodes_as_utf8") and raw.decode("utf-8") != rec["text"]:
        raise AssertionError(f"{rec['sample_id']}: decoded text does not match stored text")


def collect() -> list[dict]:
    records: list[dict] = []
    prompts_path = BASE / "evidence" / "prompts.json"
    prompt_meta = {}
    if prompts_path.exists():
        prompt_meta = {p["id"]: p for p in json.load(prompts_path.open())["prompts"]}

    # 1. Model corpus
    corpus = RAW / "corpus"
    if corpus.is_dir():
        for model_dir in sorted(corpus.iterdir()):
            if not model_dir.is_dir():
                continue
            slug = model_dir.name
            for f in sorted(model_dir.glob("*.txt")):
                pid = f.stem
                pm = prompt_meta.get(pid, {})
                records.append(make_record(
                    f"{slug}-{pid}", f,
                    kind="model_output",
                    model_slug=slug,
                    model_id=MODEL_IDS.get(slug, "unknown"),
                    model_id_verification=(
                        "asserted by harness alias resolution and weakly corroborated by "
                        "subagent self-report; NOT read from an API response header"
                    ),
                    surface="Claude Code subagent (Agent tool) -> Write tool -> file",
                    provider="Anthropic first-party API (api.anthropic.com)",
                    cloud_provider="none",
                    prompt_id=pid,
                    prompt_category=pm.get("category"),
                    prompt_length_band=pm.get("length_band"),
                    generation_params=GENERATION_PARAMS,
                    stop_reason="not exposed by the Agent tool",
                    usage="not exposed per-sample by the Agent tool",
                    presentation_layers=(
                        "model tokens -> tool-call JSON transport -> Write tool -> "
                        "filesystem (binary). No terminal, no Markdown renderer, no clipboard."
                    ),
                ))

    # 2. Controls
    controls_prov = RAW / "controls" / "provenance.json"
    prov = {}
    if controls_prov.exists():
        prov = {c["control_id"]: c for c in json.load(controls_prov.open())["controls"]}
    for sub in ("human", "synthetic"):
        d = RAW / "controls" / sub
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if not f.is_file():
                continue
            cid = f.stem
            c = prov.get(cid, {})
            records.append(make_record(
                f"control-{cid}", f,
                kind="control",
                control_class=c.get("class", sub),
                source=c.get("source", "unknown"),
                description=c.get("description", ""),
                retrieved_utc=c.get("retrieved_utc"),
                model_id="n/a (not model output)",
                surface="direct download or local tool output",
                provider=c.get("source", "unknown"),
            ))

    # 3. Presentation-route artefacts
    routes = BASE / "evidence" / "routes"
    if routes.is_dir():
        for f in sorted(routes.glob("*.txt")):
            records.append(make_record(
                f"route-{f.stem}", f,
                kind="presentation_route",
                model_id="n/a (fixed probe text, not model output)",
                surface=f.stem.split("__")[-1],
                provider="local",
                description="Phase 4 presentation-layer probe artefact",
            ))

    # 4. Scanner fixtures, if Subagent B has produced them
    fixtures = BASE / "tests" / "fixtures"
    if fixtures.is_dir():
        for f in sorted(fixtures.iterdir()):
            if f.is_file() and f.suffix in {".txt", ".json"}:
                records.append(make_record(
                    f"fixture-{f.stem}", f,
                    kind="scanner_fixture",
                    model_id="n/a (deterministic fixture)",
                    surface="tests/fixtures",
                    provider="local generator",
                    description="Scanner positive/negative control fixture",
                ))

    return records


def main() -> int:
    records = collect()
    if not records:
        print("no evidence found", file=sys.stderr)
        return 1
    for r in records:
        verify(r)  # raises on any inconsistency
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    # Re-read from disk and verify again, so the assertion covers the written file.
    n = 0
    with OUT.open("r", encoding="utf-8") as fh:
        for line in fh:
            verify(json.loads(line))
            n += 1
    assert n == len(records), "record count mismatch after write"

    by_kind: dict[str, int] = {}
    for r in records:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
    print(f"manifest: {n} records verified (base64 -> sha256 -> text all consistent)")
    for k, v in sorted(by_kind.items()):
        print(f"  {k:<22} {v}")
    print(f"  -> {OUT.relative_to(BASE)} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
