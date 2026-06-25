# =============================================================
# AeroDesk — Fare Class Schemas
# backend/schemas/fare_class_schemas.py
# =============================================================

from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from decimal import Decimal


class FareClassResponse(BaseModel):
    fare_class_id:          int
    class_name:             str
    multiplier:             Decimal
    baggage_allowance_kg:   int
    description:            Optional[str]
    created_at:             datetime

    model_config = {"from_attributes": True}


class FareClassListResponse(BaseModel):
    total:          int
    fare_classes:   list[FareClassResponse]
