# Subagent A — Official-source research: Anthropic's stated position on marking Claude-generated text

Audit date: 2026-08-12. All access timestamps UTC.

> **Post-disclosure status:** This report records the public record as it stood on
> 12 August. Anthropic published a technical announcement on 14 August naming a
> version of SynthID-Text. The dated update is recorded in
> `evidence/sources/anthropic-news-claude-text-watermark-2026-08-15.md`; its newer
> statements supersede this report's mechanism-disclosure negatives.

---

## Runtime model self-report

**Reported identifier: `claude-opus-5` (Claude Opus 5).**

Verification status: **partially verifiable — stronger than self-report, weaker than a server attestation.**

Three independent signals, in ascending order of strength:

1. **Self-report / system prompt (weak).** My system prompt states I am "powered by the model named Opus 5" with "exact model ID … claude-opus-5". This is unverifiable from inside the model and is exactly the kind of claim this audit should distrust.
2. **Process environment (no signal).** The environment contains `CLAUDE_AGENT_SDK_VERSION=0.3.221`, `AI_AGENT=claude-code_2-1-221_agent`, `CLAUDE_EFFORT=xhigh`, `CLAUDE_CODE_SESSION_ID=<session-id>`, `ANTHROPIC_BASE_URL=https://api.anthropic.com`. **There is no model environment variable.** Absence recorded rather than glossed.
3. **Harness transcript (moderately strong, and external to me).** The Claude Code harness writes a per-session JSONL log at
   `~/.claude/projects/<project>/<session-id>.jsonl`.
   Every assistant turn carries a `model` field. Within my working window (from 02:46:22Z onward) **every** assistant row is `claude-opus-5`. I tied a specific row to my own action rather than trusting the aggregate: the turn that issued my first fetch of the support article (containing the string `16266773`) is timestamped `2026-08-12T02:46:22.690Z` and logged as `model=claude-opus-5`.
   Seven earlier rows in the same file (02:43–02:44Z, before my task began) are logged as `claude-opus-4-8`. I have not established what those belong to; they precede my first tool call and are probably the orchestrating session. I record them rather than suppress them.

**Honest limitation:** the transcript is written by the local harness — it records the model the *client requested*, not a cryptographically attested statement of what served the request. I cannot verify server-side which weights produced these tokens. I did not attempt an authenticated API call to check, as no API key is present (OAuth only).

**Material consequence for this audit:** `claude-opus-5` was launched **24 July 2026**, which is **before** the 2 August 2026 boundary Anthropic uses to define marking support. See the models section — this is the single most important finding in this report.

---

## Method

- **Fetch strategy:** every key page was retrieved twice where feasible — once via `WebFetch` (markdown conversion, LLM-extracted) and once via `curl -L` saving raw bytes. Raw bytes matter because Anthropic's marketing site is server-rendered with an embedded JSON content payload; a markdown converter silently drops parts of it. This caught a real discrepancy: `WebFetch` reported "no matches" for watermark on `anthropic.com/transparency` while the raw payload contained four. Where the two disagreed, I used the raw payload.
- **The primary support article was reconciled across both methods and the body text matched exactly**, so the archived transcript is a genuine verbatim record rather than an LLM paraphrase.
- **PDF handling:** the Claude Opus 5 system card is a 16.0 MB PDF (`%PDF-1.4`, Title "Claude Opus 5 System Card"). My first regex sweep over the compressed bytes was unsound; I re-ran it after `pdftotext` extraction (7,239 lines). Recording this because the first-pass result would have been an invalid negative.
- **Fetches:** 20 URLs retrieved (18 × HTTP 200, 2 × HTTP 404), plus 5 WebSearch queries.
- **Failures / redirects recorded exactly:**
  - `https://docs.claude.com/en/release-notes/api` → **301** to `https://platform.claude.com/docs/en/release-notes/api` (cross-host; followed explicitly).
  - `https://www.anthropic.com/legal/eu-ai-act` → **404**. Page does not exist.
  - `https://www.anthropic.com/news/anthropic-eu-ai-act` → **404**. Page does not exist.
- **Domains searched:** support.claude.com, docs.claude.com, platform.claude.com, docs.anthropic.com, www.anthropic.com (news / research / engineering / transparency / legal), trust.anthropic.com.
- **Archived to** `evidence/sources/`: `support-16266773-how-claude-marks-ai-generated-content.md`, `anthropic-transparency-hub-voluntary-commitments.md`, `negative-sweeps-first-party.md`.

---

## Source inventory

| URL | Title | Date stated | Accessed (UTC) | First-party? |
|---|---|---|---|---|
| https://support.claude.com/en/articles/16266773-how-claude-marks-ai-generated-content | How Claude marks AI-generated content | "Updated yesterday"; HTML `dateModified` = **2026-08-10T19:03:20Z** | 2026-08-12 02:46 | **y** |
| https://www.anthropic.com/transparency/voluntary-commitments | Anthropic's Transparency Hub — Voluntary Commitments | Last updated **July 23, 2026** | 2026-08-12 02:52 | **y** |
| https://www.anthropic.com/transparency | Anthropic's Transparency Hub | Last updated **July 23, 2026** | 2026-08-12 02:58 | **y** |
| https://platform.claude.com/docs/en/release-notes/api | Claude Platform release notes | Entries dated 2025-12-04 → **2026-08-11** | 2026-08-12 02:57 | **y** |
| https://docs.claude.com/en/release-notes/claude-apps | Claude Apps release notes | not stated | 2026-08-12 02:51 | **y** |
| https://support.claude.com/en/articles/12138966-release-notes | Release notes (Claude Apps) | not stated | 2026-08-12 03:02 | **y** |
| https://docs.claude.com/en/docs/about-claude/models/overview | Models overview | not stated | 2026-08-12 02:55 | **y** |
| https://platform.claude.com/docs/en/about-claude/models/whats-new-opus-5 | What's new in Claude Opus 5 | not stated | 2026-08-12 02:59 | **y** |
| https://docs.claude.com/en/api/messages | Messages — Claude API Reference | not stated | 2026-08-12 02:55 | **y** |
| https://www.anthropic.com/claude-opus-5-system-card | Claude Opus 5 System Card (PDF) | not stated in extracted text | 2026-08-12 03:02 | **y** |
| https://www.anthropic.com/news/claude-opus-5 | Introducing Claude Opus 5 | published 2026-07-24 | 2026-08-12 02:55 | **y** |
| https://www.anthropic.com/news/claude-sonnet-5 | Introducing Claude Sonnet 5 | published 2026-06-30 | 2026-08-12 02:55 | **y** |
| https://www.anthropic.com/legal/aup | Usage Policy | not stated | 2026-08-12 02:55 | **y** |
| https://www.anthropic.com/news | Newsroom index | n/a | 2026-08-12 02:51 | **y** |
| https://www.anthropic.com/research | Research index | n/a | 2026-08-12 03:04 | **y** |
| https://www.anthropic.com/engineering | Engineering index | n/a | 2026-08-12 03:04 | **y** |
| https://support.claude.com/en/articles/15425695-covered-models | Covered Models | Updated **July 1, 2026** (`dateModified` 2026-07-01T19:31:02Z) | 2026-08-12 03:03 | **y** |
| https://www.anthropic.com/legal/eu-ai-act | — | — | 2026-08-12 03:02 | **404 — does not exist** |
| https://www.anthropic.com/news/anthropic-eu-ai-act | — | — | 2026-08-12 03:02 | **404 — does not exist** |

---

## Verification of the six task-author claims

The task author's summary was **broadly accurate but materially incomplete in two ways**: it omitted the C2PA/file half of the policy entirely, and it did not register that the page's tense and scope qualifiers place almost everything in the future.

### Claim 1 — "supported models embed an imperceptible watermark directly into generated text"

**Verdict: `Confirmed by Anthropic documentation`, with a load-bearing qualifier the summary dropped.**

> "When a supported Claude model generates text, it weaves an imperceptible watermark directly into the text itself."

> "You won't see it, and it doesn't change the meaning, quality, or readability of Claude's response."

The word **"supported"** carries the entire claim. Anthropic never states which models are supported by name (see below), so this sentence is unfalsifiable as written.

### Claim 2 — "it travels with copied text and may survive some editing"

**Verdict: `Confirmed by Anthropic documentation` — but stated in the future tense.**

> "Because the watermark is part of the text, it will travel with the text when it's copied and pasted elsewhere, and may persist through some editing."

Note "**will** travel", not "travels". Note also the hedge "**may** persist through **some** editing" — Anthropic makes no robustness claim whatsoever.

### Claim 3 — "it is applied at model level"

**Verdict: `Confirmed by Anthropic documentation` — future tense.**

> "Watermarking will be applied at the model level, which means it will be present no matter which Claude product or surface the text comes from."

This is the sentence that, if true and in force, would mean API output and subagent output are marked identically to chat output.

### Claim 4 — "models launched on or after 2 August 2026 support marking at launch"

**Verdict: `Confirmed by Anthropic documentation`, but the page states this TWICE in mutually inconsistent forms.** This is a real defect in the source, not a reading error.

In the "What's covered" section (present tense, no region qualifier):

> "Claude models launched on or after August 2, 2026 support marking at launch."

In the commitments bullets near the top (future tense, **EU-qualified**):

> "Claude models launched in the EU on or after August 2, 2026 will support machine-readable marking at launch."

One says *support*; the other says *will support*. One is unqualified; the other says *in the EU*. A separate bullet then asserts worldwide scope ("wherever Claude is offered, worldwide"). These cannot all be the most precise statement. **Classification of the discrepancy itself: `Confirmed by Anthropic documentation` (both sentences verifiably appear on the page).**

### Claim 5 — "support for older models is being added"

**Verdict: `Confirmed by Anthropic documentation`.**

> "We're also working to add marking support to Claude models released before that date, and we'll update this article as that becomes available."

> "The law includes a transition period for Anthropic models launched before August 2, 2026, and we're working to add marking support for those models as well."

No date, no model list, no completion criterion is given.

### Claim 6 — "public detection details are forthcoming"

**Verdict: `Confirmed by Anthropic documentation`.**

> "We'll share details on detection mechanisms in forthcoming technical documentation."

> "We'll support users and other third parties to detect Claude's marks, as the Code requires, and we'll share details in forthcoming documentation."

I enumerated every hyperlink on the page. **No technical documentation, detector, verification endpoint, API reference, or partner programme is linked.** The only outbound article links are unrelated help-centre items (incorrect responses, training on outputs, logging in, Claude for Government, Covered Models).

### Omission the task author's summary missed

The page describes **two** techniques, not one. The second is entirely absent from the brief:

> "Claude uses two complementary techniques to mark content generated and processed by Claude: (1) watermarks embedded in text, and (2) signed provenance metadata attached to files."

> "When Claude generates a supported file type, such as a .svg, .png, or .jpg, it will attach signed provenance metadata."

> "This metadata follows the Coalition for Content Provenance and Authenticity (C2PA) open standard"

---

## Which models are covered

**Verdict: `Not supported by evidence` that Anthropic has named ANY specific model as marking-enabled.**

Anthropic names **zero exact model identifiers** anywhere in the marking article. No `claude-opus-5`, no `claude-sonnet-5`, no `claude-fable-5`, no `claude-haiku-4-5-20251001`. **The supported set is defined purely by a launch date relative to 2 August 2026.** I did not invent IDs to fill this gap.

Cross-referencing that date rule against Anthropic's own first-party launch record (Claude Platform release notes and models overview) produces the central finding of this report:

| Model | Exact API ID | First-party launch date | On/after 2 Aug 2026? |
|---|---|---|---|
| Claude Opus 5 | `claude-opus-5` | **24 July 2026** | **No** |
| Claude Sonnet 5 | `claude-sonnet-5` | **30 June 2026** | **No** |
| Claude Fable 5 | `claude-fable-5` | **9 June 2026** | **No** |
| Claude Mythos 5 | `claude-mythos-5` | 9 June 2026 (limited availability) | **No** |
| Claude Opus 4.8 / 4.7 / 4.6, Sonnet 4.6 / 4.5, Haiku 4.5 | `claude-opus-4-8` etc. | earlier | **No** |

Verbatim from the release notes:

> "**July 24, 2026** … We've launched **Claude Opus 5** (`claude-opus-5`), a step-change improvement over Claude Opus 4.8."

> "**June 30, 2026** … We've launched **Claude Sonnet 5** (`claude-sonnet-5`), the next generation of our Sonnet model family"

**Therefore: as of 2026-08-12, not one generally available Claude model falls into the "supports marking at launch" bucket by Anthropic's own definition. Every current model sits in the "existing models are in progress" transition bucket.**

Two conclusions must be kept apart:

- *"Anthropic has confirmed that current Claude models watermark their text output"* — **`Not supported by evidence`.** No first-party source states this for any named model.
- *"Current Claude models, including `claude-opus-5`, do not watermark their text"* — also **not established**. Anthropic says work on pre-August models is "in progress", which is compatible with marking having quietly shipped to some of them. The true status of `claude-opus-5` output today is **`Plausible but unverified`** in both directions. This is precisely the question the experimental subagent must settle empirically.

---

## Which surfaces are covered / where the docs are silent

Named explicitly (verbatim):

> "Claude markings cover output from supported models everywhere you use Claude, including Claude Platform (API), Claude, Claude Code, Claude Cowork, and Claude Tag."

- **The Anthropic API is explicitly in scope, not silent** — "Claude Platform (API)" is named twice. This directly answers the task's question.
- **claude.ai / Claude apps** — covered as "Claude".
- **Claude Code** — named.
- **Claude Cowork** — named.
- **Claude Tag** — named.
- **Bedrock / Vertex / Foundry** — covered by parent-company name, with a carve-out:
  > "Embedded watermarks will apply when supported Claude models are accessed through AWS, Google Cloud, or Microsoft Foundry. Signed provenance metadata may not be supported on every platform, depending on the features each platform offers."
- **Text vs files split:** "Embedded watermarks will apply to all generated text. Provenance metadata will apply where Claude supports processing files."
- **Regions:** "Marking will apply to output from supported models wherever Claude is offered, worldwide." (In tension with the EU-qualified bullet — see Claim 4.)

**Silent on:**

- **Subagents** — never mentioned on any first-party page. The "model level" claim would imply coverage, but that is inference, not documentation. `Plausible but unverified`.
- **Extended thinking / reasoning blocks** — never distinguished from response text. Unstated whether thinking tokens are marked.
- **Tool-call arguments, structured/JSON output, code** — never distinguished from prose. "All generated text" is the only guidance.
- **Streaming vs non-streaming** — never addressed.
- **Any global blanket caveat:** "Some platforms or features may not support certain marking types" — undefined which.

---

## Mechanism disclosure

**Verdict: the text-watermark mechanism is `Not supported by evidence` — that is, entirely UNDISCLOSED.**

**What IS disclosed:**

- That a text watermark is claimed to be *imperceptible*, *part of the text itself*, *copy-paste-persistent*, *possibly edit-persistent*, and *applied at the model level*.
- That it degrades on short passages: "The passage is very short, leaving too little text for a reliable signal." This is the **only** technical hint in the entire corpus, and it is a strong one: a length-dependent "reliable signal" is characteristic of a *statistical/distributional* watermark rather than a lookup of literal inserted characters. **Classification: `Plausible but unverified`** — it is an inference from a limitation statement, not a disclosure, and I am flagging it as exactly that.
- That the **file** mechanism is C2PA, cryptographically signed, and tamper-evident. This is a genuine, specific, named mechanism disclosure — **but only for `.svg`, `.png`, `.jpg` files, never for text.**

**What is NOT disclosed:** the encoding scheme, the detector, the key model, the false-positive rate, the minimum reliable text length, robustness bounds, whether detection is public or gated, and whether any of it is live today.

**Do not conflate the two.** The strongest available restatement is: *Anthropic has published a policy commitment to text watermarking whose mechanism is undisclosed, alongside a specific, named, disclosed mechanism (C2PA) that applies only to image/vector files.*

---

## Targeted keyword sweep — first-party corpus

One line each, verdict per term. Full counts in `evidence/sources/negative-sweeps-first-party.md`.

| Term | Result across all first-party sources |
|---|---|
| **Unicode** | Zero first-party mentions in any watermarking context. `Not supported by evidence`. |
| **Invisible / zero-width characters** | Zero mentions. Anthropic says "imperceptible", never "invisible character". `Not supported by evidence`. |
| **Token probabilities / logit biasing** | Zero mentions. `Not supported by evidence`. |
| **Sampling-time watermarking** | Zero mentions. Sampling is discussed only as `temperature`/`top_p`/`top_k` API params, with no marking rationale. `Not supported by evidence`. |
| **Lexical / synonym selection** | Zero mentions. (Press claims about "word selection and phrasing" are **not** Anthropic's words — see Secondary leads.) `Not supported by evidence`. |
| **SynthID / SynthID-Text** | **Zero first-party mentions anywhere.** No Anthropic page names SynthID. `Not supported by evidence`. |
| **C2PA / Content Credentials / CAI** | **DISCLOSED — but for files only.** "This metadata follows the Coalition for Content Provenance and Authenticity (C2PA) open standard". Applies to `.svg`, `.png`, `.jpg`. Never applied to text. `Confirmed by Anthropic documentation`. |
| **Cryptographic signatures** | Disclosed for **files** ("digitally signed provenance metadata", tamper detection). Never claimed for text. `Confirmed by Anthropic documentation` (files) / `Not supported by evidence` (text). |
| **Provenance API** | No provenance API, parameter, response field, or response header exists in the Messages API reference or anywhere in the platform docs. `Not supported by evidence`. |
| **Public/private detector, verification endpoint, partner programme** | **Does not exist as of 2026-08-12.** Only a forward promise: "forthcoming technical documentation". No link, no waitlist, no partner programme, no endpoint. `Not supported by evidence`. |

### API-specific check (task item 7)

Swept the Messages API reference and the full Claude Platform release notes (every dated entry, 4 Dec 2025 → 11 Aug 2026): **zero occurrences** of watermark, watermarking, provenance, C2PA, marking, content authenticity, or Article 50. **There is no release-note entry announcing marking, and no API parameter, response field, or response header relating to it.** `Not supported by evidence`.

One false positive recorded for honesty: a Console UI string, "No stored fingerprint for that previous_message_id — not evidence your request changed." This concerns request-body fingerprinting for message continuation and is unrelated to content marking.

---

## Implemented now vs planned/forthcoming

### Stated as implemented now

Almost nothing. Only two present-tense assertions exist in the entire first-party corpus, and both are scope-gated by the undefined word "supported":

1. "Claude models launched on or after August 2, 2026 **support** marking at launch." — vacuous today, because **no such model exists** (latest launch: `claude-opus-5`, 24 July 2026).
2. "When a supported Claude model generates text, it **weaves** an imperceptible watermark directly into the text itself." — conditional on the same empty set.

### Stated as planned / forthcoming

Everything of substance. Every operative sentence is future tense:

- "will support machine-readable marking at launch"
- "Generated text **will** carry embedded watermarks"
- "Marks **will** apply to output from supported Claude models across Claude Platform (API), Claude, Claude Code, Claude Cowork, and Claude Tag"
- "it **will** travel with the text when it's copied and pasted"
- "Watermarking **will** be applied at the model level"
- "it **will** attach signed provenance metadata"
- "Embedded watermarks **will** apply when supported Claude models are accessed through AWS, Google Cloud, or Microsoft Foundry"
- "We're **working to** add marking support to Claude models released before that date"
- "We're **also working to** enable users and other third parties to detect Claude's embedded watermarks"
- "We'll share details on detection mechanisms in **forthcoming** technical documentation"
- "we'll share technical guidance on our marking and detection approach **as it becomes available**"

**Corroborating first-party evidence that this is forward-looking, not deployed:** the Transparency Hub, last updated **23 July 2026**, still says:

> "We have worked across industry and academia to explore and stay abreast of technological developments for watermarking and are **preparing for compliance** with applicable laws by the relevant legal deadlines."

That is preparation language, three weeks before the support article, and the Hub has not been updated since.

---

## Anything newer than the support article

**Nothing.** The support article (`dateModified` 2026-08-10T19:03:20Z) is the newest and only substantive first-party source. Specifically checked and found silent:

- **Claude Platform release notes** through 11 Aug 2026 — no marking entry.
- **Claude Apps release notes** — no marking entry.
- **Claude Opus 5 System Card** (16 MB PDF, 7,239 lines extracted) — **zero** mentions of watermark, provenance, C2PA, or Article 50. The flagship model card is silent on marking.
- **Newsroom** (13 current posts incl. `/news/claude-opus-5`, `/news/claude-sonnet-5`) — no marking post; the model launch posts do not mention it.
- **Research and Engineering indexes** — zero mentions.
- **Usage Policy** — silent; notably, it contains **no prohibition on removing or tampering with marks**.
- **Transparency Hub** — last updated 23 July 2026, pre-dates the article, still says "preparing for compliance".
- `anthropic.com/legal/eu-ai-act` and `anthropic.com/news/anthropic-eu-ai-act` — both **404**.

**On C2PA for images/files as distinct from text (explicitly asked):** yes, Anthropic distinguishes them, and only within the support article. C2PA is scoped to `.svg`, `.png`, `.jpg`. Separately, the Transparency Hub's child-safety commitments include "Include content provenance on image and video outputs" — again media, not text. **No first-party source ever applies C2PA to text.**

---

## Secondary leads — QUARANTINED, non-evidential

**These are NOT evidence of what Anthropic does.** Listed only because they surfaced in search and one contains a specific mechanism claim that must be actively rebutted rather than silently ignored.

- the-decoder.com, siliconangle.com, cryptobriefing.com, interestingengineering.com, techtimes.com, cyberkendra.com — all 10–11 Aug 2026, all derivative recaps of the same support article.
- **Active correction required:** search summarisation of this press produced the claim that the watermark is "woven into the statistical patterns of the text, the subtle choices in word selection and phrasing that a language model makes billions of times per output." **This phrasing appears nowhere in any Anthropic source.** I verified the support article twice by independent retrieval; it contains no such sentence. This is journalistic extrapolation from the word "weaves". **Anyone encountering this claim downstream should treat it as `Not supported by evidence`.** It is the single most likely vector for a false mechanism belief entering this audit.
- None of these outlets point to any first-party artefact beyond the support article itself. **No secondary lead is worth chasing.**

---

## Open questions Anthropic has not answered

1. **Is `claude-opus-5` output watermarked today?** Unanswerable from documentation. It launched 24 July 2026, before the cutoff, so it is in the unspecified "in progress" bucket. **This is the question the experimental work must answer.**
2. **Which models, by exact ID, are marking-enabled right now?** No list exists.
3. **What is the text mechanism?** Wholly undisclosed.
4. **When does detection ship, and to whom?** No date, no access model, no waitlist.
5. **Is detection public, gated, or partner-only?** Unstated.
6. **What is the minimum reliable text length?** Only "very short" — no number.
7. **What robustness is claimed?** Only "may persist through some editing" — no bound, no threat model.
8. **False-positive rate?** Never mentioned. Critical for any accusatory use.
9. **Does the EU-only qualifier or the worldwide claim govern?** The page asserts both.
10. **Are thinking blocks, tool arguments, structured output, and code marked?** Undefined.
11. **Are subagent outputs marked?** Never addressed.
12. **Which platforms/features are the excluded "some"?** Undefined.
13. **Is removing a mark a policy violation?** The Usage Policy is silent.
14. **Why has the Transparency Hub not been reconciled with the support article?**

---

## Confidence statement

**High confidence** in what Anthropic has and has not published. Every material quote was verified by two independent retrieval paths, and the primary article's body text was reconciled byte-for-byte between a markdown conversion and a raw HTML extraction. Negative results were re-run after I found that my first PDF sweep was methodologically unsound, and after I found that markdown conversion had produced a false negative on the Transparency Hub. I consider the negatives trustworthy.

**High confidence** that the text-watermark mechanism is undisclosed, that no detector exists publicly as of 2026-08-12, and that there is no API surface for marking.

**High confidence** in the launch dates, which come from Anthropic's own dated release notes.

**The load-bearing inference — and its limit.** The chain "Anthropic marks models launched on/after 2 Aug 2026" + "every current model launched before that date" ⇒ "no current model is documented as marking-enabled" is sound as a statement *about the documentation*. It is **not** proof that current output is unmarked. Anthropic explicitly says retrofitting is in progress and gives no completion date, so silent deployment to pre-August models is entirely possible. **Documentation cannot settle this; only experiment can.** I have deliberately not let the strength of the documentary finding leak into a claim about physical reality.

**Residual risk:** help-centre pages are edited without version history, so wording may change after 2026-08-10T19:03:20Z. The archived verbatim copy in `evidence/sources/` is the fixed record for this audit.

---

## 15 August follow-up

The follow-up opened Anthropic's 14 August announcement, the Help Centre article,
the Platform release notes, the Models overview and the public Models API reference.
Anthropic now says Claude uses a version of SynthID-Text and that no hidden
characters are added. It says older-model rollout is continuing, but still names no
older model as enabled and publishes no compatible detector, key, threshold or error
rates.

The documented Models API schema lists nine capability groups and `created_at`; it
does not document marking or provenance status. No authenticated API response was
captured, so no claim is made about the fields returned by a live account or about
whether marking is enabled. The complete bounded observation is in
`evidence/sources/models-api-capabilities-2026-08-15.md`.
