# 🚗 El Comparativo

**Venezuelan Vehicle Search Aggregator with RAG-Powered Conversational Search**

[![Status](https://img.shields.io/badge/status-backend_complete-success)]()
[![Python](https://img.shields.io/badge/python-3.11-blue)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green)]()
[![License](https://img.shields.io/badge/license-MIT-blue)]()

---

## 📖 Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Deployment](#deployment)
- [Project Status](#project-status)
- [Documentation](#documentation)

---

## 🎯 Overview

**El Comparativo** is a B2C SaaS platform that aggregates vehicle listings from all major Venezuelan platforms and enables **conversational search** powered by RAG (Retrieval-Augmented Generation).

### The Problem
Venezuelan car buyers must manually search across multiple platforms:
- TuCarro.com.ve
- MercadoLibre.com.ve
- Autocosmos.com.ve
- Buscomiauto.com
- And more...

Each platform has different interfaces, inconsistent data, and no cross-platform comparison.

### The Solution
**One conversational search across ALL platforms:**

```
👤 User: "Busco Toyota 4Runner 2018-2020 blanca menos de 35 mil dólares"

🤖 El Comparativo:
   ✅ Searches 6 platforms simultaneously
   ✅ Understands natural language intent
   ✅ Returns semantically ranked results
   ✅ Shows side-by-side comparison
   ✅ Sends price drop alerts
```

---

## ✨ Features

### For End Users
- 🎯 **Conversational Search** - Ask in natural Spanish, no complex filters needed
- 🔍 **Multi-Platform Aggregation** - Search TuCarro, MercadoLibre, Autocosmos, and more at once
- 💰 **Price Alerts** - Get notified when matching vehicles drop in price
- 📊 **Smart Comparison** - Compare vehicles side-by-side with AI-powered insights
- ⭐ **Saved Searches** - Quick access to frequent searches
- 💳 **Freemium Model** - 5 searches/day free, unlimited for $7.99/month

### Technical Features
- 🧠 **RAG-Powered Search** - OpenAI embeddings + pgvector semantic search
- 🔐 **Complete Auth System** - JWT tokens, user management, subscription tiers
- 🤖 **6 Active Scrapers** - Covering 80%+ of Venezuelan online vehicle market
- 📊 **~16,000 Vehicles** - Complete, up-to-date inventory
- 🇻🇪 **Venezuela-Optimized** - Dual currency (USD/Bs), local locations, WhatsApp integration
- ⚡ **Fast Search** - <500ms response time with vector indexing

---

## 🏗️ Tech Stack

### Backend (✅ Complete)
```
Framework:     FastAPI 0.109
Language:      Python 3.11
Database:      PostgreSQL 15 + pgvector
Vector Search: OpenAI text-embedding-3-small
Auth:          JWT (python-jose)
Scraping:      Playwright + BeautifulSoup4
Cache:         Redis 7
Hosting:       Render
```

### Frontend (🔲 Pending)
```
Framework:     Next.js 14 (App Router)
Language:      TypeScript
Styling:       Tailwind CSS + shadcn/ui
Auth:          NextAuth.js
State:         Zustand
Animations:    Framer Motion
Hosting:       Vercel
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+ with pgvector
- Redis (optional, for caching)
- OpenAI API Key
- Anthropic API Key

### Local Development

```bash
# 1. Clone repository
git clone https://github.com/yourusername/el-comparativo.git
cd el-comparativo

# 2. Run setup script
chmod +x setup.sh
./setup.sh

# 3. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your API keys

# 4. Start services
docker-compose up -d  # PostgreSQL + Redis

# 5. Run API
cd backend
uvicorn main:app --reload

# 6. Access API
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Run Scrapers

```bash
# Scrape all platforms (~30 min, ~16K vehicles)
cd backend
python -m scrapers.master_scraper

# Or scrape individual platforms
python -m scrapers.tucarro
python -m scrapers.mercadolibre
```

---

## 🌐 Deployment

### Deploy to Render (Recommended)

**See:** [DEPLOY_GUIDE.md](DEPLOY_GUIDE.md) for complete instructions.

**Quick Deploy:**

1. Push to GitHub
2. Connect Render to your repo
3. Render auto-detects `render.yaml`
4. Set API keys in dashboard
5. Deploy! 🚀

**Cost:** $14/month (API $7 + DB $7)

---

## 📊 Project Status

### ✅ Completed (Backend)

**Authentication System** ✅
- [x] JWT-based authentication
- [x] User registration & login
- [x] Password hashing (bcrypt)
- [x] Refresh tokens
- [x] Protected routes
- [x] Subscription tiers (free/premium)
- [x] Usage tracking & rate limiting

**RAG Search Engine** ✅
- [x] OpenAI embeddings generation
- [x] pgvector semantic search
- [x] Claude-powered query understanding
- [x] Hybrid ranking (semantic + filters)
- [x] Batch embedding processing

**Web Scrapers** ✅
- [x] TuCarro.com.ve (~10,000 vehicles)
- [x] MercadoLibre.com.ve (~5,000 vehicles)
- [x] Autocosmos.com.ve (~700 vehicles)
- [x] Buscomiauto.com (~1,500 vehicles)
- [x] GrupoMultimarca (~800 vehicles)
- [x] UsaditosCars.com (~300 vehicles)

**Master Orchestrator** ✅
- [x] Parallel scraper execution
- [x] Automatic deduplication
- [x] Embedding generation pipeline
- [x] Database population
- [x] Error handling & logging

**API Endpoints** ✅
- [x] POST /api/auth/register
- [x] POST /api/auth/login
- [x] GET /api/auth/me
- [x] POST /api/search/conversational (RAG)
- [x] POST /api/search (traditional filters)
- [x] GET /api/vehicles/:id
- [x] GET /api/brands
- [x] GET /api/models/:brand
- [x] GET /api/stats

**Database Schema** ✅
- [x] users (with subscription management)
- [x] vehicles (with pgvector embeddings)
- [x] saved_searches
- [x] saved_vehicles
- [x] search_history
- [x] payments

### 🔲 Pending (Frontend)

**Landing Page** 🔲
- [ ] Hero section (minimalista/maximalista design)
- [ ] Features showcase
- [ ] Pricing tiers
- [ ] Dark theme with gradient accents

**Authentication UI** 🔲
- [ ] Login modal
- [ ] Signup modal
- [ ] Password recovery
- [ ] OAuth (Google/Facebook optional)

**Dashboard** 🔲
- [ ] Conversational search interface
- [ ] Vehicle cards with glassmorphism
- [ ] Comparison view
- [ ] Saved searches
- [ ] Price alerts
- [ ] User profile

**Mobile** 🔲
- [ ] Responsive design
- [ ] Touch-optimized
- [ ] Progressive Web App (PWA)

---

## 📈 Metrics & Performance

### Coverage
```
TuCarro:         ~10,000 vehicles (55%)
MercadoLibre:     ~5,000 vehicles (27%)
Autocosmos:         ~700 vehicles (4%)
Buscomiauto:      ~1,500 vehicles (8%)
Multimarca:         ~800 vehicles (4%)
UsaditosCars:       ~300 vehicles (2%)
──────────────────────────────────────
TOTAL:          ~18,300 vehicles (raw)
UNIQUE:         ~16,000 vehicles (after dedup)
```

### Performance
- **Search Latency:** <500ms (p95)
- **API Response:** <1s (p95)
- **Scraper Runtime:** ~30 minutes (all platforms)
- **Database Size:** ~2 GB (16K vehicles + embeddings)

### Costs
- **Infrastructure:** $14/month (Render)
- **Embeddings:** $0.06 one-time + $0.01/day updates
- **Total Monthly:** ~$14.30

---

## 📚 Documentation

- **[DEPLOY_GUIDE.md](DEPLOY_GUIDE.md)** - Complete deployment instructions
- **[TECHNICAL_SPEC.md](TECHNICAL_SPEC.md)** - Deep technical dive
- **[RAG_INTEGRATION.md](RAG_INTEGRATION.md)** - RAG architecture details
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Step-by-step setup guide
- **[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)** - Business case & roadmap

---

## 🎨 Design System

**Theme:** "Dark Luxury meets Venezuelan Energy"

**Colors:**
```css
Primary:   Deep Blues/Purples (#1A1333, #2D1B4E)
Accent:    Electric Cyan (#00D9FF, #4DE6FF)
Secondary: Warm Amber (#FF6B35, #FF8C42)
Neutrals:  Sophisticated Grays (#1C1C1E to #F2F2F7)
```

**Style:** Minimalista/Maximalista
- Generous white space + dramatic gradients
- Glassmorphism effects
- Fluid animations
- Strong visual hierarchy

---

## 🔐 Security

- ✅ Password hashing (bcrypt)
- ✅ JWT tokens with expiration
- ✅ Refresh token rotation
- ✅ Rate limiting by tier
- ✅ SQL injection protection (parameterized queries)
- ✅ CORS configuration
- ✅ Environment variable management

---

## 💰 Business Model

### Freemium SaaS

**Free Tier:**
- 5 searches per day
- View results
- Basic filters

**Premium - $7.99/month:**
- Unlimited searches
- Price drop alerts
- Saved searches
- Comparison tools
- Priority support
- Ad-free experience

**Target:** 1,000 users × 10% conversion = 100 paying = $800/month

---

## 🗺️ Roadmap

### Phase 1: Backend (✅ Complete)
- [x] Authentication system
- [x] RAG search engine
- [x] 6 platform scrapers
- [x] Database schema
- [x] API endpoints

### Phase 2: Frontend (Current)
- [ ] Landing page
- [ ] Auth UI
- [ ] Dashboard
- [ ] Mobile responsive
- [ ] Deploy to Vercel

### Phase 3: Launch (Week 3)
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] SEO optimization
- [ ] Analytics setup
- [ ] 🚀 PUBLIC LAUNCH

### Phase 4: Growth (Month 2+)
- [ ] Payment integration (Stripe/Zinli)
- [ ] Email notifications
- [ ] Mobile app (React Native)
- [ ] Admin dashboard
- [ ] More scrapers (Facebook Marketplace)

---

## 👥 Team

**Founder & Creator:** Mario Cardozo  
**Company:** MGA (Mac Global Apps)  
**Email:** mac@macmga.com  
**Location:** Venezuela  
**Experience:** 30+ years in computer science

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

---

## 🙏 Acknowledgments

- **RAGFIN1** - Proven RAG architecture foundation
- **Anthropic Claude** - Development assistance & query understanding
- **OpenAI** - Embeddings & semantic search
- **Render** - Hosting platform
- **Venezuela** - Market inspiration

---

## 📞 Contact

- **Founder:** Mario Cardozo
- **Company:** MGA (Mac Global Apps)
- **Email:** mac@macmga.com
- **Website:** elcomparativo.ve (pending)

---

**Built with ❤️ in Venezuela 🇻🇪**

*Making car shopping easier, one search at a time.*
#   R a i l w a y   d e p l o y  
 