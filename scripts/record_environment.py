#!/usr/bin/env python3
"""Phase 1: record the test environment to evidence/environment.json.

Deliberately excludes secrets and personal identifiers:
  - No API keys, tokens, cookies or credentials. Only presence/absence booleans.
  - No absolute paths containing a username; paths are recorded relative to the
    audit directory.
  - No IP address, no precise geolocation. Region is derived from the system
    timezone and reported at country / broad-service-region level only.
  - No account, organisation or session identifiers.

Re-run this at the end of the audit so the recorded script hashes match the
final state of the scripts.
"""

from __future__ import annotations

import hashlib
import json
import locale
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "evidence" / "environment.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run(cmd: list[str]) -> str | None:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return p.stdout.strip() if p.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def script_hashes() -> dict:
    out = {}
    for sub in ("scripts", "tests"):
        d = BASE / sub
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*")):
            if p.is_file() and p.suffix in {".py", ".sh", ".ts", ".js", ".txt"}:
                # Exclude generated evidence; only hash tooling and fixtures.
                out[str(p.relative_to(BASE))] = {
                    "sha256": sha256_file(p),
                    "bytes": p.stat().st_size,
                }
    return out


def broad_region() -> dict:
    """Timezone-derived region only. No IP lookup, no precise location."""
    tz = None
    link = Path("/etc/localtime")
    if link.is_symlink():
        target = os.readlink(link)
        if "zoneinfo/" in target:
            tz = target.split("zoneinfo/", 1)[1]
    tz = tz or run(["date", "+%Z"]) or "unknown"
    country = {"Europe/London": "United Kingdom (GB)"}.get(tz, "not resolved")
    return {
        "system_timezone": tz,
        "country_broad": country,
        "method": "derived from /etc/localtime symlink; no IP geolocation performed",
        "note": "Anthropic API serving region is NOT observable from this environment.",
    }


def main() -> int:
    py_enc = {
        "sys.getdefaultencoding": sys.getdefaultencoding(),
        "sys.getfilesystemencoding": sys.getfilesystemencoding(),
        "locale.getpreferredencoding": locale.getpreferredencoding(False),
        "sys.stdout.encoding": getattr(sys.stdout, "encoding", None),
    }

    env = {
        "audit": "claude-watermark-audit",
        "phase": "Phase 1 - environment record",
        "generated_utc": utc_now(),
        "generator": "scripts/record_environment.py",

        "operating_system": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "platform": platform.platform(),
            "mac_product_name": run(["sw_vers", "-productName"]),
            "mac_product_version": run(["sw_vers", "-productVersion"]),
            "mac_build_version": run(["sw_vers", "-buildVersion"]),
        },

        "locale_and_encoding": {
            "LANG": os.environ.get("LANG", ""),
            "LC_ALL": os.environ.get("LC_ALL", ""),
            "LC_CTYPE": os.environ.get("LC_CTYPE", ""),
            "python_encodings": py_enc,
            "unicodedata_unidata_version": __import__("unicodedata").unidata_version,
            "note": (
                "unicodedata is Unicode 14.0.0 (bundled with CPython 3.11). Code points "
                "assigned after Unicode 14 will scan as unnamed. This is a stated "
                "limitation of the scanner, not evidence about any model."
            ),
        },

        "claude_product": {
            "surface": "Claude Code (agent harness, non-interactive session)",
            "claude_code_version": (run(["claude", "--version"]) or "unknown"),
            "claude_agent_sdk_version": os.environ.get("CLAUDE_AGENT_SDK_VERSION", "unset"),
            "entrypoint": os.environ.get("CLAUDE_CODE_ENTRYPOINT", "unset"),
            "anthropic_base_url_host": "api.anthropic.com",
            "base_url_note": (
                "ANTHROPIC_BASE_URL resolves to the first-party Anthropic API host. "
                "No third-party gateway, proxy or cloud reseller is in the path."
            ),
        },

        "models": {
            "orchestrator": {
                "assigned": "claude-fable-5",
                "alias_used": "n/a (session model)",
                "verification": "reported by the harness system prompt; not independently verifiable from inside the process",
            },
            "subagents": {
                "selection_mechanism": "Agent tool `model` parameter (alias -> harness resolution)",
                "aliases_available": ["opus", "sonnet", "haiku", "fable"],
                "assignments": {
                    "A_official_sources": "opus",
                    "B_unicode_forensics": "fable",
                    "C_statistical": "sonnet",
                    "D_sceptical_review": "haiku",
                    "generator_opus5": "opus",
                    "generator_sonnet5": "sonnet",
                    "generator_haiku45": "haiku",
                    "generator_fable5": "fable",
                },
                "expected_resolution": {
                    "opus": "claude-opus-5",
                    "sonnet": "claude-sonnet-5",
                    "haiku": "claude-haiku-4-5-20251001",
                    "fable": "claude-fable-5",
                },
                "verification_caveat": (
                    "Alias-to-exact-ID resolution is asserted by the harness environment, and "
                    "each subagent additionally self-reports its runtime model. Self-reports are "
                    "WEAKLY VERIFIED: a model's belief about its own identity is not an "
                    "independent measurement. No response header or API metadata exposing the "
                    "served model ID is reachable from this environment."
                ),
            },
        },

        "api_access": {
            "direct_http_api": "UNAVAILABLE",
            "official_sdk": "UNAVAILABLE",
            "detail": (
                "No ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN or CLAUDE_CODE_OAUTH_TOKEN is present "
                "in the environment. A nested `claude -p` invocation fails with "
                "'Failed to authenticate: OAuth session expired and could not be refreshed'. "
                "Neither the Python `anthropic` package nor `@anthropic-ai/sdk` is installed, and "
                "no package installation was attempted. Extracting the host application's stored "
                "credentials was deliberately NOT attempted."
            ),
            "credential_presence_only": {
                "ANTHROPIC_API_KEY": bool(os.environ.get("ANTHROPIC_API_KEY")),
                "ANTHROPIC_AUTH_TOKEN": bool(os.environ.get("ANTHROPIC_AUTH_TOKEN")),
                "CLAUDE_CODE_OAUTH_TOKEN": bool(os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")),
            },
        },

        "shell_terminal_editor": {
            "shell": os.environ.get("SHELL", "unknown"),
            "shell_version": run(["zsh", "--version"]),
            "bash_version": (run(["bash", "--version"]) or "").split("\n")[0] or None,
            "TERM": os.environ.get("TERM", "unset"),
            "stdout_is_a_tty": sys.stdout.isatty(),
            "terminal_note": (
                "Commands run under an agent harness, not an interactive terminal. "
                "Terminal rendering was tested explicitly with a stdlib pseudo-terminal "
                "(scripts/route_test.py route R4)."
            ),
            "editor": "none; all files written by the agent Write tool or by Python",
            "python": sys.version.split()[0],
            "git": run(["git", "--version"]),
            "node": run(["node", "--version"]),
        },

        "clipboard_route": {
            "mechanism": "macOS NSPasteboard via /usr/bin/pbcopy and /usr/bin/pbpaste",
            "tested": True,
            "limitation": (
                "This is the operating system clipboard only. The claude.ai web 'Copy' "
                "button and any JavaScript clipboard handler in Claude's web or desktop "
                "interface were NOT tested and are not reachable from this environment."
            ),
        },

        "cloud_provider": {
            "provider": "none",
            "detail": "Direct first-party Anthropic API host. Not Bedrock, not Vertex AI, not Azure/Foundry.",
        },

        "region": broad_region(),

        "unavailable_test_surfaces": [
            {"surface": "Raw Anthropic HTTP API response body",
             "reason": "No usable API credential in this environment; credential extraction not attempted.",
             "classification": "Test not possible in this environment"},
            {"surface": "Official Anthropic SDK (Python or TypeScript)",
             "reason": "Neither SDK installed; no package installation performed.",
             "classification": "Test not possible in this environment"},
            {"surface": "claude.ai web interface rendered output",
             "reason": "Non-interactive session; no authenticated browser session available.",
             "classification": "Test not possible in this environment"},
            {"surface": "claude.ai / desktop app 'Copy' button handler",
             "reason": "Requires the authenticated web or desktop interface.",
             "classification": "Test not possible in this environment"},
            {"surface": "Manual human selection-and-copy from the rendered interface",
             "reason": "Requires a human at an interactive GUI session.",
             "classification": "Test not possible in this environment"},
            {"surface": "Claude on Amazon Bedrock",
             "reason": "No pre-existing access; obtaining paid services for this test was out of scope.",
             "classification": "Test not possible in this environment"},
            {"surface": "Claude on Google Cloud Vertex AI",
             "reason": "No pre-existing access; obtaining paid services for this test was out of scope.",
             "classification": "Test not possible in this environment"},
            {"surface": "Claude on Microsoft Foundry",
             "reason": "No pre-existing access; obtaining paid services for this test was out of scope.",
             "classification": "Test not possible in this environment"},
            {"surface": "Cowork",
             "reason": "Not available in this environment.",
             "classification": "Test not possible in this environment"},
            {"surface": "Temperature / top_p / seed control over generation",
             "reason": "The Agent tool exposes no sampling parameters; harness defaults apply and are not observable.",
             "classification": "Test not possible in this environment"},
            {"surface": "Token-level logprobs",
             "reason": "Not exposed by the Anthropic API or the harness. A statistical-watermark test at token level is therefore impossible here.",
             "classification": "Test not possible in this environment"},
        ],

        "available_test_surfaces": [
            "Claude Code subagent (Agent tool) -> model text -> Write tool -> file on disk",
            "Claude Code orchestrator assistant turn -> Write tool -> file on disk",
            "Local file write (Python binary and text mode)",
            "Shell redirection",
            "macOS system clipboard round-trip (pbcopy/pbpaste)",
            "Pseudo-terminal round-trip (stdlib pty)",
            "JSON tool-transport round-trip (ensure_ascii both settings)",
        ],

        "test_script_hashes": script_hashes(),

        "privacy_note": (
            "No secrets, tokens, cookies, account identifiers, organisation identifiers, "
            "session identifiers, IP addresses or absolute user paths are recorded in this file."
        ),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as fh:
        json.dump(env, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"wrote {OUT.relative_to(BASE)} ({OUT.stat().st_size} bytes, "
          f"{len(env['test_script_hashes'])} script hashes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
