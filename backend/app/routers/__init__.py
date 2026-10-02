"""路由模块汇总导入"""
from app.routers.auth import router as auth_router
from app.routers.units import router as units_router
from app.routers.persons import router as persons_router
from app.routers.custom_fields import router as custom_fields_router
from app.routers.statistics import router as statistics_router
from app.routers.reports import router as reports_router
from app.routers.resume_import import router as resume_import_router
from app.routers.organization import (
    router as departments_router,
    rank_router,
    position_router,
    person_position_router,
)
from app.routers.permissions import router as permissions_router
from app.routers.workspace import router as workspace_router

__all__ = [
    "auth_router",
    "units_router",
    "persons_router",
    "custom_fields_router",
    "statistics_router",
    "reports_router",
    "resume_import_router",
    "departments_router",
    "rank_router",
    "position_router",
    "person_position_router",
    "permissions_router",
    "workspace_router",
]