# 🚀 DEPLOY INMEDIATO - El Comparativo

**Tiempo estimado:** 30 minutos  
**Costo:** $14/mes

---

## PASO 1: Preparar GitHub (5 minutos)

### 1.1 Crear Repositorio en GitHub

1. Ir a https://github.com/new
2. **Repository name:** `el-comparativo`
3. **Description:** "Venezuelan Vehicle Search Aggregator with RAG"
4. **Visibility:** Private (o Public si prefieres)
5. **Click:** "Create repository"

### 1.2 Push del Código

```bash
# En tu máquina local, navega al proyecto
cd el-comparativo  # (o donde tengas los archivos)

# Inicializar git
git init

# Agregar todos los archivos
git add .

# Primer commit
git commit -m "Initial commit - El Comparativo Backend completo"

# Conectar con GitHub (reemplaza TU_USUARIO)
git remote add origin https://github.com/TU_USUARIO/el-comparativo.git

# Push
git branch -M main
git push -u origin main
```

**✅ Checkpoint:** Código en GitHub

---

## PASO 2: Crear Cuenta Render (2 minutos)

1. Ir a https://render.com
2. **Sign up** con GitHub (recomendado)
3. Autorizar Render en GitHub
4. **✅ Listo**

---

## PASO 3: Crear PostgreSQL Database (3 minutos)

### 3.1 Nueva Database

1. Dashboard Render → **"New +"** → **"PostgreSQL"**
2. Configurar:
   ```
   Name: el-comparativo-db
   Database: elcomparativo
   User: elcomparativo
   Region: Oregon
   PostgreSQL Version: 15
   Plan: Starter ($7/mo)
   ```
3. **Click:** "Create Database"
4. **Esperar:** 2-3 minutos hasta que esté "Available"

### 3.2 Habilitar pgvector

**Opción A: Via Dashboard**
1. Ir a la database → **"Shell"** (terminal icon)
2. Ejecutar:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
\q
```

**Opción B: Via Terminal Local**
1. Copiar **"External Database URL"** del dashboard
2. En tu terminal:
```bash
# Reemplaza con tu URL
psql "postgresql://elcomparativo:PASSWORD@HOST/elcomparativo?sslmode=require"

# Ejecutar en psql:
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
\q
```

**✅ Checkpoint:** pgvector habilitado

---

## PASO 4: Crear Web Service (5 minutos)

### 4.1 Nuevo Web Service

1. Dashboard Render → **"New +"** → **"Web Service"**
2. **Connect GitHub repository:** el-comparativo
3. Configurar:

**Basic:**
```
Name: el-comparativo-api
Region: Oregon
Branch: main
Runtime: Python 3
```

**Build & Deploy:**
```
Root Directory: (dejar vacío)

Build Command:
pip install -r backend/requirements.txt && playwright install chromium && playwright install-deps chromium

Start Command:
cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Plan:**
```
Instance Type: Starter ($7/mo)
```

4. **NO HAGAS CLICK EN "CREATE WEB SERVICE" TODAVÍA**

### 4.2 Environment Variables

**Antes de crear**, configurar variables de entorno:

1. Scroll down a **"Environment Variables"**
2. Click **"Add Environment Variable"** para cada una:

```
PYTHON_VERSION = 3.11.0
```

```
ENVIRONMENT = production
```

```
SECRET_KEY = [GENERAR - VER ABAJO]
```

```
DATABASE_URL = [COPIAR DE POSTGRESQL - VER ABAJO]
```

```
OPENAI_API_KEY = sk-proj-[TU_KEY_AQUI]
```

```
ANTHROPIC_API_KEY = sk-ant-[TU_KEY_AQUI]
```

#### Generar SECRET_KEY

**Opción 1: Python**
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Opción 2: OpenSSL**
```bash
openssl rand -base64 32
```

**Copiar el resultado** y pegarlo en SECRET_KEY

#### Obtener DATABASE_URL

1. Ir a tu PostgreSQL database en Render
2. Click **"Info"**
3. Copiar **"External Database URL"**
4. **IMPORTANTE:** Agregar `?sslmode=require` al final
   
   Ejemplo:
   ```
   postgresql://user:pass@host/db?sslmode=require
   ```

5. Pegar en DATABASE_URL

### 4.3 Crear Service

**Ahora sí:**
1. Scroll hasta arriba
2. Click **"Create Web Service"**
3. **Esperar:** 5-10 minutos mientras Render:
   - Clona el repo
   - Instala dependencies
   - Instala Playwright + Chromium
   - Inicia FastAPI
   - Asigna URL

**✅ Checkpoint:** Web Service deployed

---

## PASO 5: Verificar Deploy (2 minutos)

### 5.1 Health Check

Tu API estará en: `https://el-comparativo-api.onrender.com`

**Verificar:**
```bash
curl https://el-comparativo-api.onrender.com/health
```

**Respuesta esperada:**
```json
{
  "status": "ok",
  "database": "healthy",
  "rag_engine": "initialized"
}
```

### 5.2 API Docs

Abrir en navegador:
```
https://el-comparativo-api.onrender.com/docs
```

Deberías ver **Swagger UI** con todos los endpoints.

**✅ Checkpoint:** API funcionando

---

## PASO 6: Poblar Database con Scrapers (30-45 minutos)

### Opción A: Desde Tu Máquina Local (RECOMENDADO)

**Requisitos:**
- Python 3.11+
- Playwright instalado

**Pasos:**

```bash
# 1. Instalar dependencias (si no las tienes)
cd el-comparativo/backend
pip install -r requirements.txt
playwright install chromium

# 2. Configurar variables de entorno
export DATABASE_URL="postgresql://..." # Tu External Database URL con ?sslmode=require
export OPENAI_API_KEY="sk-proj-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# 3. Run master scraper
python -m scrapers.master_scraper
```

**Esto va a:**
- Scrape 6 plataformas en paralelo
- ~30-45 minutos
- ~18,300 vehículos (raw)
- ~16,000 únicos después de dedup
- Generar embeddings (~$0.06)
- Poblar database en producción

**Output esperado:**
```
🎯 EL COMPARATIVO - MASTER SCRAPER
============================================================
Start time: 2024-12-12 12:00:00
Scrapers to run: 6
============================================================

🚀 Starting tucarro scraper...
🚀 Starting mercadolibre scraper...
🚀 Starting autocosmos scraper...
...

📊 Total scraped: 17,962 vehicles
📊 Deduplication: 1,842 duplicates removed
   Total vehicles: 17,962 → 16,120

💾 POPULATING DATABASE
...
✅ Processed 16120/16120 vehicles...

🎉 SCRAPING COMPLETE!
⏱️  Duration: 1847.32 seconds (30.79 minutes)
💾 Database: 16,120 vehicles
```

### Opción B: Background Worker en Render

**Si quieres que Render ejecute los scrapers:**

1. Dashboard → **"New +"** → **"Background Worker"**
2. Mismo repo: el-comparativo
3. **Build Command:** (igual que web service)
4. **Start Command:**
   ```bash
   cd backend && python -m scrapers.master_scraper
   ```
5. Mismo environment variables
6. Click "Create Background Worker"

**NOTA:** Solo se ejecutará una vez. Para scraping recurrente necesitarías Cron Jobs (feature de pago en Render).

**✅ Checkpoint:** Database poblada con ~16K vehículos

---

## PASO 7: Verificar Todo Funciona (3 minutos)

### Test 1: Contar Vehículos

```bash
psql "DATABASE_URL" -c "SELECT COUNT(*) FROM vehicles WHERE is_active = true;"
```

**Esperado:** ~16,000

### Test 2: Verificar Embeddings

```bash
psql "DATABASE_URL" -c "SELECT COUNT(*) FROM vehicles WHERE embedding IS NOT NULL;"
```

**Esperado:** ~16,000 (mismo número)

### Test 3: Test Search Endpoint

**Registrar usuario:**
```bash
curl -X POST https://el-comparativo-api.onrender.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "mac@macmga.com",
    "password": "TestPassword123",
    "full_name": "Mario Cardozo"
  }'
```

**Guardar el access_token** de la respuesta.

**Test RAG search:**
```bash
curl -X POST https://el-comparativo-api.onrender.com/api/search/conversational \
  -H "Authorization: Bearer [TU_ACCESS_TOKEN]" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Toyota 4Runner menos de 35 mil",
    "limit": 5
  }'
```

**Deberías recibir:** Lista de vehículos rankeados por relevancia

**✅ Checkpoint:** Todo funcional en producción

---

## 🎉 DEPLOYMENT COMPLETO

### Lo que ahora tienes:

✅ Backend API en producción  
✅ PostgreSQL database con pgvector  
✅ ~16,000 vehículos con embeddings  
✅ RAG search funcional  
✅ Authentication system completo  
✅ URL pública: https://el-comparativo-api.onrender.com  

### Costos:

```
PostgreSQL: $7/mes
Web Service: $7/mes
Embeddings: $0.06 (one-time) + $0.01/día
─────────────────────────────
TOTAL: ~$14.30/mes
```

---

## ⏭️ SIGUIENTE PASO: Frontend

Con backend en producción, ahora puedes:

### Opción 1: Empezar Frontend (Recomendado)
- Next.js + TypeScript
- Conecta a `https://el-comparativo-api.onrender.com`
- Landing page + Dashboard
- Deploy a Vercel
- **Tiempo:** 4-5 días

### Opción 2: Testear API Primero
- Usar Postman/Insomnia
- Probar todos los endpoints
- Crear usuarios de prueba
- Verificar performance
- **Tiempo:** 1-2 horas

---

## 🐛 Troubleshooting

### Error: "could not load library vector"
**Fix:** Ejecutar CREATE EXTENSION vector en PostgreSQL

### Error: "playwright executable doesn't exist"
**Fix:** Verificar Build Command incluye `playwright install chromium`

### Scrapers tardan mucho
**Normal:** 30-45 minutos para 6 plataformas y ~16K vehículos

### Database connection timeout
**Fix:** Verificar DATABASE_URL tiene `?sslmode=require` al final

---

## 📊 Monitoreo

**Render Dashboard:**
- Logs en tiempo real
- CPU/Memory usage
- Request metrics
- Error tracking

**Database Queries:**
```sql
-- Vehículos por fuente
SELECT source, COUNT(*) 
FROM vehicles 
WHERE is_active = true 
GROUP BY source;

-- Top marcas
SELECT brand, COUNT(*) 
FROM vehicles 
WHERE is_active = true 
GROUP BY brand 
ORDER BY COUNT(*) DESC 
LIMIT 10;
```

---

## ✅ CHECKLIST FINAL

- [ ] Código en GitHub
- [ ] PostgreSQL database creada
- [ ] pgvector extension habilitada
- [ ] Web service deployed
- [ ] Environment variables configuradas
- [ ] Health check pasando
- [ ] API docs accesibles
- [ ] Scrapers ejecutados
- [ ] ~16K vehículos en database
- [ ] Embeddings generados
- [ ] RAG search funcional
- [ ] Usuario de prueba creado

**Cuando todos ✅ → BACKEND EN PRODUCCIÓN! 🚀**

---

**¿Listo para deployar? Sigue estos pasos y avísame si tienes algún problema.**
