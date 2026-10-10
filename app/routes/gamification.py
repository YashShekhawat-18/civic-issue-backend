from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user
from app.core.responses import success_response
from app.services import gamification_service

router = APIRouter(prefix="/gamification", tags=["Points and Badges"], dependencies=[Depends(get_current_user)])


@router.get("/me")
async def my_points_and_badges(current_user: dict = Depends(get_current_user)):
    return success_response("Points and badges fetched", await gamification_service.get_my_summary(current_user))


@router.get("/badges")
async def all_badges():
    return success_response("Badges fetched", await gamification_service.list_badges())


@router.get("/leaderboard")
async def leaderboard(limit: int = Query(10, ge=1, le=50)):
    return success_response("Leaderboard fetched", await gamification_service.get_leaderboard(limit))
