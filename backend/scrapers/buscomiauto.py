"""
Buscomiauto.com Scraper
Professional dealer platform (Grupo García-Tuñón)
"""

import asyncio
from playwright.async_api import async_playwright, Page
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from decimal import Decimal


class BuscomiautoScraper:
    """Scraper for Buscomiauto.com"""
    
    BASE_URL = "https://buscomiauto.com"
    CARS_URL = f"{BASE_URL}/vehicles"
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.context = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    def extract_price(self, price_text: str) -> Optional[Decimal]:
        """Extract numeric price from text"""
        if not price_text:
            return None
        
        numbers = re.sub(r'[^\d]', '', price_text)
        
        if numbers:
            try:
                return Decimal(numbers)
            except:
                return None
        return None
    
    async def extract_listing_data(self, listing_element) -> Optional[Dict[str, Any]]:
        """Extract data from a single listing element"""
        try:
            # Title
            title_elem = await listing_element.query_selector("h3, .vehicle-title, .car-title")
            title = await title_elem.inner_text() if title_elem else ""
            
            # Price
            price_elem = await listing_element.query_selector(".price, .vehicle-price")
            price_text = await price_elem.inner_text() if price_elem else ""
            price_usd = self.extract_price(price_text)
            
            # URL
            link_elem = await listing_element.query_selector("a")
            url = await link_elem.get_attribute("href") if link_elem else None
            
            if url and not url.startswith("http"):
                url = f"{self.BASE_URL}{url}"
            
            # External ID from URL
            external_id = None
            if url:
                match = re.search(r'/vehicles/(\d+)', url)
                if match:
                    external_id = f"BCM-{match.group(1)}"
            
            # Image
            img_elem = await listing_element.query_selector("img")
            image_url = await img_elem.get_attribute("src") if img_elem else None
            
            if image_url and not image_url.startswith("http"):
                image_url = f"{self.BASE_URL}{image_url}"
            
            # Extract details
            details = {}
            detail_elems = await listing_element.query_selector_all(".spec, .detail, .feature")
            for elem in detail_elems:
                text = await elem.inner_text()
                # Parse specs like "2019 | 45,000 km | Automática"
                if "km" in text.lower():
                    mileage_match = re.search(r'(\d+[\.,]?\d*)\s*km', text.replace(".", "").replace(",", ""))
                    if mileage_match:
                        details["mileage"] = int(mileage_match.group(1))
                
                if "año" in text.lower() or re.search(r'(19\d{2}|20[0-3]\d)', text):
                    year_match = re.search(r'(19\d{2}|20[0-3]\d)', text)
                    if year_match:
                        details["year"] = int(year_match.group(1))
            
            # Year from title or details
            year = details.get("year")
            if not year:
                year_match = re.search(r'(19\d{2}|20[0-3]\d)', title)
                if year_match:
                    year = int(year_match.group(1))
            
            # Mileage
            mileage = details.get("mileage")
            
            # Brand and model
            brand = None
            model = None
            
            if title:
                brands = [
                    'Toyota', 'Chevrolet', 'Ford', 'Jeep', 'Nissan',
                    'Honda', 'Hyundai', 'Kia', 'Mazda', 'Mitsubishi',
                    'Volkswagen', 'Renault', 'Peugeot', 'Fiat'
                ]
                
                for b in brands:
                    if b.upper() in title.upper():
                        brand = b
                        parts = title.split(brand, 1)
                        if len(parts) > 1:
                            model_part = parts[1].strip()
                            model_part = re.sub(r'\d{4}', '', model_part).strip()
                            model = ' '.join(model_part.split()[:3])
                        break
            
            return {
                "source": "buscomiauto",
                "external_id": external_id,
                "brand": brand,
                "model": model,
                "year": year,
                "price_usd": price_usd,
                "price_bs": None,
                "mileage": mileage,
                "transmission": None,
                "fuel_type": None,
                "color": None,
                "location": "Caracas",  # Buscomiauto is Caracas-based
                "description": title,
                "images": [image_url] if image_url else [],
                "contact": {},
                "url": url
            }
            
        except Exception as e:
            print(f"❌ Error extracting Buscomiauto listing: {e}")
            return None
    
    async def scrape_page(self, page: Page, page_number: int) -> List[Dict[str, Any]]:
        """Scrape a single page of listings"""
        url = f"{self.CARS_URL}?page={page_number}" if page_number > 1 else self.CARS_URL
        
        print(f"📄 Scraping Buscomiauto page {page_number}: {url}")
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(3000)  # Wait for content to load
            
            # Possible selectors
            selectors = [
                ".vehicle-card",
                ".car-listing",
                ".inventory-item",
                "article"
            ]
            
            listings = []
            for selector in selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    listings = elements
                    break
            
            print(f"  Found {len(listings)} listings on page {page_number}")
            
            vehicles = []
            for listing in listings:
                vehicle = await self.extract_listing_data(listing)
                if vehicle and vehicle["price_usd"]:
                    vehicles.append(vehicle)
            
            return vehicles
            
        except Exception as e:
            print(f"❌ Error scraping Buscomiauto page {page_number}: {e}")
            return []
    
    async def scrape(self, max_pages: int = 3) -> List[Dict[str, Any]]:
        """Scrape Buscomiauto"""
        print(f"🚗 Starting Buscomiauto scrape (max {max_pages} pages)...")
        
        all_vehicles = []
        page = await self.context.new_page()
        
        for page_num in range(1, max_pages + 1):
            vehicles = await self.scrape_page(page, page_num)
            all_vehicles.extend(vehicles)
            
            print(f"  ✅ Page {page_num}: {len(vehicles)} vehicles extracted")
            
            await asyncio.sleep(2)
        
        await page.close()
        
        print(f"🎉 Buscomiauto scrape complete: {len(all_vehicles)} total vehicles")
        
        return all_vehicles


async def main():
    """Test the scraper"""
    async with BuscomiautoScraper(headless=True) as scraper:
        vehicles = await scraper.scrape(max_pages=2)
        
        print(f"\n📊 Results:")
        print(f"Total vehicles: {len(vehicles)}")
        
        if vehicles:
            print(f"\n🚗 Sample vehicle:")
            print(vehicles[0])


if __name__ == "__main__":
    asyncio.run(main())
