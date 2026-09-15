# app/api/v1/router.py
from fastapi import APIRouter

from app.api.v1.endpoints import chat, diagnosis, meta

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(diagnosis.router, prefix="/diagnosis", tags=["Diagnosis"])
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
api_router.include_router(meta.router, prefix="/meta", tags=["Meta"])
