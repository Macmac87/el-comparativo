"""
El Comparativo - Main FastAPI Application
RAG-powered vehicle search aggregator for Venezuela
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncpg
from typing import Optional, List
import os
from dotenv import load_dotenv

from database import init_db, get_db_pool
from rag import RAGSearchEngine
from models import (
    VehicleResponse, 
    SearchRequest, 
    SearchResponse,
    ConversationalSearchRequest
)
from auth_routes import router as auth_router
from auth import get_current_active_user, UserService

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup"""
    # Initialize database pool
    await init_db()
    
    # Initialize RAG engine
    app.state.rag_engine = RAGSearchEngine()
    
    print("✅ Database pool initialized")
    print("✅ RAG engine initialized")
    
    yield
    
    # Cleanup
    pool = get_db_pool()
    if pool:
        await pool.close()
    print("🔴 Database pool closed")


app = FastAPI(
    title="El Comparativo API",
    description="RAG-powered vehicle search aggregator for Venezuela",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev
        "https://carsearch.ve",   # Production
        os.getenv("FRONTEND_URL", "*")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "CarSearch VE API",
        "status": "online",
        "version": "1.0.0",
        "rag_enabled": True
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    try:
        pool = get_db_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "ok",
        "database": db_status,
        "rag_engine": "initialized"
    }


@app.post("/api/search/conversational", response_model=SearchResponse)
async def conversational_search(
    request: ConversationalSearchRequest,
    current_user: dict = Depends(get_current_active_user)
):
    """
    RAG-powered conversational search (requires authentication)
    
    Example queries:
    - "Busco una Toyota 4Runner 2018-2020 blanca menos de 35 mil dólares"
    - "Pick-up diesel doble cabina que no sea de Caracas"
    - "Camioneta automática con poco kilometraje bajo 20 mil"
    """
    try:
        # Check search limit
        can_search = await UserService.check_search_limit(current_user["id"])
        
        if not can_search:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Daily search limit reached. Upgrade to Premium for unlimited searches."
            )
        
        rag_engine = app.state.rag_engine
        
        # Use RAG to perform semantic search
        results = await rag_engine.search(
            query=request.query,
            limit=request.limit or 20,
            filters=request.filters
        )
        
        # Increment search count
        await UserService.increment_search_count(current_user["id"])
        
        # Log search to history
        pool = get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO search_history (user_id, query, filters, results_count)
                VALUES ($1, $2, $3, $4)
            """, current_user["id"], request.query, request.filters, len(results))
        
        return SearchResponse(
            query=request.query,
            total_results=len(results),
            vehicles=results,
            search_type="conversational_rag"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search", response_model=SearchResponse)
async def traditional_search(request: SearchRequest):
    """
    Traditional filter-based search
    
    Filters: brand, model, year_min, year_max, price_max_usd, transmission, etc.
    """
    try:
        pool = get_db_pool()
        
        # Build SQL query dynamically based on filters
        query = "SELECT * FROM vehicles WHERE is_active = true"
        params = []
        param_count = 1
        
        if request.brand:
            query += f" AND LOWER(brand) = LOWER(${param_count})"
            params.append(request.brand)
            param_count += 1
        
        if request.model:
            query += f" AND LOWER(model) LIKE LOWER(${param_count})"
            params.append(f"%{request.model}%")
            param_count += 1
        
        if request.year_min:
            query += f" AND year >= ${param_count}"
            params.append(request.year_min)
            param_count += 1
        
        if request.year_max:
            query += f" AND year <= ${param_count}"
            params.append(request.year_max)
            param_count += 1
        
        if request.price_max_usd:
            query += f" AND price_usd <= ${param_count}"
            params.append(request.price_max_usd)
            param_count += 1
        
        if request.location:
            query += f" AND LOWER(location) LIKE LOWER(${param_count})"
            params.append(f"%{request.location}%")
            param_count += 1
        
        query += f" ORDER BY updated_at DESC LIMIT ${param_count}"
        params.append(request.limit or 20)
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        
        vehicles = [dict(row) for row in rows]
        
        return SearchResponse(
            query=str(request.dict()),
            total_results=len(vehicles),
            vehicles=vehicles,
            search_type="traditional_filters"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vehicles/{vehicle_id}", response_model=VehicleResponse)
async def get_vehicle(vehicle_id: int):
    """Get single vehicle by ID"""
    try:
        pool = get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM vehicles WHERE id = $1 AND is_active = true",
                vehicle_id
            )
        
        if not row:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        
        return dict(row)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/brands")
async def get_brands():
    """Get list of available brands"""
    try:
        pool = get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT DISTINCT brand, COUNT(*) as count
                FROM vehicles
                WHERE is_active = true AND brand IS NOT NULL
                GROUP BY brand
                ORDER BY count DESC, brand ASC
            """)
        
        return [{"brand": row["brand"], "count": row["count"]} for row in rows]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/models/{brand}")
async def get_models(brand: str):
    """Get models for a specific brand"""
    try:
        pool = get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT DISTINCT model, COUNT(*) as count
                FROM vehicles
                WHERE is_active = true 
                  AND LOWER(brand) = LOWER($1)
                  AND model IS NOT NULL
                GROUP BY model
                ORDER BY count DESC, model ASC
            """, brand)
        
        return [{"model": row["model"], "count": row["count"]} for row in rows]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """Get platform statistics"""
    try:
        pool = get_db_pool()
        async with pool.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_vehicles,
                    COUNT(DISTINCT brand) as total_brands,
                    COUNT(DISTINCT source) as total_sources,
                    AVG(price_usd) as avg_price_usd,
                    MIN(price_usd) as min_price_usd,
                    MAX(price_usd) as max_price_usd
                FROM vehicles
                WHERE is_active = true
            """)
        
        return dict(stats)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
