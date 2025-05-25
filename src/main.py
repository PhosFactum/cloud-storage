from fastapi import FastAPI
from database import Base, engine
from routes import auth, users, files


app = FastAPI(
    title="Cloud Storage API",
    version="0.1.0",
    description="Backend of cloud storage"
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(files.router)


Base.metadata.create_all(bind=engine)