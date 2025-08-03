from fastapi import APIRouter

from .parser import router as parser_router

router = APIRouter()
router.include_router(parser_router)
