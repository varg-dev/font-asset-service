import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from .v1 import router as v1_router


app = FastAPI(docs_url="/docs", redoc_url=None)

app.include_router(
    v1_router,
    prefix="/api",
)


origins = os.environ.get('CORS_ALLOWED_DOMAINS', '').split(';')

if len(origins) > 0:
    print('Allow CORS for following domains:', origins, flush=True)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(GZipMiddleware, minimum_size=2048) # bytes

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("service.main:app", host="0.0.0.0", port=8192, log_level="info")
