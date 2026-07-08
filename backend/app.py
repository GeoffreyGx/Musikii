import logging
from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI

# APP SETUP
load_dotenv()
logger = logging.getLogger()
app = FastAPI()

# ENDPOINTS
from routers import library
app.include_router(
    library.router,
    prefix="/library",
    tags=["library"]
)

@app.get("/")
async def root():
    return {"message": "Welcome to the Musikii API! Access is controlled beyond this endpoint."}

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)