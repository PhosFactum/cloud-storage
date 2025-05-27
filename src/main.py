# src/main.py

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from database import Base, engine
from routes import auth, users, files
from utils.errors import AppError

app = FastAPI(
    title="Cloud Storage API",
    version="0.1.0",
    description="Backend of cloud storage"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],     
    allow_headers=["*"],         
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(files.router)

app.mount("/", StaticFiles(directory="client", html=True), name="client")

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

Base.metadata.create_all(bind=engine)
