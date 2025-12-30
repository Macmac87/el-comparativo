import asyncio
from scrapers.tucarro import TuCarroScraper

async def test():
    try:
        async with TuCarroScraper(headless=True) as scraper:
            vehicles = await scraper.scrape(max_pages=1)
            print(f'Got {len(vehicles)} vehicles')
            if vehicles:
                print(f'First vehicle: {vehicles[0]}')
    except Exception as e:
        print(f'ERROR: {e}')
        import traceback
        traceback.print_exc()

asyncio.run(test())