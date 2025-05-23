from fastapi import FastAPI
from database import Base, engine
from routes import auth, user, files


app = FastAPI(
    title="Cloud Storage API",
    version="0.1.0",
    description="Backend of cloud storage"
)

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(files.router)


Base.metadata.create_all(bind=engine)