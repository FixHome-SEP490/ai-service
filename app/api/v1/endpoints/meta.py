# app/api/v1/endpoints/meta.py
from fastapi import APIRouter

from app.services.pipeline.knowledge_base import get_knowledge_base

router = APIRouter()


@router.get(
    "/catalog",
    summary="Device types, visible conditions and service groups the engine knows",
)
async def get_catalog() -> dict:
    """Published so Backend and clients stay aligned with the trained catalog.

    Anything outside these lists cannot be produced by the engine.
    """
    kb = get_knowledge_base()
    return {
        "deviceTypes": [
            {
                "deviceType": d,
                "nameVi": kb.device_name_vi(d),
                "detectorClass": d in kb.detector_classes,
            }
            for d in kb.device_types
        ],
        "visibleConditions": [
            {"code": c, "nameVi": kb.condition_name_vi(c)} for c in kb.condition_codes
        ],
        "serviceGroupCodes": kb.all_service_groups(),
    }
