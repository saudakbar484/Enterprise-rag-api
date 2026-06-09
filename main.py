import uvicorn
from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(title=settings.app_name)

@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=settings.port, reload=settings.debug)