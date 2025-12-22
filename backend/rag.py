"""
RAG Search Engine for El Comparativo
Semantic vehicle search using embeddings and pgvector
"""

import os
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from database import get_db_pool


class RAGSearchEngine:
    """RAG-powered vehicle search engine"""
    
    def __init__(self):
        """Initialize RAG engine with OpenAI and Anthropic"""
        # OpenAI client for embeddings
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise ValueError("OPENAI_API_KEY not set")
        
        self.openai_client = AsyncOpenAI(api_key=openai_key)
        
        # Anthropic client for conversational search
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        self.anthropic_client = AsyncAnthropic(api_key=anthropic_key)
        
        print("✅ RAG engine initialized with OpenAI embeddings")
    
    
    async def create_embedding(self, text: str) -> List[float]:
        """Create embedding vector for text using OpenAI"""
        try:
            response = await self.openai_client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Embedding error: {e}")
            return []
    
    
    async def search(
        self,
        query: str,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search vehicles using conversational query with semantic search
        """
        try:
            pool = get_db_pool()
            
            # Parse query with Claude to extract filters
            parsed = await self._parse_query_with_claude(query)
            
            # Merge with explicit filters
            if filters:
                parsed.update(filters)
            
            # Create embedding for semantic search
            query_embedding = await self.create_embedding(query)
            
            if not query_embedding:
                # Fallback to filter-only search
                return await self._filter_search(parsed, limit)
            
            # Build SQL with vector similarity
            sql_query = """
                SELECT *, 
                       (embedding <=> $1::vector) as similarity
                FROM vehicles 
                WHERE is_active = true
            """
            params = [query_embedding]
            param_count = 2
            
            if parsed.get("brand"):
                sql_query += f" AND LOWER(brand) = LOWER(${param_count})"
                params.append(parsed["brand"])
                param_count += 1
            
            if parsed.get("model"):
                sql_query += f" AND LOWER(model) LIKE LOWER(${param_count})"
                params.append(f"%{parsed['model']}%")
                param_count += 1
            
            if parsed.get("year_min"):
                sql_query += f" AND year >= ${param_count}"
                params.append(parsed["year_min"])
                param_count += 1
            
            if parsed.get("year_max"):
                sql_query += f" AND year <= ${param_count}"
                params.append(parsed["year_max"])
                param_count += 1
            
            if parsed.get("price_max_usd"):
                sql_query += f" AND price_usd <= ${param_count}"
                params.append(parsed["price_max_usd"])
                param_count += 1
            
            if parsed.get("transmission"):
                sql_query += f" AND LOWER(transmission) = LOWER(${param_count})"
                params.append(parsed["transmission"])
                param_count += 1
            
            if parsed.get("location"):
                sql_query += f" AND LOWER(location) LIKE LOWER(${param_count})"
                params.append(f"%{parsed['location']}%")
                param_count += 1
            
            sql_query += f" ORDER BY similarity ASC LIMIT ${param_count}"
            params.append(limit)
            
            # Execute query
            async with pool.acquire() as conn:
                rows = await conn.fetch(sql_query, *params)
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"RAG search error: {e}")
            return []
    
    
    async def _filter_search(self, filters: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        """Fallback filter-only search"""
        try:
            pool = get_db_pool()
            sql_query = "SELECT * FROM vehicles WHERE is_active = true"
            params = []
            param_count = 1
            
            if filters.get("brand"):
                sql_query += f" AND LOWER(brand) = LOWER(${param_count})"
                params.append(filters["brand"])
                param_count += 1
            
            if filters.get("model"):
                sql_query += f" AND LOWER(model) LIKE LOWER(${param_count})"
                params.append(f"%{filters['model']}%")
                param_count += 1
            
            if filters.get("year_min"):
                sql_query += f" AND year >= ${param_count}"
                params.append(filters["year_min"])
                param_count += 1
            
            if filters.get("year_max"):
                sql_query += f" AND year <= ${param_count}"
                params.append(filters["year_max"])
                param_count += 1
            
            if filters.get("price_max_usd"):
                sql_query += f" AND price_usd <= ${param_count}"
                params.append(filters["price_max_usd"])
                param_count += 1
            
            sql_query += f" ORDER BY updated_at DESC LIMIT ${param_count}"
            params.append(limit)
            
            async with pool.acquire() as conn:
                rows = await conn.fetch(sql_query, *params)
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"Filter search error: {e}")
            return []
    
    
    async def _parse_query_with_claude(self, query: str) -> Dict[str, Any]:
        """Use Claude to parse natural language query into structured filters"""
        try:
            prompt = f"""Parse this vehicle search query into structured filters.
Extract: brand, model, year_min, year_max, price_max_usd, transmission, location, color.

Query: "{query}"

Respond with ONLY a JSON object, no explanation:
{{"brand": "Toyota", "year_min": 2018, "price_max_usd": 35000}}"""

            response = await self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            import json
            text = response.content[0].text
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
            
        except Exception as e:
            print(f"Query parsing error: {e}")
            return {}
