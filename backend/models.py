"""
Pydantic models for request/response validation
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


class VehicleBase(BaseModel):
    """Base vehicle model"""
    source: str
    external_id: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    year: Optional[int] = None
    price_usd: Optional[Decimal] = None
    price_bs: Optional[Decimal] = None
    mileage: Optional[int] = None
    transmission: Optional[str] = None
    fuel_type: Optional[str] = None
    color: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    images: Optional[List[str]] = None
    contact: Optional[Dict[str, Any]] = None
    url: Optional[str] = None


class VehicleCreate(VehicleBase):
    """Model for creating a new vehicle"""
    pass


class VehicleResponse(VehicleBase):
    """Model for vehicle response"""
    id: int
    scraped_at: datetime
    updated_at: datetime
    is_active: bool
    similarity_score: Optional[float] = None
    
    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    """Traditional filter-based search request"""
    brand: Optional[str] = None
    model: Optional[str] = None
    year_min: Optional[int] = Field(None, ge=1900, le=2030)
    year_max: Optional[int] = Field(None, ge=1900, le=2030)
    price_min_usd: Optional[Decimal] = Field(None, ge=0)
    price_max_usd: Optional[Decimal] = Field(None, ge=0)
    mileage_max: Optional[int] = Field(None, ge=0)
    transmission: Optional[str] = None
    fuel_type: Optional[str] = None
    color: Optional[str] = None
    location: Optional[str] = None
    limit: Optional[int] = Field(20, ge=1, le=100)
    
    @validator("year_max")
    def year_max_must_be_greater(cls, v, values):
        if v and "year_min" in values and values["year_min"]:
            if v < values["year_min"]:
                raise ValueError("year_max must be greater than year_min")
        return v


class ConversationalSearchRequest(BaseModel):
    """RAG-powered conversational search request"""
    query: str = Field(..., min_length=3, max_length=500)
    limit: Optional[int] = Field(20, ge=1, le=100)
    filters: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Busco una Toyota 4Runner 2018-2020 blanca menos de 35 mil dólares",
                "limit": 20
            }
        }


class SearchResponse(BaseModel):
    """Search response with results"""
    query: str
    total_results: int
    vehicles: List[Dict[str, Any]]
    search_type: str
    extracted_filters: Optional[Dict[str, Any]] = None


class AlertCreate(BaseModel):
    """Create price alert"""
    user_email: str = Field(..., regex=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    query: str = Field(..., min_length=3)
    filters: Optional[Dict[str, Any]] = None
    max_price_usd: Optional[Decimal] = None


class AlertResponse(BaseModel):
    """Alert response"""
    id: int
    user_email: str
    query: str
    filters: Optional[Dict[str, Any]]
    max_price_usd: Optional[Decimal]
    is_active: bool
    created_at: datetime
    last_checked: Optional[datetime]
    last_notified: Optional[datetime]
    
    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    """Platform statistics"""
    total_vehicles: int
    total_brands: int
    total_sources: int
    avg_price_usd: Optional[Decimal]
    min_price_usd: Optional[Decimal]
    max_price_usd: Optional[Decimal]


class BrandResponse(BaseModel):
    """Brand with count"""
    brand: str
    count: int


class ModelResponse(BaseModel):
    """Model with count"""
    model: str
    count: int


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    database: str
    rag_engine: str
