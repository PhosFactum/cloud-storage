from fastapi import FastAPI, Request
from database import Base, engine
from routes import auth, users, files
from fastapi.responses import JSONResponse
from utils.errors import AppError


app = FastAPI(
    title="Cloud Storage API",
    version="0.1.0",
    description="Backend of cloud storage"
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(files.router)

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """
    Catches all AppError and returns JSON with proper status code.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

Base.metadata.create_all(bind=engine)