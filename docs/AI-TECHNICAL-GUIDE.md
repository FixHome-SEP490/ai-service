# AI-FixHome AI Technical Guide

This document governs every human and AI change in the independent FastAPI service. The service is
advisory: probabilistic output is never an authoritative FixHome business decision.

## 1. Repository Purpose

AI-FixHome owns the preliminary home-repair diagnosis API, the grounded advisory chatbot, the
Pydantic request/response contract, confidence/clarification behavior, the self-hosted inference
pipeline, the curated knowledge base, the mock engine, and safe fallback signaling consumed by
Backend-FixHome.

It does not authenticate FixHome users, authorize actions, assign technicians, approve quotations,
write the FixHome database, or transition Service Orders. Backend-FixHome owns those responsibilities.
Frontend and Mobile must call providers only through Backend/the approved AI service flow.

## 2. Technology Stack

- Python 3.11, pinned by `.python-version`
- FastAPI 0.115 and Uvicorn 0.32
- Pydantic 2 and pydantic-settings 2
- HTTPX for outbound calls to the model server
- YOLOv8n via Ultralytics for device detection, Qwen2.5-VL-3B-Instruct AWQ served by vLLM
- Pillow for image handling
- python-dotenv and multipart support
- Pytest and pytest-asyncio
- Ruff for static linting and Python `compileall`/import checks

Runtime packages stay in `requirements.txt`; development/CI tools stay in `requirements-dev.txt`.
Do not upgrade model runtimes or FastAPI as part of unrelated work. Pin model versions
(weights, HuggingFace revision, vLLM, CUDA) so results stay reproducible across rentals.

## 3. Existing Architecture

```text
Uvicorn
  -> FastAPI app (`app/main.py`)
  -> versioned API router (`app/api/v1/router.py`)
  -> diagnosis endpoint
  -> Pydantic request validation
  -> `get_ai_provider()` factory
  -> `AIProvider` contract
     -> LocalPipelineProvider | MockAIProvider
        -> Detector (YOLOv8n): locate and classify the appliance, crop the region
        -> Retriever: rank candidate faults for that device from the knowledge base
        -> VLM (Qwen2.5-VL): read surface damage on the crop, reason over the Vietnamese
           description, choose fault codes from the shortlist
        -> KnowledgeBase: resolve codes to Vietnamese names, service codes, price, urgency
  -> normalized DiagnosisResponse, clarification response, or structured error
  -> Backend-FixHome
```

Why the stages are split this way. The detector is a small model trained on the team's own photos
and identifies Vietnamese household appliances more reliably than a general 3B model; cropping also
lets the VLM spend its attention on the device rather than the room. Retrieval narrows the candidate
faults before generation, which is what keeps output inside the catalog. The VLM contributes the two
things neither of the other stages can: reading surface damage off the image, and understanding a
Vietnamese description in context rather than by keyword.

Every Vietnamese string, service code and price returned to customers is looked up from
`app/data/`, never generated. A code the model produces that is absent from the catalog is dropped.
Changing wording or pricing means editing JSON, not retraining.

`app/core/config.py` loads environment settings. `MockAIProvider` makes unit CI deterministic, and
the stub detector and stub VLM let the real pipeline run without weights or a GPU. The health
endpoint exposes only non-sensitive operational metadata.

Preserve this abstraction. Do not put engine conditionals or raw model output into routes.

## 4. Folder Structure

- `.github/workflows/`: independent Python CI.
- `app/main.py`: FastAPI construction, CORS, handlers, routers, health.
- `app/api/v1/`: versioned router and endpoint transport logic.
- `app/schemas/`: Pydantic contracts and enums.
- `app/services/`: provider interface, factory, and the mock engine.
- `app/services/pipeline/`: detector, retriever, VLM adapter, knowledge-base loader, orchestrator.
- `app/data/`: device catalog, fault knowledge base and service mapping. Curated by the team; the
  single source of every Vietnamese string, price range and urgency the service returns.
- `tools/`: Gradio demo, dataset builder, image collector and auto-labeller. Never imported by the
  service, and never a runtime dependency.
- `docker/train/`: pinned training image and its entry point. See `docs/DATASET-AND-TRAINING.md`.
- `app/core/`: configuration and service exception behavior.
- `tests/`: health and provider-contract unit tests.
- `requirements.txt`: runtime/test packages currently needed by the service.
- `requirements-model.txt`: detector/VLM runtime, deliberately excluded from CI.
- `requirements-dev.txt`: CI lint dependencies layered on runtime requirements.
- `pyproject.toml`: Ruff governance.
- `docs/`: repository-local governance.

## 5. Coding Rules

- Modules/functions/variables use snake_case; classes/Pydantic models use PascalCase; constants and
  enum members use UPPER_SNAKE_CASE.
- Endpoints handle HTTP concerns only. Provider selection and SDK work remain in services/adapters.
- Every engine implements the async `AIProvider` contract (`diagnose` and `answer`) and returns the
  normalized schemas; never leak raw model output to consumers.
- Model runtimes (`ultralytics`, `torch`, vLLM clients) are imported lazily inside the adapter that
  needs them, so the service starts and the suite runs without weights or a GPU.
- Request fields need explicit Pydantic constraints appropriate to cost, length, URL/image, and
  category semantics. Preserve camelCase JSON aliases expected by Backend.
- Catch expected provider timeout/rate-limit/unavailable errors explicitly and map to stable error
  codes. Do not catch all errors merely to expose their text.
- Use structured logging at boundaries without prompts, images, keys, tokens, personal data, or raw
  provider payloads. Current ad hoc prints are not acceptable.
- Configuration comes from `Settings`/environment. Update `.env.example`; never hard-code keys.
- Keep provider prompts/templates within the owning adapter or a clearly established prompt module;
  version material contract changes and test their response parsing.
- Reuse existing schemas/services and avoid unnecessary abstraction, sync blocking calls, or broad
  source rewrites.

## 6. Business Rules

- Primary actor is Customer through Backend; Technician/Service Manager may consume advisory output
  only through approved flows. System/Backend is the direct API consumer.
- Diagnosis is preliminary and always includes the approved disclaimer.
- Fault codes belong to this service; service codes belong to Backend and live in
  `service_mapping.json`. An empty mapping means `recommendedServices` is empty, which is a valid
  state and not an error.
- Confidence is between 0 and 1. Below `AI_CONFIDENCE_THRESHOLD` the service returns
  `needs_clarification` with suggested questions and manual service groups. It never guesses.
- The advisory chatbot answers only from retrieved passages and returns citations. With no
  grounding it declines; it never recommends a service or creates booking intent.
- Provider failure, timeout, rate limit, unsupported/invalid input, or insufficient information must
  preserve a manual service-selection fallback. AI failure cannot block Booking.
- Estimated cost is indicative, non-negative, ordered (`min <= max`), and denominated explicitly; it
  is not a quotation or customer approval.
- AI may recommend a service identifier but cannot create bookings, assign a technician, authorize
  spending, or modify Service Order state.
- Schema/error-code changes are cross-repository API changes requiring Backend/client/Docs review.

## 7. Security Rules

- Treat descriptions, image references, category hints, prompts, and provider responses as untrusted.
  Defend against prompt injection by constraining output schemas and never granting tools/business
  authority based on model text.
- Images arrive inline, base64 in JSON or multipart upload. The service never dereferences a URL on
  a caller's behalf, which removes the SSRF surface entirely; do not add URL fetching back.
- Decide an image's format from its bytes, never from a declared content type. Enforce the size cap
  before decoding, and downscale on intake so a large upload cannot exhaust memory.
- Configure strict outbound timeouts and bounded retries; never retry indefinitely or fan out without
  limits. Avoid sending unnecessary personal data to providers.
- Never expose API keys, prompt internals, provider exception strings, stack traces, or customer data
  in HTTP errors/health/logs. Map to stable, safe messages.
- Restrict deployed CORS to approved callers/origins; wildcard methods/headers require deployment
  review. Authentication/authorization remains at Backend unless architecture explicitly changes.
- Keep `.env` ignored and secrets in deployment secret stores. Use mock provider in deterministic CI.
- Review input validation, SSRF/upload risk, prompt injection, secret/sensitive data exposure,
  dependency risk, error leakage, timeout/DoS, and unsafe output use for relevant work.

## 8. Testing Rules

- Unit-test every engine against the normalized contract using stubs; no model download, GPU use or
  live inference in default CI.
- Keep a fixed regression set of real cases and run it whenever weights change. Report device
  classification accuracy against the untrained baseline, and re-measure after AWQ quantization
  rather than assuming it holds.
- Test health/import/startup, valid requests, invalid/empty/oversized input, provider selection,
  timeout, rate limit, provider error, low confidence, malformed provider output, and fallback.
- Assert output bounds, aliases, disclaimer, stable error codes, and absence of secrets/internal text.
- Use `pytest.mark.asyncio` for async units and FastAPI TestClient/HTTPX for API behavior.
- A live provider smoke test requires explicit credentials/scope and must be reported separately; it
  is `NOT VERIFIED` otherwise.

## 9. CI/CD Rules

`.github/workflows/ci.yml` runs independently for pushes and pull requests targeting `main`,
`development`, or the retained `develop` alias:

```text
pip install -r requirements-dev.txt
ruff check app tests
pytest
python import check
python -m compileall -q app tests
start Uvicorn and GET /health
```

All steps are blocking. Do not use `continue-on-error`, real provider keys, or external model calls
in baseline CI. Deployment needs a separate approved workflow with health/readiness, secret store,
timeouts, and rollback controls.

## 10. AI Development Workflow

```text
Task
-> read this guide and relevant Docs-FixHome/Backend contracts
-> inspect endpoint/schema/provider/tests/config/dependencies
-> BA analysis: actor, requirement, input/output, advisory rule, validation, permission boundary,
   API/state, error/fallback, edge cases, affected repositories
-> PM scope review
-> CTO/Tech Lead review: provider boundary, contract compatibility, latency/failure impact,
   maintainability and backward compatibility
-> impact analysis and minimum implementation
-> Senior Developer review
-> Security review, including prompt/SSRF/data/secret/timeout risks
-> Tester review
-> QA/QC trace: requirement -> Backend contract -> schema/provider -> clients -> tests -> docs
-> lint/test/import/compile/startup checks
-> git diff and unintended-change review
-> final architecture review
-> PASS, FAIL, or BLOCKED/NOT VERIFIED
```

If final review finds an issue, determine root cause, fix, rerun, and review again. The final report
must include Task, Repository, Analysis, Files Changed, Implementation, role reviews, Technical
Validation, Issues Found, Auto Fix, Remaining Issues, and Final Status. Never claim live-provider,
security, or startup PASS unless that specific check was executed.
