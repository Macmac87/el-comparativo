# CarSearch VE - Complete Technical Specification

## Executive Summary

**Product:** B2C vehicle search aggregator for Venezuela with AI-powered conversational search

**Target Market:** Venezuelan car buyers looking across multiple listing platforms

**Core Technology:** RAG (Retrieval-Augmented Generation) with pgvector semantic search

**MVP Timeline:** 3 weeks

**Initial Scale:** 500-1,000 vehicles across 2-3 platforms

---

## Technical Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│  Next.js 14 + TypeScript + Tailwind CSS (Vercel)           │
│  - Conversational search interface                          │
│  - Traditional filters                                       │
│  - Vehicle comparison                                        │
└────────────────────┬────────────────────────────────────────┘
                     │ REST API
┌────────────────────┴────────────────────────────────────────┐
│                      Backend (Render)                        │
│  FastAPI + Python 3.11                                       │
│  - RAG Search Engine (OpenAI + Anthropic)                   │
│  - Vehicle scrapers (Playwright)                            │
│  - API endpoints                                             │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────┴────────────────────────────────────────┐
│              Data Layer                                      │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  PostgreSQL 15   │  │   Redis 7        │                │
│  │  + pgvector      │  │   (cache/queue)  │                │
│  │  (Main DB)       │  │                  │                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. Scraping Pipeline:
   Scrapers → Raw HTML → Parser → Normalizer → PostgreSQL
                                                    ↓
                                              Generate Embeddings
                                                    ↓
                                              Store in pgvector

2. Search Pipeline:
   User Query → LLM Filter Extraction → Generate Query Embedding
                                              ↓
                                    Vector Similarity Search
                                              ↓
                                      Apply Additional Filters
                                              ↓
                                    Rank & Return Results
```

---

## Database Schema

### Primary Tables

#### vehicles
```sql
CREATE TABLE vehicles (
    id SERIAL PRIMARY KEY,
    
    -- Source info
    source VARCHAR(50) NOT NULL,              -- 'tucarro', 'mercadolibre', etc
    external_id VARCHAR(255) UNIQUE,          -- Platform's ID
    
    -- Vehicle details
    brand VARCHAR(100),                       -- Toyota, Ford, etc
    model VARCHAR(100),                       -- 4Runner, F-150, etc
    year INTEGER,                             -- 2018, 2019, etc
    
    -- Pricing
    price_usd DECIMAL(10,2),                  -- Primary price in USD
    price_bs DECIMAL(15,2),                   -- Optional Bs price
    
    -- Specifications
    mileage INTEGER,                          -- Kilometers
    transmission VARCHAR(50),                 -- Manual, Automática
    fuel_type VARCHAR(50),                    -- Gasolina, Diesel
    color VARCHAR(50),                        -- Blanco, Negro, etc
    
    -- Location & description
    location VARCHAR(100),                    -- Caracas, Maracaibo, etc
    description TEXT,                         -- Full listing description
    
    -- Media & contact
    images JSONB,                             -- ["url1", "url2", ...]
    contact JSONB,                            -- {phone, whatsapp, email}
    url TEXT,                                 -- Link to original listing
    
    -- RAG components
    embedding vector(1536),                   -- OpenAI embedding
    
    -- Metadata
    scraped_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    
    -- Constraints
    CONSTRAINT valid_year CHECK (year >= 1900 AND year <= 2030),
    CONSTRAINT valid_price CHECK (price_usd >= 0)
);

-- Indexes
CREATE INDEX idx_vehicles_brand ON vehicles(brand);
CREATE INDEX idx_vehicles_model ON vehicles(model);
CREATE INDEX idx_vehicles_year ON vehicles(year);
CREATE INDEX idx_vehicles_price_usd ON vehicles(price_usd);
CREATE INDEX idx_vehicles_location ON vehicles(location);
CREATE INDEX idx_vehicles_source ON vehicles(source);
CREATE INDEX idx_vehicles_active ON vehicles(is_active);
CREATE INDEX idx_vehicles_updated ON vehicles(updated_at);

-- Vector index (critical for RAG performance)
CREATE INDEX idx_vehicles_embedding ON vehicles 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

#### searches (analytics)
```sql
CREATE TABLE searches (
    id SERIAL PRIMARY KEY,
    query TEXT NOT NULL,
    filters JSONB,                            -- Extracted filters
    user_ip VARCHAR(50),                      -- For rate limiting
    results_count INTEGER,
    clicked_vehicle_id INTEGER REFERENCES vehicles(id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_searches_created ON searches(created_at);
CREATE INDEX idx_searches_clicked ON searches(clicked_vehicle_id);
```

#### alerts (future feature)
```sql
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255) NOT NULL,
    query TEXT NOT NULL,
    filters JSONB,
    max_price_usd DECIMAL(10,2),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    last_checked TIMESTAMP,
    last_notified TIMESTAMP
);

CREATE INDEX idx_alerts_active ON alerts(is_active);
CREATE INDEX idx_alerts_user ON alerts(user_email);
CREATE INDEX idx_alerts_checked ON alerts(last_checked);
```

---

## RAG Implementation Details

### 1. Text Preparation

**Purpose:** Convert structured vehicle data into natural language text for embedding

```python
def prepare_vehicle_text(vehicle: dict) -> str:
    """
    Combines all searchable fields into coherent text
    
    Strategy:
    - Include all searchable attributes
    - Use natural Spanish language
    - Keep descriptions concise (<500 chars)
    - Format consistently for better embeddings
    """
    parts = [
        f"Marca: {vehicle['brand']}",
        f"Modelo: {vehicle['model']}",
        f"Año: {vehicle['year']}",
        f"Precio: ${vehicle['price_usd']:,.0f} USD",
        f"Transmisión: {vehicle['transmission']}",
        f"Combustible: {vehicle['fuel_type']}",
        f"Color: {vehicle['color']}",
        f"Ubicación: {vehicle['location']}",
        f"Kilometraje: {vehicle['mileage']:,} km",
        f"Descripción: {vehicle['description'][:500]}"
    ]
    
    return "\n".join(p for p in parts if p.split(": ")[1])
```

### 2. Embedding Generation

**Model:** OpenAI text-embedding-3-small
- **Dimensions:** 1536
- **Cost:** $0.00002 per 1K tokens
- **Performance:** Best price/performance ratio
- **Language:** Excellent Spanish support

```python
async def generate_embedding(text: str) -> List[float]:
    """
    Generate 1536-dimensional embedding vector
    
    Cost per vehicle: ~$0.000004 (200 tokens avg)
    For 10K vehicles: ~$0.04 total
    """
    response = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding
```

### 3. Query Understanding (LLM)

**Model:** Claude 3.5 Sonnet (faster & cheaper than GPT-4)
- **Cost:** ~$0.0003 per search
- **Latency:** 200-500ms
- **Accuracy:** >95% filter extraction

```python
async def extract_filters_from_query(query: str) -> dict:
    """
    Convert natural language to structured filters
    
    Input:  "Busco Toyota 4Runner 2018-2020 blanca menos de 35 mil"
    Output: {
        "brand": "Toyota",
        "model": "4Runner",
        "year_min": 2018,
        "year_max": 2020,
        "color": "blanca",
        "price_max_usd": 35000
    }
    """
    prompt = """
    Extrae parámetros de búsqueda de esta consulta en español.
    
    Consulta: "{query}"
    
    Devuelve JSON con: brand, model, year_min, year_max, 
    price_max_usd, transmission, fuel_type, color, location
    
    Usa null si no se menciona explícitamente.
    """
    
    response = await anthropic_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return json.loads(response.content[0].text)
```

### 4. Semantic Search

**Algorithm:** Cosine similarity with pgvector

```python
async def semantic_search(
    query_embedding: List[float],
    filters: dict,
    limit: int = 20
) -> List[dict]:
    """
    Hybrid search: semantic + filters
    
    Performance:
    - Without index: O(n) - slow for 10K+ vehicles
    - With IVFFlat: O(log n) - fast even for 100K+ vehicles
    
    Query time: 10-50ms with proper indexing
    """
    sql = """
        SELECT 
            *,
            1 - (embedding <=> $1::vector) as similarity_score
        FROM vehicles
        WHERE is_active = true
          AND ($2::text IS NULL OR LOWER(brand) = LOWER($2))
          AND ($3::int IS NULL OR year >= $3)
          AND ($4::int IS NULL OR year <= $4)
          AND ($5::decimal IS NULL OR price_usd <= $5)
        ORDER BY embedding <=> $1::vector
        LIMIT $6
    """
    
    return await db.fetch(sql, 
        query_embedding,
        filters.get("brand"),
        filters.get("year_min"),
        filters.get("year_max"),
        filters.get("price_max_usd"),
        limit
    )
```

### 5. Result Ranking

**Scoring Strategy:**

```
Final Score = (0.6 × Semantic Similarity) + (0.4 × Filter Match)

Where:
- Semantic Similarity: Cosine distance (0-1)
- Filter Match: Boolean score for each matched filter

Example:
Vehicle A: similarity=0.85, matches 4/5 filters = 0.85×0.6 + 0.8×0.4 = 0.83
Vehicle B: similarity=0.90, matches 2/5 filters = 0.90×0.6 + 0.4×0.4 = 0.70
→ Rank A higher (better overall match)
```

---

## Web Scraping Strategy

### Target Platforms (Priority Order)

1. **TuCarro.com.ve** (Primary)
   - Most popular in Venezuela
   - Clean HTML structure
   - USD pricing standard
   - ~10,000+ active listings

2. **MercadoLibre.com.ve** (Secondary)
   - Largest overall marketplace
   - Vehicle section active
   - Mixed USD/Bs pricing
   - ~5,000+ vehicle listings

3. **Demotores.com.ve** (Tertiary)
   - Dealer-focused
   - Professional listings
   - Consistent data quality
   - ~2,000+ listings

### Scraping Architecture

```python
class VehicleScraper:
    """Base class for all scrapers"""
    
    async def scrape(self, max_pages: int) -> List[dict]:
        """Main scraping method"""
        pass
    
    async def scrape_detail(self, url: str) -> dict:
        """Get additional details from listing page"""
        pass
    
    def normalize_data(self, raw: dict) -> dict:
        """Convert platform-specific data to standard format"""
        pass
```

### Scraping Best Practices

**1. Respectful Scraping:**
```python
# Rate limiting
await asyncio.sleep(2)  # 2 seconds between requests

# User agent rotation
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
]

# Respect robots.txt
# Check rate limits
# Handle errors gracefully
```

**2. Error Handling:**
```python
try:
    vehicle = await scrape_listing(url)
except TimeoutError:
    logger.warning(f"Timeout scraping {url}")
except Exception as e:
    logger.error(f"Failed to scrape {url}: {e}")
    # Continue with next listing
```

**3. Data Validation:**
```python
def validate_vehicle(vehicle: dict) -> bool:
    """Ensure scraped data is usable"""
    required = ["brand", "model", "year", "price_usd", "url"]
    
    # Check required fields
    if not all(vehicle.get(field) for field in required):
        return False
    
    # Validate ranges
    if not (1900 <= vehicle["year"] <= 2030):
        return False
    
    if vehicle["price_usd"] <= 0:
        return False
    
    return True
```

### Scheduling Strategy

```python
# Celery Beat schedule
from celery.schedules import crontab

CELERYBEAT_SCHEDULE = {
    'scrape-tucarro': {
        'task': 'scrapers.scrape_tucarro',
        'schedule': crontab(hour='*/6'),  # Every 6 hours
        'args': (10,)  # max_pages
    },
    'scrape-mercadolibre': {
        'task': 'scrapers.scrape_mercadolibre',
        'schedule': crontab(hour='*/6'),
        'args': (10,)
    },
    'cleanup-old-listings': {
        'task': 'tasks.cleanup_old',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
    },
    'reindex-embeddings': {
        'task': 'tasks.reindex_new_vehicles',
        'schedule': crontab(hour='*/6'),  # After scraping
    }
}
```

---

## API Specification

### Endpoints

#### POST /api/search/conversational
**RAG-powered conversational search**

Request:
```json
{
  "query": "Busco Toyota 4Runner 2018-2020 blanca menos de 35 mil dólares",
  "limit": 20
}
```

Response:
```json
{
  "query": "Busco Toyota 4Runner 2018-2020...",
  "total_results": 15,
  "extracted_filters": {
    "brand": "Toyota",
    "model": "4Runner",
    "year_min": 2018,
    "year_max": 2020,
    "color": "blanca",
    "price_max_usd": 35000
  },
  "search_type": "conversational_rag",
  "vehicles": [
    {
      "id": 123,
      "brand": "Toyota",
      "model": "4Runner",
      "year": 2019,
      "price_usd": 32500,
      "color": "Blanco",
      "location": "Caracas",
      "mileage": 45000,
      "images": ["url1", "url2"],
      "url": "https://tucarro.com.ve/...",
      "similarity_score": 0.92
    }
  ]
}
```

#### POST /api/search
**Traditional filter-based search**

Request:
```json
{
  "brand": "Toyota",
  "year_min": 2018,
  "year_max": 2020,
  "price_max_usd": 35000,
  "limit": 20
}
```

#### GET /api/vehicles/{id}
**Get single vehicle details**

#### GET /api/brands
**List all available brands with counts**

#### GET /api/models/{brand}
**List models for a specific brand**

#### GET /api/stats
**Platform statistics**

---

## Performance Optimization

### Database Optimization

**1. Proper Indexing:**
```sql
-- B-tree indexes for exact matches
CREATE INDEX idx_vehicles_brand ON vehicles(brand);

-- Partial index for active listings
CREATE INDEX idx_vehicles_active_updated 
ON vehicles(updated_at) 
WHERE is_active = true;

-- Vector index tuning based on dataset size
-- lists = sqrt(total_rows)
CREATE INDEX idx_vehicles_embedding 
ON vehicles USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);  -- For ~10K vehicles
```

**2. Query Optimization:**
```sql
-- Use prepared statements
PREPARE search_vehicles AS
SELECT * FROM vehicles
WHERE brand = $1 AND year >= $2
ORDER BY embedding <=> $3::vector
LIMIT $4;

-- Execute multiple times efficiently
EXECUTE search_vehicles('Toyota', 2018, $embedding, 20);
```

**3. Connection Pooling:**
```python
# asyncpg pool (from database.py)
pool = await asyncpg.create_pool(
    DATABASE_URL,
    min_size=5,    # Minimum connections
    max_size=20,   # Maximum connections
    max_queries=50000,
    command_timeout=60
)
```

### Caching Strategy

**1. Redis Caching:**
```python
# Cache popular searches
cache_key = f"search:{query_hash}"
cached = await redis.get(cache_key)

if cached:
    return json.loads(cached)

# Perform search
results = await search(query)

# Cache for 1 hour
await redis.setex(cache_key, 3600, json.dumps(results))
```

**2. Embedding Caching:**
```python
# Cache query embeddings
@lru_cache(maxsize=1000)
def get_cached_embedding(query: str) -> List[float]:
    return generate_embedding(query)
```

**3. Database Query Caching:**
```python
# Cache expensive aggregations
brands = await redis.get("brands_list")
if not brands:
    brands = await db.fetch("SELECT DISTINCT brand...")
    await redis.setex("brands_list", 3600, json.dumps(brands))
```

---

## Deployment Architecture

### Production Stack (Render)

```
┌─────────────────────────────────────────────┐
│              Load Balancer (Render)          │
└────────────────┬────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
┌───────▼───────┐  ┌──────▼──────┐
│  Web Service  │  │  Web Service │
│  (FastAPI)    │  │  (FastAPI)   │
│  Auto-scale   │  │  Auto-scale  │
└───────┬───────┘  └──────┬───────┘
        │                 │
        └────────┬────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
┌───▼───┐   ┌───▼───┐   ┌───▼───┐
│ PostgreSQL │  │ Redis │  │ Celery │
│ (Managed) │  │(Redis  │  │Worker │
│           │  │Cloud) │  │       │
└───────────┘  └───────┘  └───────┘
```

### Environment Variables (Production)

```env
# Database
DATABASE_URL=postgresql://user:pass@host.render.com/db
DATABASE_POOL_SIZE=20

# AI APIs
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...

# Redis
REDIS_URL=redis://default:pass@redis-cloud.com:6379

# Security
API_SECRET_KEY=your-256-bit-secret
CORS_ORIGINS=https://carsearch.ve,https://www.carsearch.ve

# Features
ENABLE_SCRAPING=true
SCRAPER_MAX_PAGES=20
SCRAPER_SCHEDULE=0 */6 * * *  # Every 6 hours

# Monitoring
SENTRY_DSN=https://...
LOG_LEVEL=INFO

# Email (alerts)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG....
FROM_EMAIL=noreply@carsearch.ve
```

---

## Cost Estimation

### Infrastructure (Monthly)

**Render (Backend):**
- Web Service: $25/month (Starter)
- PostgreSQL: $7/month (Starter)
- Redis Cloud: $0/month (Free tier) or $5/month

**Vercel (Frontend):**
- Free tier (hobby projects)
- Pro: $20/month (if needed)

**Total Infrastructure: ~$32-57/month**

### AI API Costs

**Embeddings (OpenAI):**
- 10,000 vehicles × 200 tokens = 2M tokens
- Initial: $0.04
- Daily updates (100 new): $0.004/day = $0.12/month

**Query Understanding (Anthropic):**
- 1,000 searches/day × $0.0003 = $0.30/day
- Monthly: $9/month

**Total AI Costs: ~$10/month**

### Total Monthly: ~$42-67

For 1,000 daily searches serving Venezuelan car buyers!

---

## Success Metrics

### Technical Metrics

1. **Search Quality:**
   - Semantic relevance: >0.7 similarity score
   - Filter extraction accuracy: >95%
   - User clicks on top 3 results: >60%

2. **Performance:**
   - API response time: <500ms (p95)
   - Search latency: <1s (p95)
   - Uptime: >99.5%

3. **Data Quality:**
   - Active listings: >500
   - Data freshness: <6 hours old
   - Scraping success rate: >90%

### Business Metrics

1. **Engagement:**
   - Daily active users: 100+
   - Searches per user: 3+
   - Time on site: >5 minutes

2. **Conversion:**
   - Click-through rate: >40%
   - Contact attempts: >10%
   - Return users: >30%

---

## Launch Checklist

### Pre-Launch (3 Weeks)

**Week 1: Backend**
- [x] Database schema with pgvector
- [x] RAG search engine
- [x] TuCarro scraper
- [ ] MercadoLibre scraper
- [ ] Initial dataset (500+ vehicles)
- [ ] API endpoints
- [ ] Deploy to Render

**Week 2: Testing & Optimization**
- [ ] Test search quality
- [ ] Optimize vector indexes
- [ ] Add caching layer
- [ ] Error monitoring (Sentry)
- [ ] Load testing

**Week 3: Frontend**
- [ ] Next.js setup
- [ ] Search interface
- [ ] Vehicle cards
- [ ] Detail pages
- [ ] Deploy to Vercel

### Launch Day
- [ ] DNS configuration
- [ ] SSL certificates
- [ ] Analytics setup
- [ ] Error monitoring
- [ ] Backup strategy
- [ ] Go live! 🚀

---

**Ready to build? Let's execute.**
