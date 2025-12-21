"""
El Comparativo - Master Scraper Orchestrator
Coordinates all platform scrapers and populates database with embeddings
"""

import asyncio
from typing import List, Dict, Any
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.tucarro import TuCarroScraper
from scrapers.mercadolibre import MercadoLibreScraper
from scrapers.autocosmos import AutocosmosScraper
from scrapers.buscomiauto import BuscomiautoScraper
from scrapers.multimarca import MultimarcaScraper
from scrapers.usaditoscars import UsaditosCarsScraper
from database import init_db, get_db_pool
from rag import RAGSearchEngine


class MasterScraper:
    """
    Orchestrates all scrapers and manages data pipeline
    
    Pipeline:
    1. Run all scrapers in parallel
    2. Deduplicate vehicles
    3. Generate embeddings
    4. Insert into PostgreSQL with pgvector
    5. Log statistics
    """
    
    def __init__(self):
        self.scrapers_config = {
            "tucarro": {"class": TuCarroScraper, "pages": 10, "priority": 1},
            "mercadolibre": {"class": MercadoLibreScraper, "pages": 10, "priority": 1},
            "autocosmos": {"class": AutocosmosScraper, "pages": 5, "priority": 2},
            "buscomiauto": {"class": BuscomiautoScraper, "pages": 3, "priority": 2},
            "multimarca": {"class": MultimarcaScraper, "pages": 3, "priority": 3},
            "usaditoscars": {"class": UsaditosCarsScraper, "pages": 2, "priority": 3},
        }
        
        self.rag_engine = None
    
    async def run_scraper(
        self, 
        scraper_name: str, 
        scraper_class, 
        max_pages: int
    ) -> List[Dict[str, Any]]:
        """Run a single scraper"""
        try:
            print(f"\n{'='*60}")
            print(f"🚀 Starting {scraper_name} scraper...")
            print(f"{'='*60}")
            
            async with scraper_class(headless=True) as scraper:
                vehicles = await scraper.scrape(max_pages=max_pages)
            
            print(f"✅ {scraper_name}: {len(vehicles)} vehicles scraped")
            return vehicles
            
        except Exception as e:
            print(f"❌ {scraper_name} failed: {e}")
            return []
    
    async def run_all_scrapers(self) -> Dict[str, List[Dict[str, Any]]]:
        """Run all scrapers in parallel"""
        print("\n" + "="*60)
        print("🎯 EL COMPARATIVO - MASTER SCRAPER")
        print("="*60)
        print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Scrapers to run: {len(self.scrapers_config)}")
        print("="*60 + "\n")
        
        # Create scraping tasks
        tasks = []
        scraper_names = []
        
        for name, config in self.scrapers_config.items():
            task = self.run_scraper(
                name,
                config["class"],
                config["pages"]
            )
            tasks.append(task)
            scraper_names.append(name)
        
        # Run all scrapers in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Organize results by scraper
        scraped_data = {}
        for name, result in zip(scraper_names, results):
            if isinstance(result, Exception):
                print(f"❌ {name} failed with exception: {result}")
                scraped_data[name] = []
            else:
                scraped_data[name] = result
        
        return scraped_data
    
    def deduplicate_vehicles(
        self, 
        all_vehicles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Deduplicate vehicles across platforms
        
        Strategy:
        - Use external_id as primary key
        - If no external_id, use (brand, model, year, price_usd) tuple
        """
        seen = set()
        unique_vehicles = []
        
        for vehicle in all_vehicles:
            # Create unique key
            if vehicle.get("external_id"):
                key = vehicle["external_id"]
            else:
                key = (
                    vehicle.get("brand", "").lower(),
                    vehicle.get("model", "").lower(),
                    vehicle.get("year"),
                    vehicle.get("price_usd")
                )
            
            if key not in seen:
                seen.add(key)
                unique_vehicles.append(vehicle)
        
        duplicates_removed = len(all_vehicles) - len(unique_vehicles)
        print(f"\n📊 Deduplication: {duplicates_removed} duplicates removed")
        print(f"   Total vehicles: {len(all_vehicles)} → {len(unique_vehicles)}")
        
        return unique_vehicles
    
    async def populate_database(self, vehicles: List[Dict[str, Any]]):
        """Insert vehicles into database with embeddings"""
        print(f"\n{'='*60}")
        print("💾 POPULATING DATABASE")
        print(f"{'='*60}")
        
        # Initialize RAG engine
        if not self.rag_engine:
            self.rag_engine = RAGSearchEngine()
        
        pool = get_db_pool()
        inserted_count = 0
        skipped_count = 0
        error_count = 0
        
        for i, vehicle in enumerate(vehicles):
            try:
                # Generate embedding
                embedding = await self.rag_engine.embed_vehicle(vehicle)
                
                # Insert into database
                async with pool.acquire() as conn:
                    result = await conn.execute("""
                        INSERT INTO vehicles (
                            source, external_id, brand, model, year,
                            price_usd, price_bs, mileage, transmission,
                            fuel_type, color, location, description,
                            images, contact, url, embedding,
                            scraped_at, updated_at, is_active
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10,
                            $11, $12, $13, $14, $15, $16, $17,
                            NOW(), NOW(), true
                        )
                        ON CONFLICT (external_id) DO UPDATE SET
                            price_usd = EXCLUDED.price_usd,
                            price_bs = EXCLUDED.price_bs,
                            mileage = EXCLUDED.mileage,
                            description = EXCLUDED.description,
                            images = EXCLUDED.images,
                            updated_at = NOW()
                    """,
                        vehicle["source"],
                        vehicle.get("external_id"),
                        vehicle.get("brand"),
                        vehicle.get("model"),
                        vehicle.get("year"),
                        vehicle.get("price_usd"),
                        vehicle.get("price_bs"),
                        vehicle.get("mileage"),
                        vehicle.get("transmission"),
                        vehicle.get("fuel_type"),
                        vehicle.get("color"),
                        vehicle.get("location"),
                        vehicle.get("description"),
                        vehicle.get("images"),
                        vehicle.get("contact"),
                        vehicle.get("url"),
                        embedding
                    )
                
                inserted_count += 1
                
                # Progress indicator
                if (i + 1) % 100 == 0:
                    print(f"  ✅ Processed {i + 1}/{len(vehicles)} vehicles...")
                
            except Exception as e:
                if "duplicate key" in str(e).lower():
                    skipped_count += 1
                else:
                    error_count += 1
                    print(f"  ❌ Error inserting vehicle {i+1}: {e}")
        
        print(f"\n📊 Database Population Summary:")
        print(f"   ✅ Inserted: {inserted_count}")
        print(f"   ⏭️  Skipped (duplicates): {skipped_count}")
        print(f"   ❌ Errors: {error_count}")
        print(f"   📦 Total processed: {len(vehicles)}")
    
    async def run(self):
        """Main execution method"""
        start_time = datetime.now()
        
        try:
            # Initialize database
            print("🔧 Initializing database...")
            await init_db()
            
            # Run all scrapers
            scraped_data = await self.run_all_scrapers()
            
            # Combine all vehicles
            all_vehicles = []
            for source, vehicles in scraped_data.items():
                all_vehicles.extend(vehicles)
                print(f"   {source}: {len(vehicles)} vehicles")
            
            print(f"\n📊 Total scraped: {len(all_vehicles)} vehicles")
            
            if not all_vehicles:
                print("❌ No vehicles scraped. Exiting.")
                return
            
            # Deduplicate
            unique_vehicles = self.deduplicate_vehicles(all_vehicles)
            
            # Populate database
            await self.populate_database(unique_vehicles)
            
            # Final statistics
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print(f"\n{'='*60}")
            print("🎉 SCRAPING COMPLETE!")
            print(f"{'='*60}")
            print(f"⏱️  Duration: {duration:.2f} seconds ({duration/60:.2f} minutes)")
            print(f"📊 Vehicles per source:")
            for source, vehicles in scraped_data.items():
                print(f"   {source}: {len(vehicles)}")
            print(f"\n💾 Database:")
            print(f"   Total vehicles in DB: {len(unique_vehicles)}")
            print(f"{'='*60}")
            
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            raise


async def main():
    """Entry point"""
    scraper = MasterScraper()
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())
