"""
FastAPI REST API Server for Icd10 Ccsr Mapper.
"""
from typing import Dict, Any, List
from functools import lru_cache
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .base import AuditLogger, PHIGuard, SecurityException
from ccsr_mapper import CCSRMapper
from .models import SystemTaskPayload, ConsensusDossier
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")

app = FastAPI(
    title="Icd10 Ccsr Mapper API",
    description="Enterprise Distributed Component Platform (Clinical & Biomedical AI)",
    version="3.0.0-ENTERPRISE",
)


class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "HEALTHY", "service": "icd10-ccsr-mapper", "domain": "Clinical & Biomedical AI", "standard": "CAP / CLSI / ISO Standards", "version": "3.0.0-ENTERPRISE"}


@app.get("/metrics")
def metrics():
    return {
        "dossiers_processed_total": len(supervisor.dossier_registry),
        "audit_blocks_total": len(AuditLogger.get_trail()),
        "system_status": "NOMINAL_OPTIMAL"
    }


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return dossier.to_dict()


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        ans = supervisor.query_supervisory_chat(req.query)
        return {"response": ans}
    except SecurityException:
        raise HTTPException(status_code=400, detail="Input contains a restricted identifier")


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(), "verified": AuditLogger.verify_integrity()}

@lru_cache(maxsize=1)
def _load_ccsr_mapping(path: str):
    return CCSRMapper.from_csv(path)


@app.get("/api/ccsr/{code}")
def api_ccsr_lookup(code: str):
    """Exact diagnosis code lookup; mapping release configured on the server."""
    mapping_path = os.getenv("CCSR_MAPPING_CSV")
    if not mapping_path:
        raise HTTPException(status_code=503, detail="CCSR_MAPPING_CSV is not configured")
    try:
        mapper = _load_ccsr_mapping(mapping_path)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Configured CCSR mapping is unavailable") from exc
    result = mapper.lookup(code)
    if not result["found"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
