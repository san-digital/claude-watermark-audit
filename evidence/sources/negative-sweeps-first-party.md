# Archived source — negative-result sweeps across first-party Anthropic properties

- Retrieved (UTC): 2026-08-12T02:46Z – 03:05Z
- Method: `curl -L` with a desktop user agent, saving raw bytes, then case-insensitive regex counting over the retrieved payload (server-rendered HTML includes the embedded JSON content payload, so this catches text that a markdown converter may drop). The PDF system card was converted with `pdftotext` before searching.
- Purpose: establish where Anthropic does NOT mention watermarking, so that absence is recorded as evidence rather than assumed.

## Sweep terms

`watermark`, `provenance`, `C2PA`, `SynthID`, `zero-width`, `machine-readable`, `Article 50`, `content authenticity`, `Unicode`, `logit`, `invisible`, `marking`

## Results

| URL | HTTP | watermark | provenance | C2PA | SynthID | other sweep terms |
|---|---|---|---|---|---|---|
| https://support.claude.com/en/articles/16266773-how-claude-marks-ai-generated-content | 200 | 22 | 25 | 2 | 0 | machine-readable 10, Article 50 4, tamper 2 |
| https://www.anthropic.com/transparency/voluntary-commitments | 200 | 8 | 4 | 0 | 0 | none |
| https://www.anthropic.com/transparency | 200 | 4 | 2 | 0 | 0 | none |
| https://docs.claude.com/en/release-notes/api (→ platform.claude.com) | 200 | 0 | 0 | 0 | 0 | NONE |
| https://docs.claude.com/en/release-notes/claude-apps | 200 | 0 | 0 | 0 | 0 | NONE |
| https://support.claude.com/en/articles/12138966-release-notes (Claude Apps release notes) | 200 | 0 | 0 | 0 | 0 | NONE |
| https://docs.claude.com/en/docs/about-claude/models/overview | 200 | 0 | 0 | 0 | 0 | NONE |
| https://docs.claude.com/en/api/messages (Messages API reference) | 200 | 0 | 0 | 0 | 0 | NONE |
| https://www.anthropic.com/legal/aup (Usage Policy) | 200 | 0 | 0 | 0 | 0 | NONE |
| https://www.anthropic.com/news (newsroom index) | 200 | 0 | 0 | 0 | 0 | NONE |
| https://www.anthropic.com/news/claude-opus-5 | 200 | 0 | 0 | 0 | 0 | NONE |
| https://www.anthropic.com/news/claude-sonnet-5 | 200 | 0 | 0 | 0 | 0 | NONE |
| https://www.anthropic.com/research (index) | 200 | 0 | 0 | 0 | 0 | NONE |
| https://www.anthropic.com/engineering (index) | 200 | 0 | 0 | 0 | 0 | NONE |
| https://www.anthropic.com/claude-opus-5-system-card (PDF, 16.0 MB, 7,239 lines of extracted text) | 200 | 0 | 0 | 0 | 0 | NONE — the single `marking` hit is the substring inside "Benchmarking" in a bibliography entry (line 6636, "OSWorld 2.0: Benchmarking computer use agents…") |
| https://support.claude.com/en/articles/15425695-covered-models | 200 | 0 | 0 | 0 | 0 | NONE |
| https://www.anthropic.com/legal/eu-ai-act | **404** | — | — | — | — | page does not exist |
| https://www.anthropic.com/news/anthropic-eu-ai-act | **404** | — | — | — | — | page does not exist |

## Notable non-findings

- The **Claude Opus 5 System Card** (the model card for the current flagship model, and the model this audit is running on) contains NO mention of watermarking, provenance, C2PA, Article 50, or content marking of any kind.
- The **Claude Platform release notes**, covering every dated entry from 4 December 2025 through 11 August 2026, contain NO mention of watermarking, provenance, C2PA, marking, or Article 50. There is no release-note entry announcing marking.
- The **Messages API reference** contains no watermarking/provenance parameter, field, or response header.
- The **Usage Policy** does not mention marking, watermarks, or any restriction on removing marks.
- The "Covered Models" support article (updated 2026-07-01) is unrelated to marking — it concerns data-retention safeguards for Claude Mythos 5 and Claude Fable 5. It is easy to mistake for a watermarking-scope page; it is not one.

## False positive recorded for honesty

- `docs.claude.com` release-notes payload contains the UI string: "No stored fingerprint for that previous_message_id — not evidence your request changed." This is a Console UI string about request-body fingerprinting for message continuation. It is NOT related to content watermarking. Recorded so the term "fingerprint" is not later miscounted as a hit.

## First-party model launch dates (from Claude Platform release notes)

Retrieved verbatim from https://platform.claude.com/docs/en/release-notes/api :

- **July 24, 2026** — "We've launched **Claude Opus 5** (`claude-opus-5`), a step-change improvement over Claude Opus 4.8."
- **June 30, 2026** — "We've launched **Claude Sonnet 5** (`claude-sonnet-5`), the next generation of our Sonnet model family"
- **June 9, 2026** — Claude Fable 5 (`claude-fable-5`) generally available; Claude Mythos 5 limited availability (per the models overview: "Claude Fable 5 is generally available on the Claude API, Amazon Bedrock, Claude Platform on AWS, Google Cloud, and Microsoft Foundry beginning June 9, 2026.")

All of these precede 2 August 2026.

## Adjacent-but-not-evidence observation (sampling parameter locking)

From the same release notes, verbatim:

- June 30, 2026 (Claude Sonnet 5): "setting sampling parameters (`temperature`, `top_p`, `top_k`) to non-default values returns a 400 error"
- May 2026 entry: "Setting the sampling parameters `temperature`, `top_p`, or `top_k` to a non-default value returns a 400 error on Claude Opus 4.8, same as on Claude Opus 4.7."

Anthropic gives NO watermarking rationale for this. The lock was already in place on Claude Opus 4.7, well before the marking commitments were published. It is recorded here only so a later reader does not "discover" it and treat it as a smoking gun. It is not evidence of sampling-time watermarking.
