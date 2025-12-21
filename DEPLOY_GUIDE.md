# 🚀 Deploy Guide - El Comparativo Backend

**Tiempo estimado:** 30-45 minutos  
**Costo:** $14/mes (API $7 + DB $7)

---

## 📋 Pre-requisitos

- [x] Cuenta en Render.com (gratis)
- [x] OpenAI API Key
- [x] Anthropic API Key
- [x] GitHub repo (opcional, recomendado)

---

## 🎯 Opción 1: Deploy Automático (Recomendado)

### Paso 1: Push a GitHub

```bash
cd carsearch_ve

# Inicializar git (si no está)
git init

# Agregar archivos
git add .
git commit -m "El Comparativo - Backend completo"

# Crear repo en GitHub y push
git remote add origin https://github.com/TU_USUARIO/el-comparativo.git
git branch -M main
git push -u origin main
```

### Paso 2: Deploy en Render

1. **Ir a:** https://render.com
2. **Click:** "New" → "Blueprint"
3. **Conectar GitHub repo:** el-comparativo
4. **Render detectará** `render.yaml` automáticamente
5. **Click:** "Apply"

Render creará automáticamente:
- ✅ PostgreSQL database
- ✅ Web service (FastAPI)
- ✅ Environment variables

### Paso 3: Configurar Variables de Entorno

En Render dashboard:

1. **PostgreSQL database:**
   - Ir a database → "Info"
   - Copiar "External Database URL"
   - **IMPORTANTE:** Agregar `?sslmode=require` al final

2. **Web Service:**
   - Ir a service → "Environment"
   - Agregar manualmente:
     ```
     OPENAI_API_KEY=sk-proj-...
     ANTHROPIC_API_KEY=sk-ant-...
     SECRET_KEY=(auto-generado por Render)
     ```

### Paso 4: Habilitar pgvector

**Via Render Dashboard:**
1. Ir a PostgreSQL database
2. Click "Shell" (terminal)
3. Ejecutar:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

**O via terminal local:**
```bash
psql "postgresql://user:pass@host/db?sslmode=require"
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

### Paso 5: Deploy Completo

Render automáticamente:
- ✅ Instala dependencias
- ✅ Instala Playwright + Chromium
- ✅ Inicia FastAPI
- ✅ Health checks automáticos

**URL de tu API:** https://el-comparativo-api.onrender.com

---

## 🎯 Opción 2: Deploy Manual (Paso a Paso)

### 1. Crear PostgreSQL Database

1. **Render Dashboard** → "New" → "PostgreSQL"
2. **Name:** el-comparativo-db
3. **Database:** elcomparativo
4. **User:** elcomparativo
5. **Region:** Oregon
6. **Plan:** Starter ($7/mo)
7. **Click:** "Create Database"

**Esperar 2-3 minutos** hasta que esté "Available"

### 2. Habilitar pgvector

```bash
# Copiar External Database URL de Render
psql "postgresql://elcomparativo:PASSWORD@HOST/elcomparativo?sslmode=require"

# En psql:
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
\q
```

### 3. Crear Web Service

1. **Render Dashboard** → "New" → "Web Service"
2. **Conectar GitHub** (o "Public Git repository")
3. **Name:** el-comparativo-api
4. **Region:** Oregon
5. **Branch:** main
6. **Root Directory:** (dejar vacío)
7. **Runtime:** Python 3
8. **Build Command:**
   ```bash
   pip install -r backend/requirements.txt && playwright install chromium && playwright install-deps chromium
   ```
9. **Start Command:**
   ```bash
   cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
   ```
10. **Plan:** Starter ($7/mo)

### 4. Environment Variables

En "Environment" tab:

```
PYTHON_VERSION=3.11.0
ENVIRONMENT=production
SECRET_KEY=(generar random 32+ chars)
DATABASE_URL=(copiar de PostgreSQL → External Database URL + ?sslmode=require)
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
```

**Generar SECRET_KEY:**
```python
import secrets
print(secrets.token_urlsafe(32))
# Ejemplo: dGhpc19pc19hX3Zlcnlfc2VjdXJlX2tleV90aGF0X2lzXzMy
```

### 5. Deploy

**Click:** "Create Web Service"

Render automáticamente:
- Clona el repo
- Instala requirements
- Instala Playwright
- Inicia el servidor
- Asigna URL pública

**Tiempo de deploy:** 5-10 minutos

---

## ✅ Verificar Deploy

### 1. Health Check

```bash
curl https://el-comparativo-api.onrender.com/health

# Respuesta esperada:
{
  "status": "ok",
  "database": "healthy",
  "rag_engine": "initialized"
}
```

### 2. API Docs

Abrir en navegador:
```
https://el-comparativo-api.onrender.com/docs
```

Deberías ver Swagger UI con todos los endpoints.

### 3. Test Database

```bash
# Verificar que la DB tiene las tablas
psql "postgresql://..." -c "\dt"

# Deberías ver:
# - users
# - vehicles
# - saved_searches
# - search_history
# - etc.
```

---

## 🔧 Run Scrapers en Producción

### Opción A: Desde tu máquina local

```bash
# Set environment variable
export DATABASE_URL="postgresql://user:pass@host/db?sslmode=require"
export OPENAI_API_KEY="sk-proj-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Run master scraper
cd backend
python -m scrapers.master_scraper
```

**Esto poblará la DB en producción** con ~16K vehículos.

**Tiempo:** 30-45 minutos  
**Costo embeddings:** ~$0.06

### Opción B: Render Shell (NO recomendado para scraping largo)

Render tiene timeout de 30 minutos en shell. Mejor usar Opción A.

### Opción C: Background Job Service

**Para scraping recurrente:**

1. **Crear nuevo service:** "Background Worker"
2. **Build:** Igual que web service
3. **Start Command:**
   ```bash
   cd backend && python -m scrapers.master_scraper
   ```
4. **Schedule:** Cron job o manual trigger

---

## 🎯 Post-Deploy Checklist

- [ ] API responde en /health
- [ ] Database tiene pgvector habilitado
- [ ] Todas las tablas creadas
- [ ] Environment variables configuradas
- [ ] API docs accesibles en /docs
- [ ] Scrapers corrieron exitosamente
- [ ] Vehículos en database (verificar count)
- [ ] RAG search funciona
- [ ] Auth endpoints funcionan

---

## 📊 Monitoreo

### Render Dashboard

**Métricas automáticas:**
- CPU usage
- Memory usage
- Request count
- Response times
- Error rates

**Logs en tiempo real:**
```
Service → Logs → (real-time stream)
```

### Database Monitoring

```sql
-- Contar vehículos
SELECT COUNT(*) FROM vehicles WHERE is_active = true;

-- Vehículos por fuente
SELECT source, COUNT(*) 
FROM vehicles 
WHERE is_active = true 
GROUP BY source;

-- Vehículos con embeddings
SELECT COUNT(*) 
FROM vehicles 
WHERE embedding IS NOT NULL;

-- Usuarios registrados
SELECT COUNT(*) FROM users;

-- Uso de espacio
SELECT pg_size_pretty(pg_database_size('elcomparativo'));
```

---

## 🔄 Updates y Re-deploy

### Auto-deploy desde GitHub

Render detecta automáticamente commits:

```bash
# Hacer cambios
git add .
git commit -m "Update: nueva feature"
git push

# Render auto-deploya en 2-3 minutos
```

### Manual Deploy

En Render dashboard:
```
Service → Manual Deploy → "Deploy latest commit"
```

---

## 💰 Costos Mensuales

```
PostgreSQL Starter:  $7/mes (256 MB RAM, 1 GB storage)
Web Service Starter: $7/mes (512 MB RAM)
────────────────────────────────────────────
TOTAL:              $14/mes

Embeddings (one-time): ~$0.06
Embeddings (updates):  ~$0.01/día

TOTAL MENSUAL: ~$14.30
```

**Escalar más adelante:**
- Standard DB: $20/mo (1 GB RAM, 10 GB storage)
- Standard Web: $25/mo (2 GB RAM)

---

## 🐛 Troubleshooting

### Error: "relation does not exist"

**Causa:** Database tables no creadas

**Fix:**
```bash
# Verificar que DATABASE_URL está correcta
# Reiniciar el service (triggerea init_db())
```

### Error: "could not load library vector"

**Causa:** pgvector no instalado

**Fix:**
```sql
psql "DATABASE_URL"
CREATE EXTENSION vector;
```

### Error: "playwright executable doesn't exist"

**Causa:** Playwright no instalado correctamente

**Fix:** Verificar Build Command incluye:
```bash
playwright install chromium && playwright install-deps chromium
```

### Error: "Daily search limit reached"

**Causa:** Usuario free tier

**Fix:** 
- Upgrade a premium, o
- Reset counter manualmente en DB

---

## 📈 Scaling

### Cuando crecer (>1000 usuarios)

**Database:**
- Upgrade a Standard ($20/mo)
- 1 GB RAM, 10 GB storage
- Conexiones ilimitadas

**Web Service:**
- Upgrade a Standard ($25/mo)
- 2 GB RAM
- Auto-scaling

**Background Jobs:**
- Separar scrapers a Background Worker
- Cron schedule automático
- No afecta API performance

---

## 🎉 Deploy Checklist Final

```
✅ PostgreSQL database creada
✅ pgvector extension habilitada
✅ Web service deployed
✅ Environment variables configuradas
✅ Health check pasando
✅ API docs accesibles
✅ Scrapers ejecutados
✅ ~16K vehículos en DB
✅ Embeddings generados
✅ RAG search funcional
✅ Auth endpoints probados
```

**Cuando todos ✅ → BACKEND EN PRODUCCIÓN! 🚀**

---

## ⏭️ Siguiente: Frontend

Con backend en producción, podemos:

1. **Empezar frontend** mientras backend scrapes en background
2. **Testear API** desde Postman/Insomnia
3. **Monitorear métricas** en Render dashboard

**URL base para frontend:**
```javascript
const API_URL = "https://el-comparativo-api.onrender.com"
```

---

**¿Listo para deployar? Te guío paso a paso.**
