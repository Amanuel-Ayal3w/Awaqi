import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routers import chat, admin

app = FastAPI(title="Awaqi API", version="1.0.0")

# Read allowed origins from env so production can lock this down.
# Defaults include both localhost and 127.0.0.1 for local development.
_raw_origins = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)
allowed_origins = list(
    dict.fromkeys([o.strip() for o in _raw_origins.split(",") if o.strip()])
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/v1/chat", tags=["chat"])
app.include_router(admin.router, prefix="/v1", tags=["admin"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "api"}
