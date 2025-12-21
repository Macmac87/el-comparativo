"""
GrupoMultimarca / Multimarca.com.ve Scraper
Professional dealer network
"""

import asyncio
from playwright.async_api import async_playwright, Page
from typing import List, Dict, Any, Optional
import re
from decimal import Decimal


class MultimarcaScraper:
    """Scraper for Multimarca.com.ve"""
    
    BASE_URL = "https://multimarca.com.ve"
    CARS_URL = f"{BASE_URL}/vehiculos"
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser = None
        self.context = None
    
    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self.headless)
        self.context = await self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    def extract_price(self, price_text: str) -> Optional[Decimal]:
        """Extract numeric price"""
        if not price_text:
            return None
        numbers = re.sub(r'[^\d]', '', price_text)
        return Decimal(numbers) if numbers else None
    
    async def extract_listing_data(self, listing_element) -> Optional[Dict[str, Any]]:
        """Extract data from listing"""
        try:
            title_elem = await listing_element.query_selector("h3, .vehicle-name, .title")
            title = await title_elem.inner_text() if title_elem else ""
            
            price_elem = await listing_element.query_selector(".price, .precio")
            price_text = await price_elem.inner_text() if price_elem else ""
            price_usd = self.extract_price(price_text)
            
            link_elem = await listing_element.query_selector("a")
            url = await link_elem.get_attribute("href") if link_elem else None
            
            if url and not url.startswith("http"):
                url = f"{self.BASE_URL}{url}"
            
            external_id = None
            if url:
                match = re.search(r'/(\d+)', url)
                if match:
                    external_id = f"MM-{match.group(1)}"
            
            img_elem = await listing_element.query_selector("img")
            image_url = await img_elem.get_attribute("src") if img_elem else None
            if image_url and not image_url.startswith("http"):
                image_url = f"{self.BASE_URL}{image_url}"
            
            year = None
            year_match = re.search(r'(20\d{2})', title)
            if year_match:
                year = int(year_match.group(1))
            
            brand = None
            model = None
            brands = ['Toyota', 'Chevrolet', 'Ford', 'Jeep', 'Nissan', 'Honda', 'Hyundai']
            for b in brands:
                if b.upper() in title.upper():
                    brand = b
                    parts = title.split(brand, 1)
                    if len(parts) > 1:
                        model = ' '.join(parts[1].strip().split()[:2])
                    break
            
            return {
                "source": "multimarca",
                "external_id": external_id,
                "brand": brand,
                "model": model,
                "year": year,
                "price_usd": price_usd,
                "price_bs": None,
                "mileage": None,
                "transmission": None,
                "fuel_type": None,
                "color": None,
                "location": None,
                "description": title,
                "images": [image_url] if image_url else [],
                "contact": {},
                "url": url
            }
        except Exception as e:
            print(f"❌ Error extracting Multimarca listing: {e}")
            return None
    
    async def scrape_page(self, page: Page, page_number: int) -> List[Dict[str, Any]]:
        """Scrape a page"""
        url = f"{self.CARS_URL}?page={page_number}" if page_number > 1 else self.CARS_URL
        
        print(f"📄 Scraping Multimarca page {page_number}: {url}")
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            
            selectors = [".vehicle-item", ".car-card", ".product", "article"]
            listings = []
            for selector in selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    listings = elements
                    break
            
            print(f"  Found {len(listings)} listings")
            
            vehicles = []
            for listing in listings:
                vehicle = await self.extract_listing_data(listing)
                if vehicle and vehicle["price_usd"]:
                    vehicles.append(vehicle)
            
            return vehicles
        except Exception as e:
            print(f"❌ Error scraping page: {e}")
            return []
    
    async def scrape(self, max_pages: int = 3) -> List[Dict[str, Any]]:
        """Scrape Multimarca"""
        print(f"🚗 Starting Multimarca scrape...")
        
        all_vehicles = []
        page = await self.context.new_page()
        
        for page_num in range(1, max_pages + 1):
            vehicles = await self.scrape_page(page, page_num)
            all_vehicles.extend(vehicles)
            print(f"  ✅ Page {page_num}: {len(vehicles)} vehicles")
            await asyncio.sleep(2)
        
        await page.close()
        print(f"🎉 Multimarca scrape complete: {len(all_vehicles)} vehicles")
        return all_vehicles


async def main():
    async with MultimarcaScraper() as scraper:
        vehicles = await scraper.scrape(max_pages=2)
        print(f"\n📊 Total: {len(vehicles)}")
        if vehicles:
            print(f"Sample: {vehicles[0]}")


if __name__ == "__main__":
    asyncio.run(main())
