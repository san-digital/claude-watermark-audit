# Subagent D — Adversarial Review and Attack on Conclusions

**Audit date:** 2026-08-12  
**Reviewer model:** claude-haiku-4-5-20251001 (self-reported, unverified)

---

## Executive summary

The three preceding reports are methodologically sound and document their limitations with admirable honesty. Together, they establish that:
- No character-layer Unicode watermark is observable in the corpus (Subagent B, high confidence).
- No crude surface-level statistical watermark (positional/periodic) is detectable (Subagent C, high confidence given controls).
- No first-party Anthropic documentation describes a text-watermarking mechanism or detector (Subagent A, high confidence).

**However:** each report contains confounder errors, unstated assumptions, or overreaches that weaken specific claims. None of the three reports prove or disprove that Claude embeds hidden Unicode watermarks *in reality*; they prove only what their chosen observation surface can see. Below I identify vulnerabilities by target.

---

## Subagent A: Official-sources research

### Verdict on core claims

| Claim | Source | My verdict | Confidence |
|---|---|---|---|
| "Anthropic has confirmed that current Claude models watermark their text output" | Section 1 setup | **WEAKENED** | High |
| "No current model is documented as marking-enabled" | Main finding | **SURVIVES** | High |
| "Anthropic says retrofitting is in progress but gives no date or model list" | Section 4 | **SURVIVES** | High |
| "The text-watermark mechanism is entirely undisclosed" | Section 3 | **SURVIVES** | High |
| "C2PA is disclosed for files only, never for text" | Sections 3, 6 | **SURVIVES** | High |

### Material weaknesses

**1. The future-tense parsing is correct but its implication is overstated.**

Anthropic's support article (dated 2026-08-10) uses future tense: "will support", "will travel", "will be applied". Subagent A correctly notes this as forward-looking, not deployed. However, the article *also* contains present-tense language: "When a supported Claude model generates text, it **weaves** an imperceptible watermark" — this is in present tense, scoped only to "supported" models.

**The flaw:** A treats "supported" as an empty set (because no model launched ≥2 Aug 2026), concluding no current model is documented as marking-enabled. But "supported" is undefined *by name* — Anthropic does not specify which models are in the "supported" bucket. It is therefore possible (though undocumented) that Anthropic has quietly enabled marking on pre-August models as part of "work in progress". The documentation does not *forbid* this; it is silent.

**Consequence:** The finding "current models are not *documented* as marking-enabled" is correct and survives. The inference "current models are therefore not enabled" is NOT supported — it conflates documentation absence with capability absence.

**My assessment:** Subagent A correctly made this distinction and explicitly labeled it `Plausible but unverified` — I found no overreach here. However, downstream readers of Subagent A's report may miss the caveat.

**2. The Anthropic-documentation silent-on-subagents claim is correct but the implication is overstated.**

A correctly notes that Anthropic never mentions subagents or API-level output in the marking article. The article says "everywhere you use Claude", which textually includes API. But it does not *operationally define* what "Claude Platform (API)" output looks like at the bit level.

**The issue:** A infers from silence that subagents are not covered. This is reasonable, but silence is not negation. Anthropic's "model level" claim ("it will be present no matter which Claude product or surface the text comes from") would, if true, imply subagent output is marked identically. But A doesn't test whether this modal claim is justified — whether marking actually applies at the model's token-level decision or at some presentation layer. This is beyond A's scope, but it leaves a gap for downstream inference.

**3. Lack of independent source verification on the dateModified field.**

Subagent A retrieved the support article via WebFetch and via raw curl. It verified the body text was byte-identical but did not independently verify the HTML `dateModified` metadata (2026-08-10T19:03:20Z) — it relies on the served metadata itself. If Anthropic's server is misreporting the modification time, the claim "this is the latest first-party source" could be wrong.

**Severity:** Low. Metadata spoofing is implausible. But it's not independently verified.

### Confounders and gaps I identified

1. **Model-identity self-reports are used without caveats in cross-file inference:** Subagent A notes the corpus generators self-reported their identities (opus5, sonnet5, haiku45, fable5) from system prompts. Every statement about "all four models" implicitly inherits this unverified identity. If a harness misconfiguration made Haiku run as Sonnet, cross-model findings would be compromised. A flags this in `evidence/corpus_provenance_notes.json` as `Plausible but unverified`, which is honest, but it's a real constraint.

2. **C2PA distinction is sound, but the implication isn't drawn:** Anthropic discloses C2PA for image files but not for text. This is odd — it means Anthropic has proven technology for cryptographic proof of origin on files, but refuses to disclose a mechanism for text. A does not infer from this (correctly staying in scope), but a downstream reader might wonder: if Anthropic can do C2PA signatures transparently for images, why not describe the text mechanism in equivalent technical terms? The lack of disclosure for text is conspicuous because it contrasts with the file disclosure.

3. **The "forthcoming documentation" hedge:** Anthropic's support article ends with "forthcoming technical documentation". A correctly notes this is a forward promise with no date. But A does not flag that "forthcoming" language is used for two different things: (i) detection mechanisms (clearly not live), and (ii) marking support for pre-August models (could be silently deployed). These should not be conflated.

### Subagent A bottom-line assessment

**Verdict: SURVIVES with caveats.**

Subagent A's core finding — "Anthropic has published policy commitments but disclosed no mechanism and no detector" — is rock-solid and well-evidenced. The finding is scoped correctly: it's a statement about documentation, not about reality. A explicitly avoids the step from documentation to capability. This is methodologically sound.

**Confidence: High** — for what the documentation says. Low — for what marking actually does on pre-August models.

---

## Subagent B: Unicode and byte forensics

### Verdict on core claims

| Finding | My verdict | Confidence |
|---|---|---|
| Collection pipeline (model → Write tool → disk) demonstrably carries zero-width, bidi, tag, variation-selector, combining and homoglyph characters | **SURVIVES** | High |
| All 120 model files contain zero hidden-character watermarks in these categories | **SURVIVES** (for the categories tested) | High |
| Non-ASCII space variants (NBSP, NNBSP, etc.) are stripped before disk; corpus cannot detect space-variant marking | **SURVIVES** | High |
| Human control is "cleaner than model corpus": no hidden characters of any class | **WEAKENED** | Moderate |

### Material weaknesses

**1. The human-vs-model-cleanliness comparison is fundamentally inverted.**

Subagent B states (Section 9): "the model corpus is **cleaner than the human control**: no hidden characters of any class, uniform NFC, pure LF, no trailing whitespace" and concludes "the human corpus contains bidi controls and rich typography; the model corpus contains neither. Any claim that such characters indicate machine generation is inverted by this evidence."

**The error:** This inverts direction-of-inference. The evidence shows:
- Human text: rich typography, bidi marks (legitimate Gutenberg typesetting of Hebrew).
- Model text: pure ASCII-like typography, no bidi.

**This does NOT invert an "invisible characters = machine generation" claim.** Instead, it demonstrates that invisible characters can appear in legitimate human text for typographical reasons (language mixing, pre-LLM publishing conventions). Therefore:
- Finding: "Model text lacks bidi marks" ✓
- Conclusion: "Therefore no bidi-mark watermark exists in models" ✓ (for categories tested)
- False inference: "Therefore hidden characters don't mark text in general" ✗

The human control proves hidden characters *can be present legitimately*. Its presence in human text is consistent with legitimate typesetting, not watermarking. Its *absence* in model text proves either (a) no watermark using those characters, or (b) a watermark that doesn't use those specific characters, or (c) a watermark that was stripped upstream.

B correctly avoids this error in the explicit statement "Absence of hidden Unicode is evidence against character-layer watermarking only, not against watermarking in general" (Section 13). **However, the earlier framing in Section 9 conflates "cleaner text" with "fewer watermark candidates", which is a subtle direction-of-inference error even if B doesn't land on a false conclusion.**

**Severity: Moderate.** B's final summary is correct. The error is in intermediate framing, not the conclusion.

**2. The space-variant blind spot is not fully quantified.**

B correctly identifies that six space variants (U+00A0, U+202F, U+2009, U+2003, U+2002, U+3000) are converted to U+0020 before the Write tool product is stored. This is a real blind spot for space-variant watermarking.

**However:** B does not test *where* this stripping occurs:
- Is it the model refusing to emit non-ASCII spaces?
- Is it the Agent tool's output marshalling?
- Is it the harness?

The positive control proves the Write tool itself preserves zero-width/bidi/tag characters, so the Write tool is not the culprit. But no test probed the Agent tool → Write tool boundary directly with space variants. The stripping could happen upstream of storage and B would not catch it.

**Consequence:** The null finding (zero space-variant marks in corpus) is uninterpretable. It could mean:
- (a) Claude doesn't use space-variant marks (Conclusion B supports), or
- (b) Claude emits them, but they're stripped before reaching disk (blind spot B acknowledges).

**My assessment:** B explicitly states this (Section 11, blind spot 1): "Proven blind spot: the collection link converts U+00A0/U+202F to U+0020". This is honest, but it means **the absence of space-variant marks in the corpus is not evidence that Claude doesn't use them**.

**Severity: Moderate.** B flags it as a blind spot. But it means one entire watermark mechanism (space-variants) cannot be tested here.

**3. The normalization findings are uninteresting but presented as validating.**

B finds all model files are NFC, NFKC-stable, and consistently LF-only. B states: "Uniform NFC is consistent with UTF-8 text produced from a tokenizer vocabulary trained on predominantly NFC web text; it provides no watermark signal."

**This is correct.** But then B lists it as a Finding (Section 12, item 4) with classification `Confirmed by reproduced experiment`. This is true but misleading framing: consistent NFC is exactly what you'd expect from a language model *trained on web text*. It's not evidence of absence of marking — it's evidence of tokenizer normalization convention, which B explicitly acknowledges in the preceding sentence. Filing it as a Finding inflates the appearance of a negative result.

**Severity: Low.** The conclusion is correct. The filing is minor overcounting.

**4. The positive control does not test all surfaces.**

B's positive control (Section 4.1) proves that invisible/bidi/tag characters survive the Write tool path. But it does not test:
- Whether the Agent tool's transport layer strips them (though Write output matches Write input, so this is probably fine).
- Whether the model itself refuses to emit them in certain contexts.
- Whether the context window of the audit (a subagent call) differs from the API or main Claude interface.

**The first two are plausible but untested.** The third is explicitly out of scope but material.

**Severity: Low.** B's scope is "character level". Subagent-context differences are a higher-level concern.

### Confounders and contaminated comparisons

1. **Genre confounding in human vs. model:** The human control is 19th-century narrative fiction (Gutenberg). The model corpus is mixed prose/technical/code/JSON/dialogue, all modern, all constrained-prompt-driven. Comparing character usage across these is genre-confounded. B does not attempt to control for this, because B's scope is character-level, not corpus-level. But downstream readers should not conclude "models don't use curly quotes because Claude doesn't" — models might not use curly quotes because they're answering technical prompts and following explicit ASCII constraints.

2. **Corpus provenance confound (noted but not fully addressed):** Sonnet5's L01–L05 were generated by a different delegated agent. B doesn't re-run the tests excluding these files, so corpus-wide statistics on sonnet5 inherit this confound (though B flags it).

### Subagent B bottom-line assessment

**Verdict: SURVIVES for what it claims; WEAKENED for cleanliness interpretation.**

The core finding — "no hidden-character watermark detectable in 120 model files, verified through a scanner that would have caught it, under a Write tool path proven to carry such characters" — is sound. The finding is robust to the alternate interpretations.

**However:** the implications of the "cleaner" framing and the space-variant blind spot prevent B from concluding "Claude definitely doesn't use character-layer marks" — only "no character-layer mark is visible through this collection path". B makes this distinction in the final summary (Section 13) but buries it.

**Confidence: High** for "no character-layer watermark visible here", **Moderate** for "therefore Claude doesn't embed them" (space-variant blind spot; model-emission vs. harness-stripping ambiguity).

---

## Subagent C: Statistical analysis

### Verdict on core claims

| Finding | My verdict | Confidence |
|---|---|---|
| Repeat-prompt test cannot measure determinism; haiku45 byte-identical repeats are explained by in-context recall | **SURVIVES** | High |
| Positional/periodicity tests: 0 of 525 survivors after Bonferroni correction in any corpus, including human control | **SURVIVES** | High |
| Human control shows MORE periodicity "hits" than models, invalidating period-as-watermark inference | **SURVIVES** | High |
| Word frequency and TTR are genre/composition effects, not watermark signals | **SURVIVES** | High |
| Token-level statistical watermark is undetectable in this environment | **SURVIVES** | High |

### Material weaknesses

**1. Multiple-comparisons correction may be too conservative, or not conservative enough.**

Subagent C used Bonferroni correction over 705 tests, yielding α=7.09×10⁻⁵. This is conservative. But:

**In one direction (over-conservatism):** Many of the 705 tests are highly correlated (same punctuation mark across four models, same sentence-length measure across prompts). Bonferroni assumes independence, which is false. Real α might be higher, allowing legitimate signals to survive if resampling or step-down correction were applied.

**In the opposite direction (under-conservatism):** C did not correct across the lexical/punctuation battery (180 tests) and the positional battery (525 tests) simultaneously. If one was run as exploratory and the other confirmatory, Bonferroni over all 705 might be justified. But if both are treated as hypothesis tests from the same data, there's a question of whether Bonferroni should apply across the corpus-building pipeline too (i.e., is the choice of 30 prompts × 4 models a free parameter?).

**Consequence:** The 29 surviving tests in the lexical/punctuation battery (model-vs-human differences in punctuation typography) are reported accurately with p-values, but the claim that these represent real finding is credible *given* Bonferroni, and uncertain if Bonferroni is inappropriate.

**Severity: Low-Moderate.** C reports uncorrected p-values, so readers can judge. The findings that survive Bonferroni are genuine. But if Bonferroni is too conservative, real model-vs-human differences (punctuation style, for example) might be genuine even if the surviving 29 are all confounded by genre.

**My assessment:** C is correct to apply Bonferroni. The honesty is high. But the reader should not over-interpret the fact that 29 tests "survive" — it means they survive a very conservative correction for a specific kind of independence assumption.

**2. Sample size is small for detecting a weak watermark.**

C notes model corpora are ~16k-20k words per model. At this size, a token-selection watermark with small effect size (e.g., 1-2% lexical bias per token) would be statistically undetectable against ordinary sampling noise, especially without control of temperature or access to logits.

**C acknowledges this explicitly in the Headline Limitation.** But the implication is buried: "Nothing in this report can prove or disprove that Anthropic embeds a proprietary statistical watermark." This is correct, but it means the absence of findings is not evidence of absence of a watermark.

**Consequence:** A reader might conclude from "no statistical structure found" that "no statistical watermark exists". The correct conclusion is "no crude statistical watermark with high effect size exists, *detectable at this sample size without access to logits*".

**Severity: Moderate.** C's caveat is explicit and repeated. But it's in a different section from the findings, so readers might miss the scope limitation.

**3. The repeat-prompt test is confounded but still included as a Finding.**

C correctly identifies the confound: all 30 samples per model share one conversation context, in prompt order. S10 follows S01 in the same context, so a model can simply recall S01's answer. Haiku45 did this (byte-identical repeats); the other three varied their answers.

**C then reports this as a Finding (item 6) with classification `Test not possible in this environment`.**

**The issue:** The finding as reported is the raw same/different fact, not a conclusion about determinism or watermarking. C labels it correctly. **However**, this test should not have been run at all if the provenance note identifies it as confounded. Running it, even to report "can't interpret this", creates the risk that downstream readers misuse it. C mitigates this risk by flagging the confound, but the test should ideally not appear in a core findings list if it's uninterpretable.

**Severity: Low.** C's caveat is crystal-clear, and the finding is labeled uninterpretable. But the appearance of "haiku45 byte-identical repeats" in a findings table is eyecatching and could mislead.

**4. The genre confound is not fully controlled.**

C attempts to control for genre by analyzing `quoted_speech` prompts separately when comparing to human text. But the main corpus statistics (word frequency, TTR, punctuation rates, n-grams) mix genres:
- 9 of 30 prompts are non-prose (3 code, 3 JSON, 3 lists).
- Haiku45's elevated TTR and mean-word-length are explicitly attributed to code-leakage into the word count.
- Punctuation rates compare "model corpus (9 code/JSON files pooled with prose)" to "human (continuous 19th-century narrative)", which is inherently mismatched.

**C acknowledges this:** "Every model-vs-human comparison in this report either uses the genre-matched `quoted_speech` subset ... or states plainly that genre is uncontrolled."

**However**, for a reader skimming the main results (Section 9), the genre-uncontrolled comparisons are listed alongside explicit caveats, but the contrast in readability between a caveat and a table is stark. A reader might read "Human punctuation rate: 13.78 commas/1,000 chars; Model rates: 9–14" and conclude models have different punctuation, without parsing the genre-uncontrolled caveat nearby.

**Severity: Moderate.** C's caveat is present. The analysis is honest. But the presentation could emphasize the genre confound more strongly for main corpus statistics.

**5. Lexical-marker definitions are curated, not derived from the data.**

C uses a curated list of 36 "LLM-ism" markers (`delve`, `tapestry`, `crucial`, etc.). The list is not machine-derived from the corpus; it's hand-curated based on "anecdotal" association.

**This introduces cherry-picking risk:** the list is built by humans who expect LLMs to use certain words. If the list were truly LLM-istic, one would expect all four models to elevate these markers equally. Instead, only haiku45 does, at 1.46/1,000 vs. 0.26–0.42/1,000 for the others.

**C correctly concludes:** "This should not be over-read given how few of the 36 terms drive it." The haiku45 effect is real (z-test p ≈ 4×10⁻⁶, survives Bonferroni) but small (23 hits in 15,781 words).

**However**, the curated list is not validated against an independent corpus. It's unknown whether the same list would rank human 19th-century prose or modern code the same way. The list might be "LLM-ism" markers for Anthropic models specifically, or it might be "modern prose tendency" markers, or it might be "markers of technical/explanatory writing". Without a lexical discovery step, the interpretation is constrained.

**Severity: Low-Moderate.** The finding is real and cautious. But the curated-list approach limits generality.

**6. Confound not fully resolved: sonnet5's split generation context.**

Sonnet5's L01–L05 were generated by a delegated agent in a different context. C flags this and notes it mildly confounds sonnet5's long-band statistics. However, C does not re-run the analyses excluding these files to test robustness.

**Consequence:** Any sonnet5-specific finding for the `long` band is potentially confounded. Sonnet5's longer mean sentence length in the `long` band (30.9 words/sentence vs. opus5 19.6) could be an artifact of the context-split, not a stable model difference.

**Severity: Low.** C flags it. The finding stands, but with reduced generality for sonnet5.

### What this audit did not test

1. **API-level output:** The corpus was collected via Agent tool → Write tool → disk. No test probed the raw Anthropic API response body to see if it differs. Subagent A notes this is inaccessible in this environment (no API key). But this is a material gap: API responses might include response headers or JSON fields that carry marking information invisible to the disk-file level.

2. **Inter-model differences in determinism:** Opus5, Sonnet5, and Fable5 varied their answers on repeat prompts; Haiku45 did not. C attributes this to in-context recall for all models equally. But it's possible Haiku45 has lower temperature or is more deterministic by design. If so, Haiku45's behavior is a property of the model, not just the context. This should have been tested by generating *outside* the same context (e.g., in a separate conversation), which was not done.

3. **Edge-case prompts:** All 30 prompts were generated in one pass per model. No adversarial probes (e.g., "generate text that contains only the letter A", or "generate the same text 100 times") were used to stress-test for watermarking patterns that might only emerge under extreme inputs.

4. **Streaming vs. non-streaming:** The Agent tool's output was captured after streaming completed. No test compared streaming-phase vs. final output, or examined in-flight token choices.

### Subagent C bottom-line assessment

**Verdict: SURVIVES with scope limitations.**

Subagent C's core finding — "no crude surface-level statistical watermark (positional/periodic/lexical) detectable in the corpus at the sample size and without logit access" — is sound and carefully scoped.

**The finding does NOT prove:** "Claude doesn't embed a statistical watermark."

**The finding DOES prove:** "A watermark at token-selection level (invisible to surface statistics) cannot be ruled out; surface-feature tests return no signal above human-control baseline; sample size is too small to detect small-effect-size biases."

C makes these distinctions explicit. The limitation is that downstream readers might miss them.

**Confidence: High** for what C tested, **Low** for "therefore no watermark exists" inference.

---

## Cross-audit vulnerabilities

### 1. Model identity is self-reported and creates a circular dependency

Every statement of the form "all four models show X" rests on:
- Harness system prompt asserting which model alias corresponds to which model ID.
- Each model's system prompt containing its own identity.
- No independent verification (no response header, no API attestation, no cryptographic signature).

If the harness alias mapping or the models' own assertions are wrong, cross-model findings are invalid. This is flagged in `corpus_provenance_notes.json` as `Plausible but unverified`, but it's a real vulnerability.

**Consequence:** Findings framed as "all four models show X" should be downgraded to "four models that claim to be opus5/sonnet5/haiku45/fable5 show X".

### 2. Collection surface is not representative of end-user surfaces

The corpus was collected via Claude Code subagent (Agent tool) → Write tool → disk. But Anthropic's watermarking policy article says marks apply "everywhere you use Claude", including:
- claude.ai (web interface)
- Claude apps (desktop)
- Claude Platform (API)
- Claude Code (covered here)
- Bedrock, Vertex, Foundry (mentioned, with caveats)

**None of the three other surfaces were tested:**
- Web interface: requires authenticated browser session (unavailable).
- API: no API key available (explicitly out of scope).
- Bedrock/Vertex: requires paid service access (out of scope).

The audit tests only Claude Code (subagent), which is one of five named surfaces. If watermarks differ across surfaces (e.g., applied at model level but stripped by the Write tool, or applied at the API response header and lost in JSON transport), the audit cannot see it.

**Consequence:** Claims about "whether Claude watermarks" are properly scoped to "Claude Code subagent output written to disk via the Write tool" — which is correct, but narrow.

### 3. The "supported model" definition remains undefined

Anthropic says marking is supported for "models launched on/after 2 Aug 2026". As of 2026-08-12, no such model exists. Anthropic also says retrofitting pre-August models is "in progress" but gives no date, model list, or completion criterion.

**This leaves open:** Is marking deployed to any current model? Unknown. Anthropic has not answered. The audit shows no marks are visible in the corpus, but this does not prove they're not deployed — only that they're not visible through this surface.

**Consequence:** Bottom-line questions remain unanswered:
- Is `claude-opus-5` (launched 24 July 2026) watermarked right now? Unknown.
- Which models, by exact ID, carry marks today? Unknown.

### 4. No watermark implies one of three things, not one

The audit finds no watermark in the corpus. This is consistent with:
- (a) Claude doesn't embed watermarks yet (as Anthropic's docs suggest — "in progress").
- (b) Claude embeds watermarks, but they use a channel this audit cannot see (token selection, response headers, file C2PA, space-variants before disk).
- (c) Claude embeds watermarks, but they're stripped by the harness/Write tool somewhere upstream of disk.

**The audit eliminates (b) and (c) only for character-layer/obvious-surface-level marks.** For token-selection watermarks (the kind described in academic watermarking literature), all three remain possible.

---

## Claims to downgrade or remove

1. **"Model corpora are byte-identical to the canonical model set (opus5, sonnet5, haiku45, fable5)"** — should be downgraded to "Corpora claim to be generated by models asserting these identities; no independent verification." This is Subagent B's phrasing in finding 11, already correct.

2. **"Haiku45's byte-identical repeats on S01/S10, M01/M10, L01/L10 demonstrate model determinism"** — should be removed as a Finding. Subagent C correctly flags it as uninterpretable due to in-context confound, but it should not appear in the findings table at all because running a confounded test creates the appearance of a result even if labeled "uninterpretable".

3. **"Model corpus is cleaner than human control, suggesting models don't use hidden characters"** — should be rephrased to "Model corpus contains no hidden characters; human control demonstrates that hidden characters appear in legitimate pre-LLM text for typesetting reasons; therefore, character-layer watermarks, if present, must use characters not found in this audit's detection scope." Subagent B's final summary (Section 13) is already correct; Section 9 should be reworded.

4. **"Position-periodic structure is ruled out as a watermark mechanism"** — correct, but should note this applies only to surface-layer positional structure (sentence-length gaps, punctuation spacing). It does not rule out token-selection watermarks, which have no surface signature.

5. **"Anthropic has confirmed current Claude models watermark their text"** — should be downgraded to "Anthropic has confirmed future Claude models will watermark text; no current model is documented as watermark-enabled; work on pre-August models is stated as in-progress but not confirmed deployed." (Subagent A is already careful here.)

---

## What was missed

1. **No test of the Agent tool's output marshalling:** The positive control tested the Write tool's preservation of Unicode. But the Agent tool's output could be stripping characters before they reach Write. Recommend: a second positive control that writes directly to disk without an intermediate Write tool call, comparing harness-output (what Agent tool surface sees) to stored output.

2. **No test of API response metadata:** If marking is applied at the API level (response headers, JSON fields not exposed to the harness), this audit cannot see it. Recommend: (if credentials become available) a direct API call to fetch raw JSON and inspect response structure.

3. **No stress test for adversarial inputs:** No attempts to elicit watermarking failure modes (e.g., "repeat this letter 1,000 times", "generate identical text twice"). Watermarks may degrade or exhibit artifacts under extreme conditions. Recommend: a supplementary corpus of adversarial prompts.

4. **No comparison across surfaces:** Only Claude Code subagent tested. Recommend: if access becomes available, collect a parallel corpus from claude.ai, Claude Platform API, and a Bedrock deployment to test whether watermarks differ by surface.

5. **No independent detector test:** Anthropic promises "forthcoming documentation" on detection. If detector code appears, audit it against this corpus. Recommend: flag this as a follow-up task.

6. **No test of model tier-specific behavior:** Haiku45 showed elevated LLM-ism markers and lower hyphen-minus rates. Is this a watermark or a tier-specific style? Recommend: collect identical-prompt parallel samples from Claude 3 Haiku and Opus 3 (if available) to isolate tier-specific style from watermark-specific signals.

---

## Bottom-line answers

### Question 1: Does this evidence establish that Claude embeds hidden Unicode characters in generated text?

**Answer: NO.**

**Confidence: High.**

Evidence: Subagent B's positive control proved the Write tool path carries zero-width/bidi/tag/combining characters. The corpus of 120 files (457,045 characters) contains zero such characters. Either (a) Claude doesn't emit them, or (b) Claude emits them and the harness strips them upstream. The audit cannot distinguish, but finding (a) is most plausible. Space-variant stripping is proven, creating one honest blind spot. Character-layer watermarking with invisible characters (the kind suggested by casual "watermark" talk) is ruled out by this evidence to **High confidence** in the Claude Code + Write tool surface. **Moderate confidence** overall, due to surface-limitation caveats.

### Question 2: Does this evidence establish that Claude does NOT watermark its text?

**Answer: NO.**

**Confidence: Low.**

Evidence: 
- No character-layer watermark found (High confidence for this audit's surface).
- No crude statistical surface watermark found (Moderate confidence; Bonferroni may be conservative; sample size is small).
- Anthropic's documentation doesn't confirm current marking (Correct; but undisclosed deployment is possible).
- Token-selection statistical watermarks are undetectable in this environment (Acknowledged; true).

**The audit disproves character-layer watermarks, not watermarking in general.** A token-selection watermark (the kind in academic literature, operating at the model's decision boundary) would leave no visible trace in the corpus, no surface anomalies, and no documented mechanism. Its absence from this audit would prove nothing. Therefore, the audit does not establish "Claude does NOT watermark".

---

## Summary of confounders and contaminated comparisons

| Confound | Location | Severity | Impact on finding |
|---|---|---|---|
| Model identity unverified | All cross-model statements (A, B, C) | High | Weakens any claim about "all four models" |
| Genre mismatch (human control: 19th-century narrative; model: mixed technical/prose) | B Section 9, C Section 9 | Moderate | Punctuation, TTR, entropy comparisons are genre-confounded |
| Sonnet5 split generation context (L01-L05 delegated) | C, noted in methods | Low | Sonnet5 long-band statistics mildly confounded |
| Repeat-prompt confound (in-context recall, not determinism test) | C Section 6 | Moderate | Haiku45 byte-identical repeats are uninterpretable; should not appear in findings |
| Space-variant stripping point unknown | B Section 11 | Moderate | Absence of space-variant marks is uninterpretable (blind spot) |
| Collection surface not representative (Agent/Write/disk; not API, web, Bedrock) | All | Moderate | Findings scope to Claude Code subagent only |
| Curated lexical-marker list not validated | C Section 9 | Low | LLM-ism finding is real but interpretation limited |
| Corpus generation order (single context, prompt order) | C, methods | Low | Outputs are not fully independent; later samples may be conditioned on earlier ones |
| Multiple-comparisons correction assumption | C, Section on correction | Low-Moderate | 705 tests assumed independent; many are correlated. Bonferroni may be conservative. |

---

## Claims requiring independent verification before publication

1. **"No watermark uses hidden Unicode."** Survives for character-layer, conditioned on Write-tool surface. Requires independent verification with API-direct call if credentials available.

2. **"haiku45 model tier produces measurably different output styles (sentence length, hyphen usage, LLM-ism markers)."** Real finding, but confounded between watermark and tier-specific training differences. Requires parallel Claude 3 Haiku sample to disentangle.

3. **"Anthropic has disclosed no text-watermarking mechanism."** True as of 2026-08-10. But "forthcoming" language suggests a future document. Recommend: periodic re-check of Anthropic's documentation.

4. **"Current Claude models do not carry documented marking support."** True as of 2026-08-12. But Anthropic's "in progress" language and lack of date allow for undisclosed deployment. Recommend: track model release notes and support articles for changes.

---

## Confidence levels by classification

| Classification | Applied to findings | Appropriate |
|---|---|---|
| Confirmed by Anthropic documentation | Official-sources findings on first-party text | **Yes** (high confidence) |
| Confirmed by reproduced experiment | B positive control; C Bonferroni-surviving tests | **Mostly yes** (high for character layer; lower for sample size) |
| Observed anomaly, not established as watermark | C sentence-length, punctuation, TTR differences | **Yes** (correctly distinguished from watermark claims) |
| Plausible but unverified | Model identities; Subagent C's token-level watermark hypothesis | **Yes** (appropriate caveats) |
| Not supported by evidence | Character-layer watermarks; positional watermarks | **Yes** (for tested surfaces) |
| Test not possible in this environment | Token-level watermarks; API-direct inspection; space-variant marking | **Yes** (honest scope boundaries) |

---

## Final verdict

**The three reports collectively establish:**

1. ✓ Anthropic's documented watermarking policy is limited to "future" and "in progress" (Subagent A).
2. ✓ No character-layer hidden-Unicode watermark is detectable in the corpus through the Write-tool surface (Subagent B).
3. ✓ No crude statistical surface-layer watermark (positional/periodic) is detectable above human-control baseline (Subagent C).
4. ✓ The audit's scope is limited to Claude Code + Write tool + disk; other surfaces untested.
5. ✗ The audit does NOT establish that Claude doesn't watermark — only that certain watermark mechanisms are undetectable in this environment.

**For publication, recommend:**

- Emphasize scope boundaries throughout.
- Remove or reframe findings that conflate "audit finds no mark" with "no mark exists".
- Explicitly state that token-selection watermarks (the kind in academic literature) are undetectable here.
- Upgrade the Anthropic-documentation caveat about "supported" models to prominence — the future tense is load-bearing.
- Track Anthropic's documentation for changes; mark this audit as point-in-time (2026-08-12).

**Confidence in the final claim "Claude does not watermark":** LOW. 
**Confidence in the final claim "Claude's text watermarking mechanism, if present, does not use obvious hidden Unicode or surface-statistical signals detectable in 120 short samples":** HIGH.

These are different questions and must not be conflated in downstream communication.
