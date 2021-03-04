from fastapi import FastAPI

from .v1 import router as v1_router

app = FastAPI()

app.include_router(
    v1_router,
    # prefix="/v1",
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("service.main:app", host="0.0.0.0", port=9000, log_level="info")
