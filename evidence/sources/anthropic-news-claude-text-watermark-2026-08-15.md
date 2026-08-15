# Anthropic technical announcement: Claude text watermark

- Source: https://www.anthropic.com/news/claude-text-watermark
- Published by Anthropic: 14 August 2026
- Checked: 15 August 2026
- Evidence class: official statement; the technical and performance claims below were not independently reproduced
- Review status: mutable first-party page

## What the page now states

Anthropic identifies Claude's text watermark as a version of SynthID-Text. It
describes a keyed sampling process in which a few preceding words help alter the
random choice among suitable next words. It says the process adds no characters or
tokens to the text.

Anthropic also states that:

- confidence generally increases with the amount of Claude-written text;
- factual passages, exact output, code and light corrections may offer few eligible
  word choices;
- a translation produced by Claude carries the mark because Claude chooses its
  words;
- light editing probably leaves some mark, while replacing every word removes it;
- the mark and its key contain no user, organisation or conversation identifier;
- the process adds no tokens or price and has negligible speed and quality effects;
- a detection API is planned "soon";
- older-model rollout will continue over the coming months; and
- the worldwide rollout reflects Anthropic's stated inability to maintain durable
  regional scoping.

These are Anthropic's statements. This repository did not reproduce its internal
quality, performance, privacy, robustness or detection testing.

## What remains unpublished

As checked on 15 August, the page did not provide a production key, exact SynthID
configuration, usable detector, decision threshold, output scale, false-positive or
false-negative results, reliable-length floor, or a model-by-model rollout status.
No public source reviewed here identifies which older model IDs have received the
ongoing rollout.

Without Anthropic's key, an Anthropic-compatible detector and a published decision
rule, this audit cannot directly score or exclude Anthropic's statistical watermark.

## Relationship to the 12 August corpus

The announcement's no-hidden-characters statement is compatible with the original
Unicode result. It does not turn that result into a SynthID-Text test. The four
sampled model IDs pre-date 2 August, but Anthropic says older models are being
updated; their current marking status is therefore unknown.

