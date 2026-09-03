<h1 align="center">FixHome — AI Service</h1>

<p align="center">
  <strong>FastAPI AI Diagnosis Service cho nền tảng sửa chữa & bảo trì tại nhà FixHome</strong><br>
  <em>Hỗ trợ chẩn đoán sự cố thông minh bằng Gemini / OpenAI API</em>
</p>

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI |
| Language | Python 3.11+ |
| AI Provider | Gemini / OpenAI API |
| Testing | Pytest |

## Prerequisites

- **Python** 3.11 (xem `.python-version`)

## Quick Start

```bash
cp .env.example .env
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Verify

- API: http://localhost:8000
- Health: http://localhost:8000/health
- Docs: http://localhost:8000/docs

```bash
curl http://localhost:8000/health
```

## Project Structure

```
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── api/
│   │   └── v1/
│   │       ├── router.py    # API router
│   │       └── endpoints/
│   │           └── diagnosis.py  # Diagnosis endpoint
│   ├── core/
│   │   ├── config.py        # Settings & config
│   │   └── exceptions.py    # Custom exceptions
│   ├── schemas/
│   │   ├── diagnosis.py     # Request/response schemas
│   │   └── health.py        # Health check schema
│   └── services/
│       ├── ai_provider.py       # Abstract AI provider
│       ├── gemini_provider.py   # Google Gemini implementation
│       └── openai_provider.py   # OpenAI implementation
├── tests/
│   ├── test_health.py
│   └── test_provider_abstraction.py
├── requirements.txt
└── .env.example
```

## Environment Variables

See [.env.example](.env.example) for all required variables.

> **Note:** AI Service is **advisory only** — it must never control transactions, approve quotations, or change order state.

## Verification

```bash
pytest
python -m compileall app tests
```

## Related Repositories

- [Backend API](https://github.com/FixHome-SEP490/Backend-FixHome)
- [Frontend](https://github.com/FixHome-SEP490/Frontend-FixHome)
- [Mobile](https://github.com/FixHome-SEP490/Mobi-FixHome)
- [Project Documentation](https://github.com/FixHome-SEP490/Docs-FixHome)
