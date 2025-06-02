from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import uvicorn
from services.indian_kanoon import IndianKanoonService
from services.cache import CacheService
import asyncio
from datetime import datetime
import time
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Legal Case Finder",
    description="Find similar legal cases based on fact patterns",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add rate limiter to the app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CaseQuery(BaseModel):
    fact_pattern: str
    
    class Config:
        schema_extra = {
            "example": {
                "fact_pattern": "A case involving trademark infringement in e-commerce"
            }
        }

class CaseResult(BaseModel):
    title: str
    url: str
    summary: str
    similarity_score: float

class ErrorResponse(BaseModel):
    detail: str
    timestamp: str

# Initialize services
kanoon_service = IndianKanoonService()
cache_service = CacheService()

# Error handler for generic exceptions
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            detail=str(exc),
            timestamp=datetime.now().isoformat()
        ).dict()
    )

# Background task to clear expired cache
async def clear_expired_cache():
    while True:
        try:
            cache_service.clear_expired()
        except Exception as e:
            print(f"Error clearing cache: {str(e)}")
        await asyncio.sleep(3600)  # Run every hour

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(clear_expired_cache())

@app.get("/", 
         response_model=dict,
         description="Root endpoint to check if the API is running")
@limiter.limit("60/minute")
async def root(request: Request):
    return {"message": "Welcome to Legal Case Finder API", "status": "healthy"}

@app.post("/search", 
          response_model=List[CaseResult],
          description="Search for similar legal cases based on a fact pattern",
          responses={
              500: {"model": ErrorResponse},
              429: {"description": "Rate limit exceeded"},
          })
@limiter.limit("30/minute")
async def search_cases(request: Request, query: CaseQuery):
    try:
        # Check cache first
        cached_results = cache_service.get(query.fact_pattern)
        if cached_results is not None:
            return cached_results
            
        # If not in cache, search Indian Kanoon
        results = await kanoon_service.search_cases(query.fact_pattern)
        
        # Cache the results
        cache_service.set(query.fact_pattern, results)
        
        return results
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 