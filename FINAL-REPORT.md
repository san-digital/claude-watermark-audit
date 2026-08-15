# Machine-readable marking in Claude-generated text

**An audit of watermarking, fingerprinting and hidden Unicode**

Date: 12 August 2026 (UTC)
Scope: detection and technical verification only. No attempt was made to remove, evade, corrupt or reverse-engineer any watermark, or to recover any key.

---

## Post-disclosure note, checked 15 August 2026

Anthropic published [How Claude's text watermark works](https://www.anthropic.com/news/claude-text-watermark) on 14 August, after this report and corpus were frozen. The page identifies Claude's method as a version of SynthID-Text and says the text contains no added or hidden characters. The original null result is therefore compatible with Anthropic's description, but it is not a test of the disclosed statistical method.

Anthropic still has not published its production key, exact configuration, usable detector, decision rule, error rates, reliable-length floor or model-by-model rollout status. Without Anthropic's key, an Anthropic-compatible detector and a published decision rule, this work cannot directly score or exclude the production watermark. The original 12 August findings below are preserved as the point-in-time report; statements that the mechanism itself was undisclosed are superseded by this note. See the dated [announcement note](evidence/sources/anthropic-news-claude-text-watermark-2026-08-15.md) and [Models API documentation check](evidence/sources/models-api-capabilities-2026-08-15.md).

---

## 1. Executive conclusion

Anthropic does officially say Claude watermarks generated text. Its support page, updated 10 August 2026, states that a supported model "weaves an imperceptible watermark directly into the text itself", applied at model level. It names **no exact model identifiers**, defining supported models only by a launch date of 2 August 2026. Every model tested here launched before that date, so under Anthropic's own documentation none is stated to be marking-enabled.

Across 457,045 characters of output from four models, **zero** hidden characters were found: no zero-width, bidi, tag, variation-selector or non-ASCII space characters. A positive control proved the collection path carries such characters when present, so this is a real negative, not a blind pipeline. The only non-ASCII characters were 37 em dashes (36 in dialogue prompts) and legitimate diacritics.

The popular claim is close to backwards. Human public-domain prose carried 20,224 curly quotes; the models produced none.

This rules out a hidden-Unicode watermark in what was tested. It does **not** show Claude has no watermark. Anthropic's later disclosure describes a token-selection watermark that would leave no unusual characters and cannot be detected with this corpus.

---

## 2. Exact models and surfaces tested

### Models

| Slug | Exact model ID | Files | Characters | Launch (first-party) |
| --- | --- | --- | --- | --- |
| `opus5` | `claude-opus-5` | 30 | 125,943 | 24 July 2026 |
| `sonnet5` | `claude-sonnet-5` | 30 | 107,135 | 30 June 2026 |
| `haiku45` | `claude-haiku-4-5-20251001` | 30 | 113,705 | 1 October 2025 |
| `fable5` | `claude-fable-5` | 30 | 110,262 | 9 June 2026 (GA) |
| **Total** | | **120** | **457,045** | all **before** 2 Aug 2026 |

Model identity was set through the Agent tool's `model` parameter and corroborated by each subagent's self-report. Both are assertions, not measurements: no response header or API metadata exposing the served model was reachable. Every cross-model claim inherits this uncertainty.

### Surfaces

**Tested:** Claude Code subagent → tool-call JSON transport → `Write` tool → filesystem. Plus local file write, shell redirection, macOS clipboard (`pbcopy`/`pbpaste`), pseudo-terminal, and JSON transport under both `ensure_ascii` settings.

**Not testable here** (all classified `Test not possible in this environment`): the raw Anthropic HTTP API response body; the official Python or TypeScript SDK; claude.ai web or desktop rendering; the interface Copy button; human selection-and-copy; Bedrock, Vertex AI and Microsoft Foundry; Cowork; temperature, top-p or seed control; token log-probabilities.

No API credential was present. Extracting the host application's stored credentials was deliberately not attempted.

---

## 3. What Anthropic officially confirmed by 12 August

Source: *How Claude marks AI-generated content*, support.claude.com article 16266773, `dateModified` 2026-08-10T19:03:20Z. Archived at `evidence/sources/`.

`Confirmed by Anthropic documentation`:

- **Two techniques, not one.** "Claude uses two complementary techniques": watermarks embedded in text, and C2PA signed provenance metadata attached to files. The file mechanism is named and specific; the text mechanism is not.
- **Text watermark exists as a commitment.** "it weaves an imperceptible watermark directly into the text itself."
- **It survives copying.** "it will travel with the text when it's copied and pasted elsewhere, and may persist through some editing."
- **Model level.** "Watermarking will be applied at the model level."
- **Coverage claimed broadly.** Claude Platform (API), Claude, Claude Code, Claude Cowork and Claude Tag; and via AWS, Google Cloud and Microsoft Foundry; worldwide.
- **Date rule.** "Claude models launched on or after August 2, 2026 support marking at launch."
- **Older models pending.** "Existing models are in progress."
- **Detection is future work.** "We'll share details on detection mechanisms in forthcoming technical documentation."
- **Anthropic's own reliability caveats.** A detected mark "is not fully conclusive", and absence of a mark does not mean text is not AI-generated.

Two defects in the source are worth recording. The page states the date rule twice inconsistently, once unqualified and once scoped "in the EU". And the text-watermark section mixes present tense ("weaves") with future ("will be applied"), so whether marking is live today cannot be read off the page.

---

## 4. What Anthropic had not disclosed by 12 August

`Not supported by evidence` that any of the following is publicly documented:

- **The text mechanism.** Zero first-party mentions, in any watermarking context, of Unicode, invisible or zero-width characters, token probabilities, logit biasing, sampling-time watermarking, lexical or synonym substitution, or SynthID. "Imperceptible" is the strongest mechanism language that exists.
- **Any exact model identifier.** Supported models are defined purely by launch date. No model is named as marking-enabled.
- **Any detector.** No endpoint, no API parameter, no response field, no response header, no partner programme, no waitlist. A sweep of the Messages API reference and every Claude Platform release note from December 2025 to 11 August 2026 found zero occurrences of watermark, provenance, C2PA, marking or Article 50.
- **Operational specifics.** No false-positive rate, no minimum reliable text length, no robustness bounds, no statement of whether marking is live on any current model.
- **Subagents.** Never mentioned on any first-party page.

C2PA is a genuine, named, disclosed mechanism, but it applies to `.svg`, `.png` and `.jpg` files only and is never applied to text. It is file metadata, not a text watermark, and the two must not be conflated.

One inference deserves flagging as an inference. Among Anthropic's reasons a mark may not be detected is: "The passage is very short, leaving too little text for a reliable signal." A length-dependent reliability threshold is characteristic of a statistical or distributional scheme rather than literal inserted characters. This is `Plausible but unverified`. It is read from a limitation statement, not from a disclosure.

---

## 5. Unicode findings

`Confirmed by reproduced experiment`.

Across all 120 model files (457,045 characters), the validated scanner found:

| Category | Model output | Human control | Synthetic control |
| --- | --- | --- | --- |
| Zero-width / invisible | **0** | 0 | 0 |
| Bidi controls and isolates | **0** | **2** | 0 |
| Unicode tag characters | **0** | 0 | 0 |
| Variation selectors | **0** | 0 | 0 |
| Non-ASCII spaces | **0** | 0 | 0 |
| Unexpected control characters | **0** | 0 | 0 |
| Curly quotes | **0** | **20,224** | 0 |
| Em dashes | **37** | 3,055 | 0 |

The 95% Wilson upper bound on the hidden-character rate in model output is **0.0084 per 1,000 characters**. That is the honest form of the zero: not "there are none", but "the rate is below this".

Supporting results:

- **ASCII compliance: 12 of 12.** Every model obeyed the explicit ASCII-only instruction in S07, M07 and L07, producing pure printable ASCII.
- **The em dashes are content-conditioned.** 36 of 37 fall in the quoted-speech prompts and 1 in an informal social post. They mark interrupted dialogue, which is correct usage. A watermark would need to appear across prompt types; this does the opposite.
- **Diacritics behave correctly.** All 12 accented-text samples contain genuine precomposed diacritics, correctly not flagged as anomalies.
- **Normalization is uniform.** All 130 files are NFC with no mixed normalization. Model files are additionally NFKC-stable, LF-only, with no trailing whitespace.
- **The only bidi characters in the entire evidence set are in the human control**, at offsets 7095 and 7098 of *Moby Dick*, wrapping genuine Hebrew text. That is 19th-century typesetting, not marking.

**The direction of the popular claim is inverted by this evidence.** Curly quotes, em dashes and typographic punctuation were overwhelmingly a *human* signal here. Even after controlling for genre by comparing only the dialogue-fiction prompts, every model's typographic rate remained 5 to 22 times *below* the human control.

### The load-bearing methodological check

A zero finding is worthless if the collection path silently strips hidden characters. So a model deliberately emitted them through the exact path used to collect the corpus:

- Zero-width, bidi, Unicode tag, variation-selector, combining and Cyrillic/Greek homoglyph characters **all survived to disk intact**. The tag payload still decodes to its hidden message. Independently verified by Subagent B against recorded hashes.
- **Non-ASCII space variants did not survive.** 0 of 6 arrived; each became U+0020, reproduced across two independent probes.

So the corpus-wide zero is a **real negative for the detectable categories**, and a **blind spot for space-variant marking**. Those are different claims and are kept separate throughout. Since Python-authored NBSP survives the filesystem, clipboard and JSON routes unchanged, the loss occurs specifically at the model-emission-to-`Write`-tool link, not in storage or transport.

---

## 6. Raw API versus interface findings

The decisive comparison, raw API response body against rendered interface output, **could not be run**: `Test not possible in this environment`. This is the single largest gap in the audit.

What was established for the locally accessible routes (`Confirmed by reproduced experiment`):

| Route | Result |
| --- | --- |
| Python binary write | byte-identical |
| Shell redirection | byte-identical |
| macOS clipboard round-trip | byte-identical |
| Python text-mode write | byte-identical |
| JSON transport, `ensure_ascii=False` | byte-identical |
| JSON transport, `ensure_ascii=True` | byte-identical |
| Pseudo-terminal | differs by exactly `ONLCR(source)` |

The terminal difference is fully explained: the tty line discipline translated every LF to CRLF and changed nothing else. Verified by exact reconstruction, and classified by the byte comparator as `line-ending` only.

Two findings matter here. First, **the macOS clipboard preserved zero-width, bidi and tag characters rather than stripping them**, so a hidden-character mark would survive a copy-paste on this platform. Second, no local route *introduced* any Unicode. A fixed ASCII control passed through every route stayed pure ASCII.

What this cannot tell you: whether claude.ai's Markdown renderer, its Copy button, or a raw API response differs. Those layers are untested, and a character appearing only after web rendering would not be model-level output.

---

## 7. Statistical findings

**Headline limitation, stated before any result:** no tokenizer, no log-probabilities, no sampling control and no Anthropic detector exist in this environment. A genuine token-level statistical-watermark test is therefore impossible: `Test not possible in this environment`. Output regularities alone cannot prove a proprietary watermark, because every regularity is equally consistent with ordinary model style.

With that stated, 705 hypothesis tests were run with explicit multiple-comparison accounting (35.25 false positives expected by chance; 29 Bonferroni survivors).

- **No positional or periodic structure.** Across 525 autocorrelation and punctuation-gap spacing tests, **zero** survived Bonferroni correction in any corpus. The human control produced *more* nominal hits than any Claude model under the identical procedure. `Not supported by evidence` that any encoded positional payload is present.
- **N-gram distinctiveness is prompt artefact.** Apparent cross-model n-gram signatures traced almost entirely to shared prompt content, such as identical identifiers in the code and JSON prompts. `Not supported by evidence`.
- **Style differences exist and are not watermarks.** Haiku showed roughly triple the "LLM-ism" lexical marker rate of the other models (23 hits in 15,781 words), and Sonnet wrote measurably longer sentences, present even in the unconfounded short-prompt band. Both are `Observed anomaly, not established as watermark`.
- **The repeat-prompt test is void.** Haiku produced byte-identical text on all three repeat pairs. Because all 30 samples per model were generated in one context in prompt order, the model could simply reproduce its earlier answer. This says nothing about determinism or marking: `Test not possible in this environment`.

---

## 8. Alternative explanations

Every anomaly observed has an ordinary explanation that fits better than marking:

| Observation | Best explanation |
| --- | --- |
| 37 em dashes | Correct punctuation for interrupted dialogue; 36 of 37 in dialogue prompts |
| 6 check marks (haiku only) | Decorative symbols inside `print()` strings in generated test code |
| Diacritics in 12 files | The prompts explicitly demanded correctly accented text |
| CR bytes after terminal route | tty ONLCR line-ending translation |
| 2 bidi controls in human text | 19th-century typesetting wrapping Hebrew in *Moby Dick* |
| Haiku's identical repeats | In-context copying of its own earlier answer |
| Cross-model style differences | Ordinary tier and training differences |
| Curly quotes in human control | Editorial transcription convention |

The folk claim that curly quotes and em dashes indicate AI authorship is **`Not supported by evidence`** and is contradicted in direction by this corpus.

---

## 9. Independent reviewer's objections

Subagent D reviewed the frozen evidence adversarially and raised 43 material points. The substantive ones, which are accepted and incorporated above:

1. **Framing inversion.** Finding that model text is "cleaner" than human text does not support "therefore no watermark uses hidden characters". The human control proves hidden characters *can* survive in text, not that models avoid them. Correct inference runs through the pipeline positive control, not through the human comparison.
2. **The collection surface is one of five.** Only the Claude Code subagent surface was tested. An API response could in principle carry marking in headers or JSON fields that never reach the `Write` tool's disk output. The audit cannot separate "no watermark" from "watermark not visible at this layer".
3. **Self-reported model identity is circular.** Every "all four models" statement rests on models asserting their own identity from their system prompts, with no cryptographic attestation. Confidence in cross-model claims should be downgraded accordingly.
4. **The space-variant blind spot is material.** Absence of space-variant marks is uninterpretable, not negative.
5. **The confounded repeat test should not be presented as a finding**, because the eyecatching "byte-identical repeats" result invites misuse downstream even when caveated.

D's three explicit `Not supported by evidence` verdicts, all of which this report adopts: that Claude definitely does not watermark its text; that all four models behave identically in watermark-relevant metrics; and that Anthropic has confirmed current models watermark their output.

D's bottom line, which is also this report's: the audit shows no obvious watermark is visible. It does not show none exists.

**Caveat on the review itself:** D ran on Haiku 4.5, the least capable tier available, chosen because the brief required a fourth independent model. Its objections are sound but its coverage is likely less exhaustive than a higher tier would have produced.

---

## 10. Limitations and confidence levels

| Conclusion | Classification | Confidence |
| --- | --- | --- |
| Anthropic officially claims a text watermark | `Confirmed by Anthropic documentation` | High |
| The text mechanism is undisclosed | `Not supported by evidence` (that it is disclosed) | High |
| No exact model ID is named as marking-enabled | `Confirmed by Anthropic documentation` | High |
| C2PA applies to files, never to text | `Confirmed by Anthropic documentation` | High |
| No hidden Unicode in 457,045 chars of tested output | `Confirmed by reproduced experiment` | High for tested categories and surface |
| The collection path would have carried hidden characters | `Confirmed by reproduced experiment` | High |
| Space-variant marking | `Test not possible in this environment` | n/a, blind spot |
| No positional or periodic encoded structure | `Not supported by evidence` (that structure exists) | Moderate |
| Typographic punctuation indicates AI authorship | `Not supported by evidence` | High, direction inverted |
| A token-selection watermark | `Test not possible in this environment` | n/a, untestable here |
| Raw API versus rendered interface | `Test not possible in this environment` | n/a |
| Account, locale or region fingerprint | `Test not possible in this environment` | n/a, needs multiple accounts |
| Claude does not watermark its text | `Not supported by evidence` | This was never shown |

Additional limitations: `unicodedata` is Unicode 14.0.0, so code points assigned later scan as unnamed. Sampling parameters were neither settable nor observable. All 30 samples per model came from one context, so later samples are conditioned on earlier ones. The `sonnet5` corpus is not uniform: L01 to L05 came from a nested delegated subagent. The `fable5` L07 sample contains one disclosed post-generation lexical substitution. Human controls are 19th-century fiction and differ from the model corpus in genre, era and editorial convention.

---

## 11. Evidence table

All artefacts are indexed in `evidence/manifest.jsonl`: **177 self-verifying records** (120 model outputs, 10 controls, 18 route artefacts, 29 scanner fixtures). Each record stores the exact UTF-8 bytes as Base64, the decoded text and the SHA-256; the builder re-decodes every record and asserts the hash and text match.

Model corpora, SHA-256 over files concatenated in filename order (first 32 hex chars):

| Sample ID prefix | Model ID | Files | Chars | SHA-256 |
| --- | --- | --- | --- | --- |
| `opus5-*` | `claude-opus-5` | 30 | 125,943 | `3e8479d3811cc5b118619d1545c0cc71` |
| `sonnet5-*` | `claude-sonnet-5` | 30 | 107,135 | `4ac0d039c1e1c0e4313f9197cd2fdfce` |
| `haiku45-*` | `claude-haiku-4-5-20251001` | 30 | 113,705 | `9299cea418215b807d92d3fc075c415e` |
| `fable5-*` | `claude-fable-5` | 30 | 110,262 | `0cc291b320ebafe2fa0bf1f706dd9deb` |

Controls:

| Sample ID | Bytes | SHA-256 |
| --- | --- | --- |
| `control-pg1342_pride_and_prejudice` | 772,386 | `74f2665d6e6925fc2c17dec644bec9e8` |
| `control-pg11_alices_adventures` | 174,311 | `01b38ea4c710a84bc18d0bd41271a5a1` |
| `control-pg2701_moby_dick` | 1,276,263 | `9a6844ac0703853720010787c7b6c70b` |
| `control-pg74_tom_sawyer` | 434,357 | `74d77384b123a6360db9ab58463cff8b` |
| `control-pg84_frankenstein` | 448,885 | `7810cd483cffcf2cc8a1d8f0d5807931` |
| `control-compiler_assembly_output` | 2,532 | `188c70bf9a64d9bd6ca6e3a3329a659d` |
| `control-python_disassembly` | 765,434 | `8bd2c527a3d509d858c03e1d456165e2` |
| `control-random_printable_ascii` | 28,828 | `976ae86712b24ba132fdbea5effda964` |
| `control-random_pseudo_prose_ascii` | 46,403 | `f682f822d97c7c056d5f10c09197c786` |
| `control-handwritten_source_c` | 314 | `9ffc16c3c90417489a0dfd3e5e9c8ad2` |

Key probes and indexes:

| Artefact | SHA-256 |
| --- | --- |
| `evidence/routes/ascii_control__R0_source.txt` | `305749db0cffb5cc2f95e0cd07d5fed7` |
| `evidence/routes/unicode_probe__R0_source.txt` | `ac0d321f8fa0154062585a627cbf91c8` |
| `evidence/routes/pipeline_positive_control__write_tool.txt` | `59adfcaab24625d91815acea2950e9f5` |
| `evidence/routes/pipeline_space_probe__write_tool.txt` | `e596d76d9cd82d52a23b9c01800c9b71` |
| `evidence/prompts.json` | `25ad011d71c28587ba72441f758f09a5` |
| `evidence/manifest.jsonl` | `17abba6a7b7846550725f1d9043a1a41` |

Instrument validation: **29 tests, 0 failures, 0 errors**, recorded in `tests/TEST-OUTPUT.txt` and independently re-run by the orchestrator.

---

## 12. Reproduction instructions

Python 3.11+, macOS or Linux, no third-party packages. From `claude-watermark-audit/`:

```bash
python3 scripts/record_environment.py
python3 scripts/make_controls.py
python3 tests/make_fixtures.py
python3 -m unittest discover -s tests -v
python3 scripts/route_test.py < /dev/null
python3 scripts/scan_unicode.py evidence/raw/corpus/*/*.txt --json > /tmp/scan.json
python3 scripts/analyse_corpus.py
python3 scripts/build_manifest.py
```

Regenerating the corpus needs the Claude Code Agent tool with an authenticated session. The 30 fixed prompts are in `evidence/prompts.json`; generator instructions are recorded in `README.md`. Full detail is in `README.md`.

---

## 13. Direct answers

**Does Anthropic officially say Claude watermarks generated text?**
Yes. `Confirmed by Anthropic documentation`. Its 14 August announcement now identifies a version of SynthID-Text and describes keyed word selection. Whether any particular older model has received the ongoing rollout remains unpublished.

**Which exact tested models support it?**
None that Anthropic documents. Anthropic names no model identifiers at all and defines support purely by a 2 August 2026 launch date. All four tested models launched before it, placing them in the undated "in progress" bucket. `Not supported by evidence` that any tested model is marking-enabled, and equally not established that they are not.

**Is there reproducible evidence that the watermark uses Unicode?**
No. `Not supported by evidence`. No first-party source mentions Unicode in any marking context, and no hidden Unicode was found in 457,045 characters of output.

**Were any hidden or unusual Unicode characters found?**
No hidden characters at all: zero zero-width, bidi, tag, variation-selector or non-ASCII space characters. The only non-ASCII characters were 37 em dashes, 6 check marks inside generated code, and legitimate requested diacritics.

**Did they originate in raw model output or a later presentation layer?**
The em dashes and check marks are genuine model output, reaching disk without passing through a renderer, terminal or clipboard. No local presentation layer introduced any Unicode. The terminal added only carriage returns. The raw-API-versus-web-interface comparison was `Test not possible in this environment`.

**Is there evidence of a statistical watermark instead?**
Anthropic now states that Claude uses a version of SynthID-Text. That is an `official statement`, not a result reproduced by this audit. No positional or periodic structure survived correction, but those tests do not score SynthID-Text. Direct scoring remains `Test not possible in this environment` without Anthropic's key, compatible detector and decision rule.

**Can any tested method reliably attribute arbitrary text to Claude?**
No. `Not supported by evidence`. Nothing measured here attributes text to Claude. Stylistic tendencies are not machine-readable marks and are not reliable attribution. Anthropic itself says a detected mark is "not fully conclusive". Commercial AI detectors were not used and would not constitute evidence.

**What remains unknown after the 14 August disclosure?**
Which exact implementation and key Claude uses; which older models currently carry it; the minimum reliable length; the decision threshold and output scale; false-positive and false-negative rates; the detector's access and privacy terms; and whether behaviour varies by surface or model.

---

## Verdict

Anthropic has now identified Claude's text mark as a version of SynthID-Text and described its operation at a high level. It has not published the production key or exact configuration, named the older models already carrying it, or shipped a public detector.

Against that, the widespread claim that Claude marks text with hidden or unusual Unicode characters does not survive contact with the evidence. In 457,045 characters from four models, through a collection path proven to carry such characters, there were none. The typographic version of the claim is not merely unsupported but points the wrong way: the human control had 20,224 curly quotes and the models had none.

Two things this audit does not establish, and they are the ones most likely to be over-read. It does not show that Claude has no watermark: the most plausible mechanism, given Anthropic's own hint about short passages, is statistical, and no test available here could see it. And it does not speak for surfaces it could not reach, above all the raw API and the web interface.

The honest summary is narrow and firm. **No hidden-Unicode watermark was found where one could have been found. That result is compatible with Anthropic's later SynthID-Text disclosure and cannot test it.**
