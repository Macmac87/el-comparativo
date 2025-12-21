# CarSearch VE - Getting Started Guide

## 🚀 Quick Start (Local Development)

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (for frontend)
- OpenAI API Key
- Anthropic API Key

### 1. Clone and Setup

```bash
# Create project directory
mkdir carsearch_ve
cd carsearch_ve

# Copy backend files
# (Files should be in backend/ directory)

# Copy environment variables
cd backend
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

### 2. Start Services with Docker

```bash
# Start PostgreSQL + Redis + Backend
docker-compose up -d

# Check logs
docker-compose logs -f backend
```

### 3. Initialize Database

```bash
# The database will auto-initialize on first run
# Check that tables were created:
docker-compose exec postgres psql -U carsearch -d carsearch_ve -c "\dt"

# You should see:
# - vehicles
# - searches
# - alerts
```

### 4. Run Your First Scrape

```bash
# Enter backend container
docker-compose exec backend bash

# Run TuCarro scraper
python -m scrapers.tucarro

# Or use Python directly
python3 <<EOF
import asyncio
from scrapers.tucarro import TuCarroScraper
from database import init_db, get_db_pool
from rag import RAGSearchEngine

async def main():
    # Initialize database
    await init_db()
    
    # Scrape TuCarro
    async with TuCarroScraper() as scraper:
        vehicles = await scraper.scrape(max_pages=3)
    
    print(f"Scraped {len(vehicles)} vehicles")
    
    # Save to database and generate embeddings
    pool = get_db_pool()
    rag = RAGSearchEngine()
    
    for vehicle in vehicles:
        # Generate embedding
        embedding = await rag.embed_vehicle(vehicle)
        
        # Insert into database
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO vehicles (
                    source, external_id, brand, model, year,
                    price_usd, location, description, images, url, embedding
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (external_id) DO NOTHING
            """, 
                vehicle['source'],
                vehicle['external_id'],
                vehicle['brand'],
                vehicle['model'],
                vehicle['year'],
                vehicle['price_usd'],
                vehicle['location'],
                vehicle['description'],
                vehicle['images'],
                vehicle['url'],
                embedding
            )
    
    print("✅ Vehicles saved to database with embeddings")

asyncio.run(main())
EOF
```

### 5. Test RAG Search

```bash
# Test conversational search
curl -X POST http://localhost:8000/api/search/conversational \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Busco Toyota 4Runner 2018-2020 blanca menos de 35 mil dólares",
    "limit": 10
  }'
```

### 6. Access API Documentation

Open browser: http://localhost:8000/docs

You'll see Swagger UI with all endpoints.

---

## 📁 Project Structure

```
carsearch_ve/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── rag.py                  # RAG search engine
│   ├── database.py             # Database utilities
│   ├── models.py               # Pydantic models
│   ├── scrapers/
│   │   ├── tucarro.py         # TuCarro scraper
│   │   ├── mercadolibre.py    # MercadoLibre scraper (TODO)
│   │   └── demotores.py       # Demotores scraper (TODO)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env
├── frontend/                   # Next.js app (TODO)
├── docker-compose.yml
└── README.md
```

---

## 🔧 Development Workflow

### Adding a New Scraper

1. Create scraper file in `backend/scrapers/`
2. Implement scraping logic (see `tucarro.py` as template)
3. Return list of vehicle dictionaries matching schema
4. Add to scheduled tasks

### Testing RAG Search

```python
import asyncio
from rag import RAGSearchEngine
from database import init_db

async def test_search():
    await init_db()
    rag = RAGSearchEngine()
    
    # Test natural language search
    results = await rag.search(
        query="Camioneta Toyota 4x4 menos de 30 mil",
        limit=5
    )
    
    for i, vehicle in enumerate(results, 1):
        print(f"\n{i}. {vehicle['brand']} {vehicle['model']} ({vehicle['year']})")
        print(f"   ${vehicle['price_usd']:,.0f}")
        print(f"   Similarity: {vehicle.get('similarity_score', 0):.2%}")

asyncio.run(test_search())
```

### Regenerating Embeddings

If you change the embedding model or add new fields:

```python
import asyncio
from rag import RAGSearchEngine
from database import init_db

async def reindex():
    await init_db()
    rag = RAGSearchEngine()
    await rag.reindex_all_vehicles()

asyncio.run(reindex())
```

---

## 🚀 Deployment (Production)

### Option 1: Render (Recommended)

**Backend:**
1. Create new Web Service on Render
2. Connect your GitHub repo
3. Build Command: `pip install -r requirements.txt && playwright install chromium`
4. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables from `.env.example`

**Database:**
1. Create PostgreSQL database on Render
2. Enable pgvector extension:
   ```sql
   CREATE EXTENSION vector;
   ```
3. Copy connection string to `DATABASE_URL`

**Redis:**
1. Use Render Redis or external service (Redis Cloud, Upstash)
2. Copy connection string to `REDIS_URL`

### Option 2: Railway

Similar to Render, Railway has good PostgreSQL + Redis support.

### Option 3: Self-hosted VPS

```bash
# On your VPS (Ubuntu 22.04+)
git clone your-repo
cd carsearch_ve

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Create .env file with production values
nano backend/.env

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Setup nginx reverse proxy
# Setup SSL with Let's Encrypt
```

---

## 🔐 Environment Variables (Production)

```env
# Database (use managed PostgreSQL)
DATABASE_URL=postgresql://user:pass@host:5432/db

# API Keys
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...

# Redis (use managed Redis)
REDIS_URL=redis://default:password@host:6379

# Frontend
FRONTEND_URL=https://carsearch.ve

# Security
API_KEY=your-secure-api-key-here

# Monitoring
SENTRY_DSN=https://...

# Email (for alerts)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=noreply@carsearch.ve
SMTP_PASSWORD=your-app-password
```

---

## 📊 Monitoring & Maintenance

### Database Maintenance

```sql
-- Check database size
SELECT pg_size_pretty(pg_database_size('carsearch_ve'));

-- Check table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Vacuum and analyze
VACUUM ANALYZE vehicles;

-- Rebuild vector index if needed
REINDEX INDEX idx_vehicles_embedding;
```

### Scraper Schedule

Set up cron job or Celery Beat:

```python
# tasks.py (Celery)
from celery import Celery
from celery.schedules import crontab

app = Celery('tasks', broker='redis://localhost:6379')

@app.task
def scrape_tucarro():
    # Run scraper
    pass

@app.task
def scrape_mercadolibre():
    # Run scraper
    pass

# Schedule: every 6 hours
app.conf.beat_schedule = {
    'scrape-tucarro': {
        'task': 'tasks.scrape_tucarro',
        'schedule': crontab(hour='*/6'),
    },
    'scrape-mercadolibre': {
        'task': 'tasks.scrape_mercadolibre',
        'schedule': crontab(hour='*/6'),
    },
}
```

---

## 🐛 Troubleshooting

### "psycopg2.OperationalError: could not connect to server"

Check DATABASE_URL is correct and PostgreSQL is running:
```bash
docker-compose ps
docker-compose logs postgres
```

### "openai.error.AuthenticationError"

Check OPENAI_API_KEY in .env file is valid.

### Scrapers not finding elements

Websites change their HTML structure. Update selectors in scraper files.

### Vector search returns no results

Check embeddings were generated:
```sql
SELECT COUNT(*) FROM vehicles WHERE embedding IS NOT NULL;
```

If 0, run reindexing script.

---

## 📈 Next Steps

1. **Complete MercadoLibre scraper** (similar to TuCarro)
2. **Build Next.js frontend** with conversational search UI
3. **Add user authentication** (JWT tokens)
4. **Implement price alerts** (email notifications)
5. **Add caching layer** (Redis for frequent searches)
6. **Create admin panel** (monitor scrapers, view stats)
7. **Optimize vector index** (tune IVFFlat parameters)
8. **Add more scrapers** (Demotores, Facebook Marketplace)
9. **Mobile app** (React Native)
10. **Analytics dashboard** (search patterns, popular brands)

---

## 🎯 MVP Checklist

Week 1:
- [x] Backend structure
- [x] Database schema with pgvector
- [x] RAG search engine
- [x] TuCarro scraper
- [ ] MercadoLibre scraper
- [ ] Scheduled scraping (Celery)

Week 2:
- [ ] Complete API endpoints
- [ ] Authentication (optional for MVP)
- [ ] Deploy backend to Render
- [ ] Test with 500+ vehicles

Week 3:
- [ ] Next.js frontend
- [ ] Search interface (conversational + filters)
- [ ] Vehicle detail pages
- [ ] Deploy frontend to Vercel
- [ ] Launch MVP! 🚀

---

**Ready to build?** Start with:
```bash
docker-compose up -d
docker-compose logs -f backend
```

Then visit http://localhost:8000/docs to explore the API!
