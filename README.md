# claude-watermark-audit

A reproducible investigation into machine-readable marking, watermarking and
fingerprinting in text produced by Claude.

The audit asks one question: **what can actually be established about
machine-readable marking in Claude-generated text**, with particular attention to
the widely repeated claim that Claude inserts hidden or unusual Unicode characters.

It is a **detection and verification** exercise. Nothing here attempts to remove,
evade, corrupt or reverse-engineer any watermark, and no attempt is made to recover
any secret key.

Read [`FINAL-REPORT.md`](FINAL-REPORT.md) first. Everything else is the evidence
behind it.

## Post-disclosure update: 15 August 2026

Two days after this corpus and report were frozen, Anthropic published
[How Claude's text watermark works](https://www.anthropic.com/news/claude-text-watermark).
It identifies Claude's method as a version of SynthID-Text and states that nothing is
added to the text and there are no hidden characters.

That disclosure is compatible with the audit's Unicode result, but it does not make
the corpus a test of Claude's statistical watermark. Anthropic has not published the
production key, compatible detector, decision rule or model-by-model rollout status.
Without those, this repository cannot directly score or exclude Claude's production
mark. The dated source notes are in
[`evidence/sources/`](evidence/sources/anthropic-news-claude-text-watermark-2026-08-15.md).

The original 12 August corpus, controls, routes, analysis and manifest remain
unchanged. A later private transcript diagnostic is deliberately excluded because it
has no immutable input manifest and contains material that cannot be published.

## Why this is public

This repository is the evidence behind two articles on
[declawd.com](https://declawd.com/articles), an educational demonstration by
San Digital of why a text watermark cannot prove who wrote something.

Those articles make counted claims: no hidden Unicode in 457,045 characters of
Claude output across four models, against 20,224 curly quotes in a human
control corpus. Claims like that are worth very little if a reader cannot check
them, so the corpus, the controls, the scanner, its test suite and a hashed
manifest of every artefact are all here.

The counted result is now best read as a test of a discarded hidden-character
theory. It neither confirms nor refutes SynthID-Text.

Nothing in this repository is affiliated with or endorsed by Anthropic. It
neither reproduces nor interoperates with Anthropic's production watermark, and
no result here should be used to support an authorship, employment,
disciplinary, academic or forensic decision.

## What was redacted before publishing

Two identifiers were removed from the reports and nothing else was altered: a
Claude Code session UUID, and a local worktree path containing directory names.
They appear as `<session-id>` and `<worktree>`. Every figure, hash, code point
and quotation is unchanged, and the manifest still verifies.

---

## What this audit can and cannot do

The most important thing to understand before reading any result:

| Surface | Status |
| --- | --- |
| Claude Code subagent → `Write` tool → file | **Tested** |
| Local file, shell, clipboard, pseudo-terminal, JSON transport routes | **Tested** |
| Raw Anthropic HTTP API response body | **Not possible here** — no usable credential |
| Official Anthropic SDK (Python / TypeScript) | **Not possible here** — not installed |
| claude.ai web or desktop rendering, and its Copy button | **Not possible here** — non-interactive session |
| Claude on Bedrock / Vertex AI / Microsoft Foundry | **Not possible here** — no pre-existing access |
| Token log-probabilities, temperature or seed control | **Not possible here** — not exposed |

Credential extraction from the host application was deliberately **not** attempted.
The full list, with reasons, is in [`evidence/environment.json`](evidence/environment.json)
under `unavailable_test_surfaces`.

Because a genuine raw-API capture was impossible, the closest available proxy was
used: a subagent's generated text written straight to disk by the `Write` tool. That
path is `model tokens → tool-call JSON transport → filesystem`. It never passes
through a Markdown renderer, a terminal or a clipboard. Phase 4 measures that
transport independently and shows it to be byte-transparent, which is what makes the
corpus trustworthy.

---

## Reproducing the audit

Requires Python 3.11+ and macOS or Linux. **No third-party packages**, no network
except for the human control download.

```bash
cd claude-watermark-audit
```

### 1. Record the environment

```bash
python3 scripts/record_environment.py
```

Writes `evidence/environment.json`: OS, locale, encodings, product versions, model
assignments, clipboard route, broad region and SHA-256 of every script. Contains no
secrets, tokens, account identifiers or absolute user paths.

### 2. Build the controls

```bash
python3 scripts/make_controls.py
```

Downloads five public-domain human works from Project Gutenberg as **raw bytes**,
generates compiler and disassembler output, and generates seeded pseudo-random ASCII.
Provenance, URLs and hashes land in `evidence/raw/controls/provenance.json`.

### 3. Validate the scanner against known controls

```bash
python3 tests/make_fixtures.py
python3 -m unittest discover -s tests -v
```

The fixtures contain deliberate examples of every flagged category, including a
hidden message encoded in Unicode tag characters. The suite proves the scanner
**detects** each positive control, leaves the **negative** ASCII control clean, and
reports smart quotes and em dashes as *typographic* rather than *invisible*. Real
recorded output is in [`tests/TEST-OUTPUT.txt`](tests/TEST-OUTPUT.txt).

Never trust a scanner that has not been shown to fire on a known positive.

### 4. Test the presentation layers

```bash
python3 scripts/route_test.py < /dev/null
```

Passes a fixed ASCII control and a Unicode probe through every locally accessible
route and hashes each result. Answers "does a clipboard, terminal or transport layer
add or strip Unicode on its own?" — which must be known before any character found
downstream can be attributed to a model.

### 5. Scan the corpus

```bash
python3 scripts/scan_unicode.py evidence/raw/corpus/*/*.txt --json > /tmp/scan.json
python3 scripts/scan_unicode.py evidence/raw/controls/human/*.txt --text
```

### 6. Compare any two artefacts byte by byte

```bash
python3 scripts/compare_bytes.py \
  evidence/routes/ascii_control__R0_source.txt \
  evidence/routes/ascii_control__R4_pty_terminal.txt
```

### 7. Freeze the evidence

```bash
python3 scripts/build_manifest.py
```

Writes `evidence/manifest.jsonl`, one self-verifying record per artefact: sample ID,
model, surface, provider, prompt ID, generation parameters, timestamp, exact UTF-8
bytes as Base64, decoded text and SHA-256. The script re-decodes every stored Base64
and asserts it reproduces the stored hash and text; a mismatch is a hard failure.

### Regenerating the corpus

`evidence/prompts.json` holds the 30 fixed prompts, byte-identical across models, so
no cross-model difference can be blamed on prompt variation. Regenerating the corpus
requires the Claude Code Agent tool with an authenticated session; the prompts and
the exact generator instructions are recorded so the collection can be repeated.

---

## Layout

```
FINAL-REPORT.md              Conclusions, evidence table, verdict
README.md                    This file

scripts/
  record_environment.py      Phase 1 environment record
  make_controls.py           Phase 6 human and synthetic controls
  scan_unicode.py            Phase 2 Unicode and byte scanner
  compare_bytes.py           Phase 4 byte-level and character-level diff
  route_test.py              Phase 4 presentation-route harness
  build_manifest.py          Phase 3/7 evidence freeze
  analyse_corpus.py          Phase 5 aggregate + hypothesis analysis

tests/
  make_fixtures.py           Deterministic fixture generator
  fixtures/                  Positive controls + ASCII negative control
  test_scan_unicode.py       Scanner and comparator test suite
  TEST-OUTPUT.txt            Real recorded test output

evidence/
  environment.json           Phase 1 record
  prompts.json               The 30 fixed prompts
  manifest.jsonl             Self-verifying evidence index
  raw/corpus/<model>/        Immutable model output, one file per prompt
  raw/controls/              Human and synthetic controls + provenance
  routes/                    Presentation-route probe artefacts
  sources/                   Archived first-party Anthropic pages
                             and dated post-disclosure source notes

reports/
  official-sources.md        Subagent A - first-party documentation
  unicode-forensics.md       Subagent B - Unicode and byte forensics
  statistical-analysis.md    Subagent C - corpus and statistical analysis
  independent-review.md      Subagent D - adversarial review
```

Everything under `evidence/raw/` is treated as immutable. Scripts open it read-only
and in binary mode. Normalization output is written elsewhere and never overwrites a
source.

---

## Method notes that matter

**Four model tiers, one collection surface.** Corpora were generated by subagents
pinned to `opus`, `sonnet`, `haiku` and `fable`, each writing its own output straight
to disk. Holding the surface constant is what makes a cross-model comparison mean
anything. Exact model identifiers are recorded in the manifest, together with the
caveat that alias-to-ID resolution is *asserted by the harness* and corroborated only
by each subagent's self-report — a model's belief about its own identity is not an
independent measurement.

**Generators were not primed.** No generator was told the study concerned Unicode,
watermarking or hidden characters. Telling them would have invited self-censorship of
their own typography and destroyed the measurement.

**Controls are not model output.** Using one language model's text as the only
negative control for another would be circular. The human controls are pre-LLM
public-domain prose; the synthetic controls are compiler and disassembler output and
seeded random ASCII.

**Rates, not counts.** The human control is roughly 3 million characters and the
model corpus far smaller, so all comparisons are per-character rates.

**Genre is a confounder.** Nineteenth-century fiction is dialogue-heavy and
quotation-dense; technical prose and code are not. Any comparison of typographic
punctuation between the two must either control for genre or say plainly that it
does not.

---

## Reading the findings

Every material finding carries exactly one classification:

- `Confirmed by Anthropic documentation`
- `Confirmed by reproduced experiment`
- `Observed anomaly, not established as watermark`
- `Plausible but unverified`
- `Not supported by evidence`
- `Test not possible in this environment`

A Unicode watermark can only be called *confirmed by experiment* if there is a
reproducible structured pattern in raw model output **and** credible evidence that
the pattern is deliberate marking. Unusual characters alone never meet that bar.

Two failure modes are avoided throughout, and they are not symmetrical:

1. Calling an anomaly a watermark without evidence of structure or intent.
2. Calling the absence of hidden Unicode proof that no watermark exists. A
   watermark carried in token selection would leave **no** unusual characters at all,
   and nothing in this environment could detect it.
