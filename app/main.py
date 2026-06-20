from fastapi import FastAPI
from app.router.health import router as health_router

app = FastAPI(title="Eshant Portfolio API")

app.include_router(health_router)


@app.get("/")
async def root():
    return {"message": "Welcome to Eshant Portfolio API"}
