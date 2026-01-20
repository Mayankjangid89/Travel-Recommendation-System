from fastapi import FastAPI
from api.routes.health import router as health_router
from api.routes.agencies import router as agencies_router
from api.routes.packages import router as packages_router
from api.routes.recommend import router as recommend_router

app = FastAPI(
    title="Travel AI Agent API",
    version="1.0.0",
    description="AI-powered travel package recommendation backend"
)

app.include_router(health_router)
app.include_router(agencies_router)
app.include_router(packages_router)
app.include_router(recommend_router)

@app.get("/")
def root():
    return {"message": "Travel AI Agent API is running ✅"}
