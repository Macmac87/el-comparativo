#!/bin/bash

# El Comparativo - Git Setup Script
# Prepara el repositorio para push a GitHub

echo "🚀 El Comparativo - Git Setup"
echo "=============================="
echo ""

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "📦 Inicializando repositorio Git..."
    git init
    echo "✅ Git inicializado"
else
    echo "✅ Git ya está inicializado"
fi

# Create .gitignore if doesn't exist
if [ ! -f ".gitignore" ]; then
    echo "📝 Creando .gitignore..."
    cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
*.egg-info/
.installed.cfg
*.egg

# Environment variables
.env
.env.local
.env.*.local

# IDEs
.vscode/
.idea/
*.swp
.DS_Store

# Logs
*.log
logs/

# Database
*.db
*.sqlite

# Playwright
.playwright/

# Node
node_modules/
.next/
EOF
    echo "✅ .gitignore creado"
fi

# Add all files
echo ""
echo "📦 Agregando archivos..."
git add .

# Check if there are changes to commit
if git diff-index --quiet HEAD --; then
    echo "⚠️  No hay cambios para commit"
else
    echo "💾 Creando commit..."
    git commit -m "El Comparativo - Backend completo

- Sistema de autenticación JWT
- RAG search con OpenAI + pgvector
- 6 scrapers (TuCarro, MercadoLibre, Autocosmos, Buscomiauto, Multimarca, UsaditosCars)
- Master orchestrator
- Database schema completo
- 18 API endpoints
- Deploy ready para Render

Founder: Mario Cardozo
Company: MGA (Mac Global Apps)
Email: mac@macmga.com"
    
    echo "✅ Commit creado"
fi

echo ""
echo "=============================="
echo "✅ Git setup completo!"
echo ""
echo "Siguiente paso:"
echo "1. Crear repositorio en GitHub: https://github.com/new"
echo "2. Nombre: el-comparativo"
echo "3. Ejecutar:"
echo ""
echo "   git remote add origin https://github.com/TU_USUARIO/el-comparativo.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "=============================="
