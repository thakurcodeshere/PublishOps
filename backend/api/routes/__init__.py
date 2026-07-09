"""API routes package — aggregate all routers into a single api_router."""

from fastapi import APIRouter

from backend.api.routes.analytics import router as analytics_router
from backend.api.routes.calibration import router as calibration_router
from backend.api.routes.content import router as content_router
from backend.api.routes.pipeline import router as pipeline_router
from backend.api.routes.platforms import router as platforms_router
from backend.api.routes.redteam import router as redteam_router
from backend.api.routes.scheduler import router as scheduler_router
from backend.api.routes.settings import router as settings_router
from backend.api.routes.topics import router as topics_router
from backend.api.routes.webhooks import router as webhooks_router

api_router = APIRouter()
api_router.include_router(topics_router, prefix="/topics", tags=["Topics"])
api_router.include_router(content_router, prefix="/content", tags=["Content"])
api_router.include_router(pipeline_router, prefix="/pipeline", tags=["Pipeline"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(scheduler_router, prefix="/scheduler", tags=["Scheduler"])
api_router.include_router(settings_router, prefix="/settings", tags=["Settings"])
api_router.include_router(platforms_router, prefix="/platforms", tags=["Platforms"])
api_router.include_router(calibration_router, prefix="/calibration", tags=["Calibration"])
api_router.include_router(redteam_router, prefix="/redteam", tags=["RedTeam"])
api_router.include_router(webhooks_router, prefix="/webhooks", tags=["Webhooks"])
