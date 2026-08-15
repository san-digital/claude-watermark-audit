# Claude Models API documentation: marking-status field check

- Source: https://platform.claude.com/docs/en/api/models/list
- Checked: 15 August 2026
- Method: inspected the public API reference; no authenticated `GET /v1/models`
  response was captured
- Evidence class: reproduced observation of mutable documentation

The documented `ModelCapabilities` schema listed nine capability groups: batch,
citations, code execution, context management, effort, image input, PDF input,
structured outputs and thinking. The model record also documented `created_at`.

The public documentation checked on 15 August did not document a marking or
provenance capability. This is a statement about the published schema only. It does
not establish that watermarking is disabled, that the schema is exhaustive, or that
Anthropic would use this object to disclose marking status.

The public API overview and reference checked at the same time did not expose a
watermark-detection endpoint. Anthropic's 14 August announcement says an API is
coming soon; a private or unpublished interface cannot be assessed here.

