"""
MercadoLibre Venezuela Scraper
Extracts vehicle listings from MercadoLibre.com.ve
"""

import asyncio
from playwright.async_api import async_playwright, Page
from typing import List, Dict, Any, Optional
from datetime import datetime
import re
from decimal import Decimal


class MercadoLibreScraper:
    """Scraper for MercadoLibre.com.ve vehicles section"""
    
    BASE_URL = "https://www.mercadolibre.com.ve"
    CARS_URL = f"{BASE_URL}/vehiculos/carros-camionetas"
    
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
        
        # Remove currency symbols and convert to number
        # MercadoLibre uses format like "US$ 25.000" or "Bs. 145.000"
        price_text = price_text.replace("US$", "").replace("USD", "").replace("Bs.", "")
        price_text = price_text.replace(".", "").replace(",", "").strip()
        
        # Extract numbers
        numbers = re.findall(r'\d+', price_text)
        if numbers:
            try:
                return Decimal(''.join(numbers))
            except:
                return None
        return None
    
    def extract_year(self, text: str) -> Optional[int]:
        """Extract year from text"""
        if not text:
            return None
        
        match = re.search(r'(19\d{2}|20[0-3]\d)', text)
        if match:
            return int(match.group(1))
        return None
    
    def extract_mileage(self, text: str) -> Optional[int]:
        """Extract mileage from text"""
        if not text:
            return None
        
        # Look for patterns like "45000 km" or "45.000 km"
        text = text.lower().replace(".", "").replace(",", "")
        match = re.search(r'(\d+)\s*(?:km|kilometros)', text)
        if match:
            return int(match.group(1))
        return None
    
    async def extract_listing_data(self, listing_element) -> Optional[Dict[str, Any]]:
        """Extract data from a single listing element"""
        try:
            # Title
            title_elem = await listing_element.query_selector(".ui-search-item__title")
            title = await title_elem.inner_text() if title_elem else ""
            
            # Price (could be in USD or Bs)
            price_elem = await listing_element.query_selector(".andes-money-amount__fraction")
            price_text = await price_elem.inner_text() if price_elem else ""
            
            # Currency
            currency_elem = await listing_element.query_selector(".andes-money-amount__currency-symbol")
            currency = await currency_elem.inner_text() if currency_elem else ""
            
            # Determine if USD or Bs
            is_usd = "US$" in currency or "USD" in currency or "$" in currency
            
            price = self.extract_price(price_text)
            price_usd = price if is_usd else None
            price_bs = price if not is_usd else None
            
            # URL
            link_elem = await listing_element.query_selector("a.ui-search-link")
            url = await link_elem.get_attribute("href") if link_elem else None
            
            # Extract ID from URL
            external_id = None
            if url:
                # MercadoLibre URLs format: /MLB-XXXXXX-titulo
                match = re.search(r'/(MLV-\d+)', url)
                if match:
                    external_id = match.group(1)
            
            # Image
            img_elem = await listing_element.query_selector("img.ui-search-result-image__element")
            image_url = await img_elem.get_attribute("src") if img_elem else None
            
            # Location (if available)
            location_elem = await listing_element.query_selector(".ui-search-item__location")
            location = await location_elem.inner_text() if location_elem else None
            
            # Attributes (year, mileage often in subtitle)
            attrs_elem = await listing_element.query_selector(".ui-search-item__subtitle")
            attrs_text = await attrs_elem.inner_text() if attrs_elem else ""
            
            # Extract year
            year = self.extract_year(title + " " + attrs_text)
            
            # Extract mileage
            mileage = self.extract_mileage(attrs_text)
            
            # Extract brand and model from title
            brand = None
            model = None
            
            if title:
                # Common brands in Venezuela
                brands = [
                    'Toyota', 'Chevrolet', 'Ford', 'Jeep', 'Nissan',
                    'Honda', 'Hyundai', 'Kia', 'Mazda', 'Mitsubishi',
                    'Volkswagen', 'Renault', 'Peugeot', 'Fiat', 'Chery',
                    'Suzuki', 'Dodge', 'RAM'
                ]
                
                title_upper = title.upper()
                for b in brands:
                    if b.upper() in title_upper:
                        brand = b
                        # Extract model (words after brand, before year)
                        parts = title.split(brand, 1)
                        if len(parts) > 1:
                            model_part = parts[1].strip()
                            # Remove year if present
                            model_part = re.sub(r'\d{4}', '', model_part).strip()
                            # Take first few words as model
                            model_words = model_part.split()[:3]
                            model = ' '.join(model_words).strip()
                        break
            
            return {
                "source": "mercadolibre",
                "external_id": external_id,
                "brand": brand,
                "model": model,
                "year": year,
                "price_usd": price_usd,
                "price_bs": price_bs,
                "mileage": mileage,
                "transmission": None,  # Need detail page
                "fuel_type": None,
                "color": None,
                "location": location,
                "description": title,
                "images": [image_url] if image_url else [],
                "contact": {},
                "url": url
            }
            
        except Exception as e:
            print(f"❌ Error extracting MercadoLibre listing: {e}")
            return None
    
    async def scrape_page(self, page: Page, page_number: int) -> List[Dict[str, Any]]:
        """Scrape a single page of listings"""
        # MercadoLibre uses _Desde_X for pagination (X = offset)
        offset = (page_number - 1) * 50  # 50 items per page
        url = f"{self.CARS_URL}_Desde_{offset}" if offset > 0 else self.CARS_URL
        
        print(f"📄 Scraping MercadoLibre page {page_number}: {url}")
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            
            # Find all listing elements
            listings = await page.query_selector_all(".ui-search-result__wrapper")
            
            print(f"  Found {len(listings)} listings on page {page_number}")
            
            vehicles = []
            for listing in listings:
                vehicle = await self.extract_listing_data(listing)
                if vehicle and vehicle["price_usd"]:  # Only if has USD price
                    vehicles.append(vehicle)
            
            return vehicles
            
        except Exception as e:
            print(f"❌ Error scraping MercadoLibre page {page_number}: {e}")
            return []
    
    async def scrape(self, max_pages: int = 5) -> List[Dict[str, Any]]:
        """
        Scrape multiple pages of MercadoLibre
        
        Args:
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of vehicle dictionaries
        """
        print(f"🚗 Starting MercadoLibre scrape (max {max_pages} pages)...")
        
        all_vehicles = []
        page = await self.context.new_page()
        
        for page_num in range(1, max_pages + 1):
            vehicles = await self.scrape_page(page, page_num)
            all_vehicles.extend(vehicles)
            
            print(f"  ✅ Page {page_num}: {len(vehicles)} vehicles extracted")
            
            # Rate limiting
            await asyncio.sleep(2)
        
        await page.close()
        
        print(f"🎉 MercadoLibre scrape complete: {len(all_vehicles)} total vehicles")
        
        return all_vehicles


async def main():
    """Test the scraper"""
    async with MercadoLibreScraper(headless=True) as scraper:
        vehicles = await scraper.scrape(max_pages=2)
        
        print(f"\n📊 Results:")
        print(f"Total vehicles: {len(vehicles)}")
        
        if vehicles:
            print(f"\n🚗 Sample vehicle:")
            print(vehicles[0])


if __name__ == "__main__":
    asyncio.run(main())
