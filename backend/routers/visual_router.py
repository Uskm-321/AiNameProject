from fastapi import APIRouter, Depends

from core.auth import AuthHandler
from core.visual_service import generate_enterprise_visual
from models.user import User
from schemas.visual import VisualGenerateIn, VisualGenerateOut


auth_handler = AuthHandler()
router = APIRouter(prefix="/visual", tags=["visual"])


@router.post("/generate", response_model=VisualGenerateOut)
async def generate_visual(
    data: VisualGenerateIn,
    current_user: User = Depends(auth_handler.auth_user_dependency),
):
    return await generate_enterprise_visual(data)
