"""
RAG Search Engine for El Comparativo
Semantic vehicle search using embeddings and pgvector
TEMPORARY: OpenAI disabled
"""

import os
from typing import List, Dict, Any, Optional
from anthropic import AsyncAnthropic

from database import get_db_pool


class RAGSearchEngine:
    """RAG-powered vehicle search engine"""
    
    def __init__(self):
        """Initialize RAG engine"""
        # Anthropic client for conversational search
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        self.anthropic_client = AsyncAnthropic(api_key=anthropic_key)
        
        # OpenAI temporarily disabled - will add later
        self.openai_client = None
        print("⚠️  RAG engine initialized WITHOUT OpenAI (embeddings disabled)")
    
    
    async def search(
        self,
        query: str,
        limit: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search vehicles using conversational query
        Currently uses filters only (embeddings disabled)
        """
        try:
            pool = get_db_pool()
            
            # Parse query with Claude to extract filters
            parsed = await self._parse_query_with_claude(query)
            
            # Merge with explicit filters
            if filters:
                parsed.update(filters)
            
            # Build SQL query from parsed filters
            sql_query = "SELECT * FROM vehicles WHERE is_active = true"
            params = []
            param_count = 1
            
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
            
            sql_query += f" ORDER BY updated_at DESC LIMIT ${param_count}"
            params.append(limit)
            
            # Execute query
            async with pool.acquire() as conn:
                rows = await conn.fetch(sql_query, *params)
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            print(f"RAG search error: {e}")
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
            
            # Extract JSON from response
            import json
            text = response.content[0].text
            # Remove markdown code blocks if present
            text = text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
            
        except Exception as e:
            print(f"Query parsing error: {e}")
            return {}
