# Tool inventory — when to embed which platform tool in a template

John ships a small set of **platform tools** — utilities that live at workspace level (not inside the plugin) and serve any template that needs them. Templates *use* these tools; templates do *not* ship them. If a template needs a tool the platform doesn't have, the right move is to surface the gap to the user (who decides whether to add it to the platform), not to bundle the tool inside the template.

## Current platform tools (as of John v0.2.0)

### `local_clients/llm/` — workerLLM client

A FastAPI server wrapping SiliconFlow + DeepSeek (today; the URL contract is provider-agnostic so any compatible production server can be swapped in later).

- **Plugin-side caller**: `$JOHN_LLM_CLIENT_URL` env var (default `http://localhost:8500`). The plugin's `workerllm-runtime` skill teaches layer-3 Claude how to call this.
- **API contract** (live): see `$JOHARNESSBURG_PATH/../local_clients/llm/README.md` if the workspace is laid out as you expect, or browse `https://github.com/kitchen-engineer42/joharnessburg` issues/docs for the canonical contract.
- **Endpoints**: `GET /healthz` (returns providers inventory), `POST /v1/chat/completions` (OpenAI-compatible).
- **When to embed in a template**: when produced apps need to call workerLLMs at runtime — for in-app inference, per-request classification, formatting, agentic flows. The `workerllm-runtime` skill is the integration point; templates rarely need to override it, only customize the prompts/models.
- **When NOT to embed**: when the produced app is a static knowledge bundle (e.g., a slide-deck builder where all the LLM work happens during the build, not at app runtime). In that case the workerLLM is used during the BUILD phase by layer-3 Claude, but the produced app doesn't need to keep calling it.

### `local_clients/ppx/` — PDF parser client

A FastAPI server wrapping `memect-ppx` (the `ppx` engine).

- **Plugin-side caller**: `$JOHN_PPX_CLIENT_URL` env var (default `http://localhost:8501`). The plugin's `parsing` skill + `scripts/ppx_parse.py` are the integration points.
- **API contract** (live): see `local_clients/ppx/README.md` in the workspace.
- **Endpoints**: `GET /healthz`, `POST /parse` (input_path, output_dir, backend, ocr, table — Pydantic-validated literals).
- **When to embed in a template**: when produced apps (or the John build phase) need to parse PDFs — especially those with OCR, complex tables, or formula content. The parser is heavyweight; only reach for it when markitdown can't handle the format.
- **When NOT to embed**: for non-PDF inputs (markdown, HTML, plaintext, DOCX), the `parsing` skill routes to `markitdown_parse.py` or `parse_govcn_html.py` instead. Don't force ppx where it adds latency without benefit.

## The platform-vs-template boundary

John's design treats tools as **platform infrastructure**, not template content. The reasons:

- **Tools are heavy.** A parser, an LLM client, an ASR pipeline — these are real services. Shipping a copy inside every template would bloat the platform and prevent shared upgrades.
- **Operability** — when ppx gets a critical fix, the team rolls it out once at workspace level, and every template benefits.
- **Substitutability** — the URL-env-var contract means implementations can be swapped (e.g., on-prem PPX server, different LLM provider) without any template changing.

So: if a template needs a tool that's already in the platform, embed its usage (via the appropriate skill — `parsing`, `workerllm-runtime`, etc.). If a template needs a tool that's NOT in the platform, you don't bundle it. You surface the gap.

## When the platform is missing a tool you need

You'll spot patterns where the inputs hint at a tool the platform doesn't have:

- "Recordings need to be transcribed" → no ASR tool. (Hamster assumes inputs are pre-transcribed; users handle ASR upstream.)
- "Need to call a domain-specific API mid-app-runtime" → no domain-API wrapper.
- "Need to render LaTeX/OMML formulas faithfully" → not in scope; ppx handles structured doc parsing but formulas are tricky.

When you spot a pervasive need across the template's design, surface it to the user:

> "I see this template's design will require <X tool>. The platform doesn't currently provide that. Options: (1) I generalize the template's input contract to assume <X> is done upstream (the user handles it manually per app). (2) You add <X> to the platform — workspace-level, following the `local-clients-builder` methodology. (3) You skip this design direction. Which?"

Don't decide for the user. They know the platform roadmap.

## When a tool the user provides replaces a platform tool

Sometimes the user says: "We have our own internal parsing service that handles formula-rich PDFs better than ppx. Use that instead." In that case:

- **The replacement tool stays at platform level** — the user adds it (or has added it) to `local_clients/` following the same methodology.
- **The template uses URL env vars** (e.g., `$JOHN_PARSER_URL` or `$JOHN_PPX_CLIENT_URL` if it's drop-in compatible) — no template-side code change.
- **The template's `parsing` skill (or override) documents that the produced apps assume a parser at the standard URL** — leaving room for the team to deploy any compatible service.

This keeps the template portable. A template that hardcodes "use our specific internal service" would be brittle; a template that says "use whatever parser is at `$JOHN_PPX_CLIENT_URL`" survives provider changes.

## When this rots

The tool list above is pinned to John v0.2.0. The platform may grow. To re-check:

1. `ls $JOHARNESSBURG_PATH/../local_clients/` — see what clients exist locally.
2. Check joharnessburg/PLAN.md for "out of scope" → those tools haven't landed yet.
3. Read the latest `using-john` skill — it points to current tool integrations.

If a new tool has landed, propose to the user that Hamster's `tool_inventory.md` be refreshed.
