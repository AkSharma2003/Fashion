import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.errors import BusinessError, error_body
from app.modules import routers

log = logging.getLogger("wearverse")

app = FastAPI(title=settings.app_name, version="1.0.0",
              description="WearVerse: one shop and one website sharing one stock, with khata, "
                          "WhatsApp bills, Tally integration, employees and fall-pico.")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "environment": settings.environment}


@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message, exc.extra))


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    log.warning("integrity error on %s: %s", request.url.path, exc.orig)
    return JSONResponse(status_code=409, content=error_body("DUPLICATE", "This record already exists or conflicts with another one."))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    where = ".".join(str(p) for p in first.get("loc", []) if p != "body")
    message = f"{where}: {first.get('msg', 'invalid input')}" if where else first.get("msg", "Invalid input")
    body = error_body("VALIDATION_ERROR", message)
    body["errors"] = exc.errors()
    # Keep FastAPI's list-style `detail` for older screens that expect it.
    body["detail"] = exc.errors()
    return JSONResponse(status_code=422, content=jsonable(body))


def jsonable(value):
    from fastapi.encoders import jsonable_encoder
    return jsonable_encoder(value)


# Local development only: profile photos saved on disk when R2 is not set up.
if settings.is_local:
    from fastapi.staticfiles import StaticFiles

    from app.modules.store.account import MEDIA_DIR
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")

for prefix, router in routers:
    app.include_router(router, prefix=f"/api/v1/{prefix}", tags=[prefix])

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
