"""
Database configuration and utilities
PostgreSQL + pgvector for vector search
"""

import asyncpg
import os
from typing import Optional

_pool: Optional[asyncpg.Pool] = None


async def init_db():
    """Initialize database connection pool and create tables"""
    global _pool
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    _pool = await asyncpg.create_pool(
        database_url,
        min_size=5,
        max_size=20,
        command_timeout=60
    )
    
    async with _pool.acquire() as conn:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                phone VARCHAR(50),
                subscription_tier VARCHAR(20) DEFAULT 'free',
                subscription_status VARCHAR(20) DEFAULT 'active',
                subscription_starts_at TIMESTAMP,
                subscription_ends_at TIMESTAMP,
                daily_searches_count INTEGER DEFAULT 0,
                daily_searches_reset_at TIMESTAMP DEFAULT NOW(),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                last_login_at TIMESTAMP,
                is_active BOOLEAN DEFAULT true,
                email_verified BOOLEAN DEFAULT false,
                verification_token VARCHAR(255),
                CONSTRAINT valid_subscription_tier 
                    CHECK (subscription_tier IN ('free', 'premium'))
            )
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_subscription 
            ON users(subscription_tier, subscription_status)
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS vehicles (
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
                embedding vector(1536),
                scraped_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                is_active BOOLEAN DEFAULT true
            )
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_vehicles_brand ON vehicles(brand)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_vehicles_model ON vehicles(model)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_vehicles_year ON vehicles(year)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_vehicles_price_usd ON vehicles(price_usd)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_vehicles_location ON vehicles(location)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_vehicles_source ON vehicles(source)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_vehicles_active ON vehicles(is_active)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_vehicles_embedding 
            ON vehicles 
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS searches (
                id SERIAL PRIMARY KEY,
                query TEXT NOT NULL,
                filters JSONB,
                user_ip VARCHAR(50),
                results_count INTEGER,
                clicked_vehicle_id INTEGER REFERENCES vehicles(id),
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_searches_created ON searches(created_at)
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS saved_searches (
                id SERIAL PRIMARY KEY,
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                name VARCHAR(255),
                query TEXT NOT NULL,
                filters JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_saved_searches_user ON saved_searches(user_id)
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS saved_vehicles (
                id SERIAL PRIMARY KEY,
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                vehicle_id INTEGER REFERENCES vehicles(id) ON DELETE CASCADE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                CONSTRAINT unique_user_vehicle UNIQUE(user_id, vehicle_id)
            )
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_saved_vehicles_user ON saved_vehicles(user_id)
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_saved_vehicles_vehicle ON saved_vehicles(vehicle_id)
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id SERIAL PRIMARY KEY,
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                query TEXT NOT NULL,
                filters JSONB,
                results_count INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_search_history_user 
            ON search_history(user_id, created_at DESC)
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                amount DECIMAL(10,2) NOT NULL,
                currency VARCHAR(3) DEFAULT 'USD',
                status VARCHAR(20),
                payment_method VARCHAR(50),
                transaction_id VARCHAR(255),
                created_at TIMESTAMP DEFAULT NOW(),
                CONSTRAINT valid_payment_status 
                    CHECK (status IN ('pending', 'completed', 'failed', 'refunded'))
            )
        """)
        
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_payments_user ON payments(user_id, created_at DESC)
        """)
        
        print("✅ All database tables created successfully")


def get_db_pool() -> asyncpg.Pool:
    """Get the database connection pool"""
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_db() first.")
    return _pool


async def execute_query(query: str, *args):
    """Execute a query and return results"""
    pool = get_db_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def execute_one(query: str, *args):
    """Execute a query and return a single result"""
    pool = get_db_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def execute_write(query: str, *args):
    """Execute a write query (INSERT, UPDATE, DELETE)"""
    pool = get_db_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)
