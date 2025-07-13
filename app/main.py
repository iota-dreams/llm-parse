import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import router as parser_router
from llm_parse.utils import get_logger

load_dotenv()
logger = get_logger("LLM_API")

app = FastAPI(
    title="LLM PDF Parsing API",
    description="Upload a PDF and get structured content using LLM and VLM pipelines.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS setup (edit 'allow_origins' for security in production)
app.add_middleware(
    CORSMiddleware,
    # TODO: Replace '*' with a list of allowed domains in prod
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount versioned router
app.include_router(parser_router, prefix="/parse", tags=["PDF Parser"])


@app.get("/", tags=["Health"])
async def health_check() -> dict:
    """
    Health check endpoint to verify the API is up and running.
    """
    return {"status": "🟢 API is running", "version": app.version}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global error handler to catch uncaught exceptions with logging.
    """
    logger.exception(f"Unhandled exception during request: {request.url}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


if __name__ == "__main__":
    # Direct run for dev mode; use gunicorn/uvicorn CLI for production
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
