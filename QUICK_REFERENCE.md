# 🎯 DEPLOY QUICK REFERENCE - El Comparativo

**Tiempo total:** 30-45 minutos  
**Costo:** $14/mes  

---

## ✅ CHECKLIST PRE-DEPLOY

Antes de empezar, asegúrate de tener:

- [ ] OpenAI API Key (https://platform.openai.com/api-keys)
- [ ] Anthropic API Key (https://console.anthropic.com/settings/keys)
- [ ] Cuenta GitHub (https://github.com)
- [ ] Cuenta Render (https://render.com)
- [ ] Los archivos del proyecto descargados

---

## 🚀 COMANDOS RÁPIDOS

### 1. Setup Git Local
```bash
chmod +x git-setup.sh
./git-setup.sh
```

### 2. Generar SECRET_KEY
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 3. Push a GitHub
```bash
# Después de crear el repo en GitHub
git remote add origin https://github.com/TU_USUARIO/el-comparativo.git
git branch -M main
git push -u origin main
```

### 4. Habilitar pgvector
```bash
# Conectar a tu database de Render
psql "TU_DATABASE_URL?sslmode=require"

# En psql:
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
\q
```

### 5. Run Scrapers (Local)
```bash
cd backend

# Set variables
export DATABASE_URL="TU_DATABASE_URL?sslmode=require"
export OPENAI_API_KEY="sk-proj-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Install (si no tienes)
pip install -r requirements.txt
playwright install chromium

# Run
python -m scrapers.master_scraper
```

---

## 🔧 CONFIGURACIÓN RENDER

### PostgreSQL Database
```
Name: el-comparativo-db
Database: elcomparativo
User: elcomparativo
Region: Oregon
Version: 15
Plan: Starter ($7/mo)
```

### Web Service
```
Name: el-comparativo-api
Region: Oregon
Runtime: Python 3

Build Command:
pip install -r backend/requirements.txt && playwright install chromium && playwright install-deps chromium

Start Command:
cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT

Plan: Starter ($7/mo)
```

### Environment Variables
```
PYTHON_VERSION = 3.11.0
ENVIRONMENT = production
SECRET_KEY = [GENERAR]
DATABASE_URL = [COPIAR DE POSTGRESQL + ?sslmode=require]
OPENAI_API_KEY = sk-proj-...
ANTHROPIC_API_KEY = sk-ant-...
```

---

## 🧪 TESTING

### Health Check
```bash
curl https://el-comparativo-api.onrender.com/health
```

### API Docs
```
https://el-comparativo-api.onrender.com/docs
```

### Registro de Usuario
```bash
curl -X POST https://el-comparativo-api.onrender.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "mac@macmga.com",
    "password": "TestPassword123",
    "full_name": "Mario Cardozo"
  }'
```

### Test Search
```bash
curl -X POST https://el-comparativo-api.onrender.com/api/search/conversational \
  -H "Authorization: Bearer [ACCESS_TOKEN]" \
  -H "Content-Type: application/json" \
  -d '{"query": "Toyota 4Runner menos de 35 mil", "limit": 5}'
```

---

## 📊 QUERIES ÚTILES

### Contar Vehículos
```sql
SELECT COUNT(*) FROM vehicles WHERE is_active = true;
```

### Vehículos por Fuente
```sql
SELECT source, COUNT(*) 
FROM vehicles 
WHERE is_active = true 
GROUP BY source;
```

### Verificar Embeddings
```sql
SELECT COUNT(*) FROM vehicles WHERE embedding IS NOT NULL;
```

### Top Marcas
```sql
SELECT brand, COUNT(*) as total
FROM vehicles 
WHERE is_active = true 
GROUP BY brand 
ORDER BY total DESC 
LIMIT 10;
```

---

## 🐛 TROUBLESHOOTING RÁPIDO

**Error:** "could not load library vector"
→ Ejecutar CREATE EXTENSION vector en PostgreSQL

**Error:** "playwright executable doesn't exist"
→ Verificar Build Command incluye playwright install

**Error:** "Database connection failed"
→ Verificar DATABASE_URL tiene ?sslmode=require

**Error:** "401 Unauthorized"
→ Verificar API keys son correctos

**Scrapers muy lentos:**
→ Normal, 30-45 minutos para ~16K vehículos

---

## 📞 SOPORTE

**Founder:** Mario Cardozo  
**Email:** mac@macmga.com  
**Company:** MGA (Mac Global Apps)

**Documentación:**
- DEPLOY_NOW.md - Guía completa
- DEPLOY_GUIDE.md - Guía detallada
- README.md - Overview del proyecto

---

## ✅ SUCCESS CHECKLIST

Cuando todos estos estén ✅, estás en producción:

- [ ] Código en GitHub
- [ ] PostgreSQL database creada y accesible
- [ ] pgvector extension habilitada
- [ ] Web service deployed y running
- [ ] Environment variables configuradas
- [ ] Health check responde "ok"
- [ ] API docs accesibles en /docs
- [ ] Scrapers ejecutados exitosamente
- [ ] ~16,000 vehículos en database
- [ ] Embeddings generados (COUNT > 0)
- [ ] RAG search funcional
- [ ] Test de registro/login exitoso
- [ ] Test de search exitoso

---

**URL de tu API:** https://el-comparativo-api.onrender.com
**Swagger Docs:** https://el-comparativo-api.onrender.com/docs

**🎉 ¡Éxito! Backend en producción.**
