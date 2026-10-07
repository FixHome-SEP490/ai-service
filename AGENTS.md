# FixHome AI Service — Agent Instructions

This FastAPI service is an independent Git repository. AI output is advisory and untrusted.

## Repository context (read first, keep current)

`docs/CONTEXT.md` is the living context of this repository: what it owns, how it links to the other
FixHome repositories, the current state, contracts, settled PO decisions and open risks. Read it
before `docs/AI-TECHNICAL-GUIDE.md` and before touching code.

Any change that alters behaviour, an API or event contract, an enum, an environment variable, a
migration, how the project runs or is verified, or a PO decision must update `docs/CONTEXT.md` in
the same pull request, following its section 0 exactly: real Vietnam time (UTC+7), the exact
`git config user.name`, the branch, and a new top line in section 9. `tests/test_context_doc.py` enforces the
format in the normal test run and in CI; never weaken that test to make a change pass. The
repository is public: never write secrets, credentials, IP addresses or customer data into it.

## Mandatory pre-implementation gate

Before every task, read FIXHOME-DESIGN-SYSTEM.md completely together with
docs/AI-TECHNICAL-GUIDE.md. Follow its cross-platform language, terminology,
design-token, typography, title, component, status, and verification rules.
For UI or user-facing output changes, inspect the matching Web/Mobile behavior.
Preserve this repository's architecture, API contracts, permissions, and tests.
If cross-repository verification is unavailable, explicitly report NOT VERIFIED.

Before doing any task:

0. Read `docs/CONTEXT.md` completely.
1. Read `docs/AI-TECHNICAL-GUIDE.md` and `FIXHOME-DESIGN-SYSTEM.md` completely.
2. Inspect the existing project structure and affected endpoint, schema, or provider adapter.
3. Understand the current router → endpoint → provider → pipeline (detector, retriever, VLM,
   knowledge base) architecture.
4. Identify existing Python, Pydantic, async, error, and test conventions.
5. Check requirements, environment configuration, and relevant dependencies.
6. Search for an existing provider/schema implementation before creating code.
7. Do not modify unrelated files.
8. Do not restructure the project unless explicitly requested.
9. Preserve Backend-facing schemas, fallback behavior, confidence rules, and disclaimers.
10. After implementation, execute the complete review process in the technical guide.

If the technical guide has not been read, implementation must not begin.

## Repository rules

- Preserve `AIProvider`; engine-specific work stays behind adapters. The service is self-hosted
  (YOLO11s detector-v2 plus Qwen2.5-VL served by vLLM); hosted Gemini/OpenAI adapters were removed and must not be
  reintroduced without a documented decision.
- Vietnamese wording, service codes, prices and urgency come from `app/data/`, never from model free
  text. A code the model returns that is absent from the catalog must be dropped, not surfaced.
- Diagnosis and the advisory chatbot stay separate surfaces. Any service either surface recommends
  must come from the `app/data` service mapping, never from model free text.
- AI must never authorize transactions, assign technicians, approve quotations, or change orders.
- Treat user prompts, image references, and provider responses as untrusted input/data.
- Preserve timeout/failure fallback so AI outages never block manual booking.
- Do not expose provider errors, prompts, keys, or sensitive data in responses or logs.
- Coordinate schema changes with `backend` and both clients, update `docs/CONTEXT.md` in every
  affected repository, and document them in the `docs` repository.

## Required verification

Run `ruff check app tests`, `pytest`, `python -m compileall -q app tests`, an application import
check, and a health/startup check. Review `git diff`; report unavailable live-provider checks as
`NOT VERIFIED`.
