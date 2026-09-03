# FixHome AI Service — Agent Instructions

Before changing code, read the canonical project documentation:

1. [Project Documentation](https://github.com/FixHome-SEP490/Docs-FixHome/blob/main/PROJECT_DOCUMENTATION.md)
2. [AI Development Workflow](https://github.com/FixHome-SEP490/Docs-FixHome/blob/main/AI_DEVELOPMENT_WORKFLOW.md)
3. [Current Tasks](https://github.com/FixHome-SEP490/Docs-FixHome/blob/main/CURRENT_TASKS.md)

## AI Service Rules

- AI output is advisory and untrusted; it must never authorize transactions or change order state.
- Preserve the provider abstraction and graceful fallback behavior.
- Keep request and response schemas aligned with Backend DTOs.
- Never commit provider keys or local `.env` files.
- Coordinate every contract change with Backend, Frontend, Mobile, and Docs repositories.
- Run `pytest` and `python -m compileall app tests` before reporting completion.
