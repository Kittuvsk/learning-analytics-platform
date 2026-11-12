
from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.admin import router as admin_router
from app.api.routes.resources import router as resources_router
from app.api.routes.analytics import router as analytics_router
from app.api.routes.courses import router as courses_router
from app.api.routes.assessments import router as assessments_router
from app.api.routes.analytics_extended import router as extended_analytics_router

app = FastAPI(
    title="Learning Analytics Platform",
    description="Learning participation, engagement and outcome analytics",
    version="1.0.0",
)

# Register API routers
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(resources_router)
app.include_router(analytics_router)
app.include_router(courses_router)
app.include_router(assessments_router)
app.include_router(extended_analytics_router)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": "Learning Analytics Platform",
    }
