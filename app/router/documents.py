from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/documents", tags=["documents"])

_BASE = Path(__file__).resolve().parents[2] / "core" / "src_data"

_FILES = {
    "transcript": _BASE / "BTech (2).pdf",
    "degree": _BASE / "OriginalDegree (2).pdf",
}


@router.get("/{doc_key}")
async def get_document(doc_key: str):
    path = _FILES.get(doc_key)
    if path is None or not path.exists():
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(
        path,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )
