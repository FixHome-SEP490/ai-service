<h1 align="center">FixHome — AI Service</h1>

<p align="center">
  <strong>FastAPI AI Diagnosis Service cho nền tảng sửa chữa & bảo trì tại nhà FixHome</strong><br>
  <em>Chẩn đoán sơ bộ bằng pipeline tự host: YOLOv8n phát hiện thiết bị, Qwen2.5-VL đọc ảnh và mô tả, tri thức có kiểm duyệt ràng buộc đầu ra</em>
</p>

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI |
| Language | Python 3.11+ |
| Detector | YOLOv8n (Ultralytics) |
| Vision-language | Qwen2.5-VL-3B-Instruct AWQ qua vLLM |
| Grounding | Retrieval trên bảng tri thức có kiểm duyệt |
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
│   ├── services/
│   │   ├── ai_provider.py       # Contract, factory, mock engine
│   │   └── pipeline/
│   │       ├── detector.py         # YOLOv8n stage
│   │       ├── retriever.py        # Retrieval over the knowledge base
│   │       ├── vlm.py              # Qwen2.5-VL stage
│   │       ├── knowledge_base.py   # Curated catalog loader
│   │       └── local_pipeline.py   # Orchestrator
│   └── data/
│       ├── device_catalog.json         # Closed device + condition vocabulary
│       └── fault_knowledge_base.json   # Faults, services, prices, policies
├── tests/
│   ├── test_health.py
│   ├── test_provider_abstraction.py
│   └── test_pipeline.py
├── requirements.txt
└── .env.example
```

## Environment Variables

See [.env.example](.env.example) for all required variables.

> **Note:** AI Service is **advisory only** — it must never control transactions, approve quotations, or change order state.

Chạy mặc định không cần GPU hay weights: detector và VLM có bản stub tất định. Đặt `YOLO_WEIGHTS_PATH`
và `VLM_BASE_URL` để chuyển sang mô hình thật, cài thêm `requirements-model.txt`.

## Verification

```bash
pip install -r requirements-dev.txt
ruff check app tests
pytest
python -m compileall -q app tests
```

## Related Repositories

- [Backend API](https://github.com/FixHome-SEP490/Backend-FixHome)
- [Frontend](https://github.com/FixHome-SEP490/Frontend-FixHome)
- [Mobile](https://github.com/FixHome-SEP490/Mobi-FixHome)
- [Project Documentation](https://github.com/FixHome-SEP490/Docs-FixHome)

## Engineering Governance

Before any change, read [AGENTS.md](AGENTS.md) and the repository-specific
[AI Technical Guide](docs/AI-TECHNICAL-GUIDE.md). The independent CI workflow enforces lint, unit
tests, import/compile checks, and an actual FastAPI health startup check using the mock provider.
