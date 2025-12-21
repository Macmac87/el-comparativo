#!/bin/bash

# El Comparativo - Quick Start Script
# Run this to test locally before deploying

echo "🚀 El Comparativo - Local Setup"
echo "================================"

# Check if .env exists
if [ ! -f "backend/.env" ]; then
    echo "❌ Error: backend/.env not found"
    echo "📝 Creating from .env.example..."
    cp backend/.env.example backend/.env
    echo "✅ Created backend/.env"
    echo "⚠️  IMPORTANT: Edit backend/.env and add your API keys!"
    exit 1
fi

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate venv
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "📥 Installing requirements..."
pip install -r backend/requirements.txt

# Install Playwright
echo "🎭 Installing Playwright..."
playwright install chromium

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit backend/.env with your API keys"
echo "2. Start PostgreSQL + Redis: docker-compose up -d"
echo "3. Run API: cd backend && uvicorn main:app --reload"
echo "4. Run scrapers: cd backend && python -m scrapers.master_scraper"
echo ""
echo "API will be at: http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
