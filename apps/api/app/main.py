from fastapi import FastAPI

from app.core.config import settings
from app.modules import routers

app = FastAPI(title=settings.app_name)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "environment": settings.environment}


for name, router in routers:
    app.include_router(
        router, 
        prefix=f"/api/v1/{name.replace('_', '-')}", 
        tags=[name]
    )
