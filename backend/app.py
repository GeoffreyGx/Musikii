import os
import logging
from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI, Security, HTTPException, Depends, status
from fastapi.security import APIKeyHeader

# APP SETUP
load_dotenv()
logger = logging.getLogger()
app = FastAPI()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
API_KEY = os.getenv("API_KEY")
if API_KEY == None:
    raise Exception("API Key was not specified in environment variables")


async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key


# ENDPOINTS
from routers import library
app.include_router(
    library.router,
    prefix="/library",
    tags=["library"],
    dependencies=[Depends(get_api_key)]
)

@app.get("/")
async def root():
    return {"message": "Welcome to the Musikii API! Access is controlled beyond this endpoint."}

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)