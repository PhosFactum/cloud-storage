from fastapi import FastAPI
from app.database import Base, engine
from app.routes import auth


app = FastAPI(
    title="Cloud Storage API",
    version="0.1.0",
    description="Backend of cloud storage"
)

app.include_router(auth.router)

Base.metadata.create_all(bind=engine)


@app.get("/")
async def root():
    return {"message": "Cloud Storage Backend is working!"}