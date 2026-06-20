from fastapi import Depends, FastAPI
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from app.auth import verify_docs_access
from app.router.documents import router as documents_router
from app.router.health import router as health_router
from app.router.home import router as home_router

app = FastAPI(
    title="Eshant Portfolio API",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.include_router(home_router)
app.include_router(health_router)
app.include_router(documents_router)


@app.get("/openapi.json", include_in_schema=False, dependencies=[Depends(verify_docs_access)])
async def openapi():
    return get_openapi(title=app.title, version=app.version, routes=app.routes)


@app.get("/docs", include_in_schema=False, dependencies=[Depends(verify_docs_access)])
async def swagger_ui():
    return get_swagger_ui_html(openapi_url="/openapi.json", title=app.title)


@app.get("/redoc", include_in_schema=False, dependencies=[Depends(verify_docs_access)])
async def redoc():
    return get_redoc_html(openapi_url="/openapi.json", title=app.title)
