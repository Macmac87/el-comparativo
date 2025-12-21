"""
RAG Search Engine for CarSearch VE
Based on RAGFIN1 architecture with OpenAI embeddings + pgvector
"""

import asyncpg
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
from typing import List, Dict, Optional, Any
import json
import os
from datetime import datetime

from database import get_db_pool


class RAGSearchEngine:
    """
    RAG-powered search engine for vehicles
    
    Components:
    1. Query understanding (LLM-based extraction)
    2. Semantic search (vector similarity)
    3. Hybrid ranking (semantic + filters)
    """
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.anthropic_client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.embedding_model = "text-embedding-3-small"
        self.embedding_dim = 1536
        
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text
        Uses OpenAI text-embedding-3-small (same as RAGFIN1)
        """
        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"❌ Embedding generation failed: {e}")
            raise
    
    def prepare_vehicle_text(self, vehicle: Dict[str, Any]) -> str:
        """
        Prepare vehicle data as text for embedding
        Combines all searchable fields
        """
        parts = []
        
        if vehicle.get("brand"):
            parts.append(f"Marca: {vehicle['brand']}")
        
        if vehicle.get("model"):
            parts.append(f"Modelo: {vehicle['model']}")
        
        if vehicle.get("year"):
            parts.append(f"Año: {vehicle['year']}")
        
        if vehicle.get("price_usd"):
            parts.append(f"Precio: ${vehicle['price_usd']:,.0f} USD")
        
        if vehicle.get("transmission"):
            parts.append(f"Transmisión: {vehicle['transmission']}")
        
        if vehicle.get("fuel_type"):
            parts.append(f"Combustible: {vehicle['fuel_type']}")
        
        if vehicle.get("color"):
            parts.append(f"Color: {vehicle['color']}")
        
        if vehicle.get("location"):
            parts.append(f"Ubicación: {vehicle['location']}")
        
        if vehicle.get("mileage"):
            parts.append(f"Kilometraje: {vehicle['mileage']:,} km")
        
        if vehicle.get("description"):
            parts.append(f"Descripción: {vehicle['description'][:500]}")  # Truncate long descriptions
        
        return "\n".join(parts)
    
    async def extract_filters_from_query(self, query: str) -> Dict[str, Any]:
        """
        Use LLM to extract structured filters from natural language query
        
        Example:
        "Busco Toyota 4Runner 2018-2020 blanca menos de 35 mil dólares"
        →
        {
            "brand": "Toyota",
            "model": "4Runner", 
            "year_min": 2018,
            "year_max": 2020,
            "color": "blanca",
            "price_max_usd": 35000
        }
        """
        
        prompt = f"""Eres un experto en búsqueda de vehículos. Extrae los parámetros de búsqueda de esta consulta en español.

Consulta: "{query}"

Devuelve SOLO un objeto JSON válido con estos campos (usa null si no se menciona):
- brand: string (marca del vehículo)
- model: string (modelo específico)
- year_min: integer (año mínimo)
- year_max: integer (año máximo)
- price_max_usd: integer (precio máximo en dólares)
- transmission: "Manual" | "Automática" | null
- fuel_type: "Gasolina" | "Diesel" | "Eléctrico" | "Híbrido" | null
- color: string (color del vehículo)
- location: string (ciudad o estado)
- vehicle_type: "Sedan" | "SUV" | "Pick-up" | "Hatchback" | "Coupe" | null

Ejemplos:

Consulta: "Busco Toyota 4Runner 2018-2020 blanca menos de 35 mil"
{{"brand": "Toyota", "model": "4Runner", "year_min": 2018, "year_max": 2020, "color": "blanca", "price_max_usd": 35000}}

Consulta: "Pick-up diesel doble cabina que no sea de Caracas"
{{"vehicle_type": "Pick-up", "fuel_type": "Diesel"}}

Consulta: "Camioneta automática bajo 25 mil"
{{"vehicle_type": "SUV", "transmission": "Automática", "price_max_usd": 25000}}

Ahora extrae los parámetros de la consulta del usuario. Responde SOLO con el JSON, sin texto adicional."""

        try:
            # Use Claude for extraction (faster & cheaper than GPT-4)
            response = await self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Extract JSON from response
            content = response.content[0].text.strip()
            
            # Remove markdown code blocks if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()
            
            filters = json.loads(content)
            return filters
            
        except Exception as e:
            print(f"⚠️ Filter extraction failed: {e}")
            return {}
    
    async def semantic_search(
        self, 
        query: str, 
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search using vector similarity
        
        Steps:
        1. Generate query embedding
        2. Find similar vehicles using cosine similarity
        3. Apply additional filters if provided
        """
        
        # Generate embedding for query
        query_embedding = await self.generate_embedding(query)
        
        # Build SQL with vector search
        sql = """
            SELECT 
                v.*,
                1 - (v.embedding <=> $1::vector) as similarity_score
            FROM vehicles v
            WHERE v.is_active = true
        """
        
        params = [query_embedding]
        param_count = 2
        
        # Apply filters if provided
        if filters:
            if filters.get("brand"):
                sql += f" AND LOWER(v.brand) = LOWER(${param_count})"
                params.append(filters["brand"])
                param_count += 1
            
            if filters.get("model"):
                sql += f" AND LOWER(v.model) LIKE LOWER(${param_count})"
                params.append(f"%{filters['model']}%")
                param_count += 1
            
            if filters.get("year_min"):
                sql += f" AND v.year >= ${param_count}"
                params.append(filters["year_min"])
                param_count += 1
            
            if filters.get("year_max"):
                sql += f" AND v.year <= ${param_count}"
                params.append(filters["year_max"])
                param_count += 1
            
            if filters.get("price_max_usd"):
                sql += f" AND v.price_usd <= ${param_count}"
                params.append(filters["price_max_usd"])
                param_count += 1
            
            if filters.get("transmission"):
                sql += f" AND LOWER(v.transmission) = LOWER(${param_count})"
                params.append(filters["transmission"])
                param_count += 1
            
            if filters.get("fuel_type"):
                sql += f" AND LOWER(v.fuel_type) = LOWER(${param_count})"
                params.append(filters["fuel_type"])
                param_count += 1
            
            if filters.get("color"):
                sql += f" AND LOWER(v.color) LIKE LOWER(${param_count})"
                params.append(f"%{filters['color']}%")
                param_count += 1
            
            if filters.get("location"):
                sql += f" AND LOWER(v.location) LIKE LOWER(${param_count})"
                params.append(f"%{filters['location']}%")
                param_count += 1
        
        # Order by similarity and limit
        sql += f" ORDER BY v.embedding <=> $1::vector LIMIT ${param_count}"
        params.append(limit)
        
        # Execute query
        pool = get_db_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
        
        # Convert to list of dicts
        results = []
        for row in rows:
            vehicle = dict(row)
            # Remove embedding from response (too large)
            vehicle.pop("embedding", None)
            results.append(vehicle)
        
        return results
    
    async def search(
        self, 
        query: str, 
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Main search method - combines filter extraction + semantic search
        
        Workflow:
        1. Extract filters from natural language query
        2. Perform semantic search with extracted filters
        3. Return ranked results
        """
        
        # Extract filters from query if not provided
        if not filters:
            filters = await self.extract_filters_from_query(query)
            print(f"🔍 Extracted filters: {filters}")
        
        # Perform semantic search
        results = await self.semantic_search(query, limit=limit, filters=filters)
        
        print(f"✅ Found {len(results)} vehicles")
        
        return results
    
    async def embed_vehicle(self, vehicle: Dict[str, Any]) -> List[float]:
        """
        Generate embedding for a vehicle
        Used when adding new vehicles to the database
        """
        text = self.prepare_vehicle_text(vehicle)
        embedding = await self.generate_embedding(text)
        return embedding
    
    async def reindex_all_vehicles(self):
        """
        Regenerate embeddings for all vehicles in database
        Run this after major schema changes or data imports
        """
        pool = get_db_pool()
        
        async with pool.acquire() as conn:
            # Get all vehicles without embeddings
            vehicles = await conn.fetch("""
                SELECT * FROM vehicles 
                WHERE is_active = true 
                  AND (embedding IS NULL OR embedding = '{}'::vector)
            """)
            
            print(f"📊 Reindexing {len(vehicles)} vehicles...")
            
            for i, vehicle in enumerate(vehicles):
                try:
                    # Generate embedding
                    embedding = await self.embed_vehicle(dict(vehicle))
                    
                    # Update database
                    await conn.execute("""
                        UPDATE vehicles 
                        SET embedding = $1::vector, updated_at = NOW()
                        WHERE id = $2
                    """, embedding, vehicle["id"])
                    
                    if (i + 1) % 10 == 0:
                        print(f"  ✅ Processed {i + 1}/{len(vehicles)}")
                    
                except Exception as e:
                    print(f"  ❌ Failed to embed vehicle {vehicle['id']}: {e}")
            
            print(f"🎉 Reindexing complete!")


# Singleton instance
_rag_engine = None

def get_rag_engine() -> RAGSearchEngine:
    """Get singleton RAG engine instance"""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGSearchEngine()
    return _rag_engine
