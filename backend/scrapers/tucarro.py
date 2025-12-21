"""
TuCarro.com.ve Scraper
Extracts vehicle listings from TuCarro using Playwright
"""

import asyncio
from playwright.async_api import async_playwright, Page
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from decimal import Decimal


class TuCarroScraper:
    """Scraper for TuCarro.com.ve"""
    
    BASE_URL = "https://www.tucarro.com.ve"
    SEARCH_URL = f"{BASE_URL}/carros/usados"
    
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
        
        # Remove currency symbols and text
        price_text = price_text.replace("$", "").replace("USD", "").replace(",", "").replace(".", "")
        price_text = re.sub(r"[^\d]", "", price_text)
        
        if price_text:
            try:
                return Decimal(price_text)
            except:
                return None
        return None
    
    def extract_year(self, text: str) -> Optional[int]:
        """Extract year from text"""
        if not text:
            return None
        
        # Look for 4-digit year (1990-2030)
        match = re.search(r"(19\d{2}|20[0-3]\d)", text)
        if match:
            return int(match.group(1))
        return None
    
    def extract_mileage(self, text: str) -> Optional[int]:
        """Extract mileage from text"""
        if not text:
            return None
        
        # Look for numbers followed by "km" or "kilometros"
        text = text.lower().replace(",", "").replace(".", "")
        match = re.search(r"(\d+)\s*(?:km|kilometros|kilómetros)", text)
        if match:
            return int(match.group(1))
        return None
    
    async def extract_listing_data(self, listing_element) -> Optional[Dict[str, Any]]:
        """Extract data from a single listing element"""
        try:
            # Title (usually contains brand, model, year)
            title_elem = await listing_element.query_selector(".ui-search-item__title")
            title = await title_elem.inner_text() if title_elem else ""
            
            # Price
            price_elem = await listing_element.query_selector(".ui-search-price__second-line .andes-money-amount__fraction")
            price_text = await price_elem.inner_text() if price_elem else ""
            price_usd = self.extract_price(price_text)
            
            # URL
            link_elem = await listing_element.query_selector("a.ui-search-link")
            url = await link_elem.get_attribute("href") if link_elem else None
            
            # Extract external ID from URL
            external_id = None
            if url:
                match = re.search(r"[/-]([A-Z]{3}\d+)", url)
                if match:
                    external_id = match.group(1)
            
            # Image
            img_elem = await listing_element.query_selector("img.ui-search-result-image__element")
            image_url = await img_elem.get_attribute("src") if img_elem else None
            
            # Location
            location_elem = await listing_element.query_selector(".ui-search-item__location")
            location = await location_elem.inner_text() if location_elem else None
            
            # Extract year from title
            year = self.extract_year(title)
            
            # Extract brand and model from title (basic parsing)
            brand = None
            model = None
            if title:
                parts = title.split()
                if len(parts) >= 2:
                    brand = parts[0]
                    # Model is everything after brand until year
                    model_parts = []
                    for part in parts[1:]:
                        if re.match(r"^\d{4}$", part):  # Stop at year
                            break
                        model_parts.append(part)
                    model = " ".join(model_parts) if model_parts else None
            
            return {
                "source": "tucarro",
                "external_id": external_id,
                "brand": brand,
                "model": model,
                "year": year,
                "price_usd": price_usd,
                "price_bs": None,  # TuCarro usually shows USD
                "mileage": None,  # Need to visit detail page
                "transmission": None,
                "fuel_type": None,
                "color": None,
                "location": location,
                "description": title,
                "images": [image_url] if image_url else [],
                "contact": {},
                "url": url
            }
            
        except Exception as e:
            print(f"❌ Error extracting listing: {e}")
            return None
    
    async def scrape_page(self, page: Page, page_number: int) -> List[Dict[str, Any]]:
        """Scrape a single page of listings"""
        url = f"{self.SEARCH_URL}?page={page_number}"
        
        print(f"📄 Scraping page {page_number}: {url}")
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)  # Wait for dynamic content
            
            # Find all listing elements
            listings = await page.query_selector_all(".ui-search-result")
            
            print(f"  Found {len(listings)} listings on page {page_number}")
            
            vehicles = []
            for listing in listings:
                vehicle = await self.extract_listing_data(listing)
                if vehicle and vehicle["price_usd"]:  # Only include if has price
                    vehicles.append(vehicle)
            
            return vehicles
            
        except Exception as e:
            print(f"❌ Error scraping page {page_number}: {e}")
            return []
    
    async def scrape(self, max_pages: int = 5) -> List[Dict[str, Any]]:
        """
        Scrape multiple pages of TuCarro
        
        Args:
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of vehicle dictionaries
        """
        print(f"🚗 Starting TuCarro scrape (max {max_pages} pages)...")
        
        all_vehicles = []
        
        page = await self.context.new_page()
        
        for page_num in range(1, max_pages + 1):
            vehicles = await self.scrape_page(page, page_num)
            all_vehicles.extend(vehicles)
            
            print(f"  ✅ Page {page_num}: {len(vehicles)} vehicles extracted")
            
            # Rate limiting
            await asyncio.sleep(2)
        
        await page.close()
        
        print(f"🎉 TuCarro scrape complete: {len(all_vehicles)} total vehicles")
        
        return all_vehicles
    
    async def scrape_detail(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape detailed information from a vehicle detail page
        
        This can be used to get additional info like:
        - Exact mileage
        - Transmission type
        - Fuel type
        - Color
        - Full description
        - All images
        - Contact info
        """
        try:
            page = await self.context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            
            # Extract detailed information
            # (Selectors will need to be adjusted based on actual page structure)
            
            detail_data = {}
            
            # Mileage
            mileage_elem = await page.query_selector("text=/kilometraje/i")
            if mileage_elem:
                mileage_text = await mileage_elem.inner_text()
                detail_data["mileage"] = self.extract_mileage(mileage_text)
            
            # Transmission
            trans_elem = await page.query_selector("text=/transmisión/i")
            if trans_elem:
                detail_data["transmission"] = await trans_elem.inner_text()
            
            # More fields can be added here...
            
            await page.close()
            return detail_data
            
        except Exception as e:
            print(f"❌ Error scraping detail page: {e}")
            return None


async def main():
    """Test the scraper"""
    async with TuCarroScraper(headless=True) as scraper:
        vehicles = await scraper.scrape(max_pages=2)
        
        print(f"\n📊 Results:")
        print(f"Total vehicles: {len(vehicles)}")
        
        if vehicles:
            print(f"\n🚗 Sample vehicle:")
            print(vehicles[0])


if __name__ == "__main__":
    asyncio.run(main())
