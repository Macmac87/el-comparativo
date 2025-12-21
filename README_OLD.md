# CarSearch VE - Venezuelan Vehicle Search Aggregator with RAG

## Overview
B2C platform that aggregates vehicle listings from multiple Venezuelan platforms with conversational search powered by RAG (Retrieval-Augmented Generation).

## Architecture

### Tech Stack
- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind CSS
- **Backend**: FastAPI + Python 3.11
- **Database**: PostgreSQL 15 + pgvector extension
- **RAG**: OpenAI Embeddings + Vector Search (from RAGFIN1)
- **Scrapers**: Playwright + BeautifulSoup4
- **Cache/Queue**: Redis
- **Hosting**: Render (backend) + Vercel (frontend)

### Core Components

#### 1. Web Scrapers
- **TuCarro.com** - Primary source
- **MercadoLibre Venezuela** - Secondary source
- **Demotores** - Tertiary source
- Scheduled runs every 6 hours
- Rate limiting & proxy rotation

#### 2. Data Pipeline
```
Scraper → Raw Data → Parser → Normalizer → PostgreSQL
                                              ↓
                                        Vector Embeddings
                                              ↓
                                        pgvector Index
```

#### 3. RAG Integration (from RAGFIN1)
- **Embeddings Model**: text-embedding-3-small (OpenAI)
- **Vector DB**: pgvector extension in PostgreSQL
- **Retrieval**: Semantic search + metadata filtering
- **LLM**: GPT-4 or Claude for query understanding

#### 4. Search Interface
- Traditional filters (marca, modelo, año, precio)
- **Conversational search** (RAG-powered)
- Side-by-side comparison
- Price alerts & saved searches

## Database Schema

```sql
-- Main vehicles table
CREATE TABLE vehicles (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    external_id VARCHAR(255) UNIQUE,
    brand VARCHAR(100),
    model VARCHAR(100),
    year INTEGER,
    price_usd DECIMAL(10,2),
    price_bs DECIMAL(15,2),
    mileage INTEGER,
    transmission VARCHAR(50),
    fuel_type VARCHAR(50),
    color VARCHAR(50),
    location VARCHAR(100),
    description TEXT,
    images JSONB,
    contact JSONB,
    url TEXT,
    embedding vector(1536),  -- OpenAI embeddings dimension
    scraped_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- Indexes
CREATE INDEX idx_vehicles_brand ON vehicles(brand);
CREATE INDEX idx_vehicles_model ON vehicles(model);
CREATE INDEX idx_vehicles_year ON vehicles(year);
CREATE INDEX idx_vehicles_price_usd ON vehicles(price_usd);
CREATE INDEX idx_vehicles_location ON vehicles(location);
CREATE INDEX idx_vehicles_embedding ON vehicles USING ivfflat (embedding vector_cosine_ops);

-- User searches (for analytics & improvement)
CREATE TABLE searches (
    id SERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    user_ip VARCHAR(50),
    results_count INTEGER,
    clicked_vehicle_id INTEGER REFERENCES vehicles(id),
    created_at TIMESTAMP DEFAULT NOW()
);
```

## RAG Implementation

### 1. Vector Embeddings Generation
```python
from openai import OpenAI

def generate_embedding(text: str) -> list[float]:
    """Generate embeddings for vehicle descriptions"""
    client = OpenAI()
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def prepare_vehicle_text(vehicle: dict) -> str:
    """Combine vehicle fields for embedding"""
    return f"""
    Marca: {vehicle['brand']}
    Modelo: {vehicle['model']}
    Año: {vehicle['year']}
    Precio: ${vehicle['price_usd']:,.0f}
    Transmisión: {vehicle['transmission']}
    Combustible: {vehicle['fuel_type']}
    Color: {vehicle['color']}
    Ubicación: {vehicle['location']}
    Kilometraje: {vehicle['mileage']:,} km
    Descripción: {vehicle['description']}
    """
```

### 2. Semantic Search
```python
async def semantic_search(query: str, limit: int = 20) -> list[dict]:
    """RAG-powered vehicle search"""
    
    # 1. Generate query embedding
    query_embedding = generate_embedding(query)
    
    # 2. Vector similarity search
    results = await db.fetch("""
        SELECT 
            v.*,
            1 - (v.embedding <=> $1::vector) as similarity
        FROM vehicles v
        WHERE v.is_active = true
        ORDER BY v.embedding <=> $1::vector
        LIMIT $2
    """, query_embedding, limit)
    
    return results
```

### 3. Conversational Query Parser
```python
async def parse_natural_query(query: str) -> dict:
    """Use LLM to extract structured filters from natural language"""
    
    prompt = f"""
Extract vehicle search parameters from this query in Spanish:
"{query}"

Return JSON with these fields (null if not mentioned):
- brand: string
- model: string
- year_min: int
- year_max: int
- price_max_usd: int
- transmission: "Manual" | "Automática"
- fuel_type: string
- color: string
- location: string

Example: "Busco Toyota 4Runner 2018-2020 blanca menos de 35 mil dolares"
Output: {{"brand": "Toyota", "model": "4Runner", "year_min": 2018, "year_max": 2020, "price_max_usd": 35000, "color": "blanca"}}
"""
    
    # Call GPT-4/Claude for structured extraction
    # Combine with vector search for best results
```

## Scraper Architecture

### TuCarro Scraper
```python
# scrapers/tucarro.py
import asyncio
from playwright.async_api import async_playwright

async def scrape_tucarro(max_pages: int = 10) -> list[dict]:
    """Scrape vehicle listings from TuCarro"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        vehicles = []
        
        for page_num in range(1, max_pages + 1):
            url = f"https://www.tucarro.com.ve/carros/usados?page={page_num}"
            await page.goto(url, wait_until="domcontentloaded")
            
            # Extract listings
            listings = await page.query_selector_all(".ui-search-result")
            
            for listing in listings:
                vehicle = await extract_vehicle_data(listing)
                vehicles.append(vehicle)
            
            await asyncio.sleep(2)  # Rate limiting
        
        await browser.close()
        return vehicles
```

## API Endpoints

```
POST   /api/search              - Conversational search (RAG)
GET    /api/vehicles             - List with filters
GET    /api/vehicles/:id         - Single vehicle details
POST   /api/alerts               - Create price alert
GET    /api/brands               - Available brands
GET    /api/models/:brand        - Models for brand
```

## MVP Timeline (2-3 weeks)

### Week 1: Backend + Scraping
- [ ] FastAPI project setup
- [ ] PostgreSQL + pgvector setup
- [ ] TuCarro scraper (working)
- [ ] MercadoLibre scraper (working)
- [ ] Data normalization pipeline
- [ ] Generate embeddings for initial dataset

### Week 2: RAG + API
- [ ] RAG search implementation
- [ ] Natural query parser (LLM integration)
- [ ] REST API endpoints
- [ ] Hybrid search (vector + filters)
- [ ] Deploy backend to Render

### Week 3: Frontend
- [ ] Next.js setup
- [ ] Search interface (conversational + traditional)
- [ ] Vehicle cards & detail view
- [ ] Comparison feature
- [ ] Deploy to Vercel

## Monetization (B2C)

### Free Tier
- 5 searches per day
- Basic filters
- No alerts

### Premium ($7.99/month)
- Unlimited searches
- Price drop alerts
- Saved searches
- Priority support
- Ad-free experience

### Payment Integration
- Zinli (primary for Venezuela)
- PayPal (international)
- Crypto (USDT via Binance P2P)

## Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:pass@host:5432/carsearch_ve

# OpenAI (for RAG)
OPENAI_API_KEY=sk-...

# Anthropic (alternative)
ANTHROPIC_API_KEY=sk-ant-...

# Redis
REDIS_URL=redis://localhost:6379

# Scraping
PROXY_URL=http://proxy:port
USER_AGENT=Mozilla/5.0...

# Frontend
NEXT_PUBLIC_API_URL=https://api.carsearch.ve
```

## Key Differentiators

1. **Conversational Search**: "Busco pickup diesel menos de 20 mil" → Results
2. **Multi-platform Aggregation**: One search across all platforms
3. **RAG Intelligence**: Understands context & user intent
4. **Real-time Alerts**: Price drops & new matches
5. **Venezuelan-optimized**: Dual currency, local locations, WhatsApp integration

## Technical Challenges & Solutions

### Challenge 1: Scraping Reliability
**Solution**: Headless browsers (Playwright), retry logic, multiple fallback selectors

### Challenge 2: Data Inconsistency
**Solution**: Robust parsers, fuzzy matching for brands/models, manual mapping tables

### Challenge 3: Venezuela Infrastructure
**Solution**: Lightweight deployments, aggressive caching, CDN for images

### Challenge 4: Rate Limits
**Solution**: Respectful scraping (delays), proxy rotation if needed, cache aggressively

## Next Steps

1. **Today**: Set up project structure, database schema, first scraper
2. **Tomorrow**: RAG integration, embeddings generation, search API
3. **Day 3**: Frontend basics, deploy MVP
4. **Day 4+**: Iterate based on real usage data

---

**Status**: Ready to start development
**Target Launch**: 3 weeks from today
**Initial Dataset Goal**: 500-1000 vehicles across 2-3 platforms
