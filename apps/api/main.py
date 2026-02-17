from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apps.api.routers import chat, admin

app = FastAPI(title="Awaqi API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/v1/chat", tags=["chat"])
app.include_router(admin.router, prefix="/v1", tags=["admin"])

@app.get("/health")
async def health_check():
    return {"status": "working", "service": "api"}
