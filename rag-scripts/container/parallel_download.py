import asyncio
import aiohttp
import os

URLS_FILE = "links.txt"
OUTPUT_DIR = "html_data"


async def fetch(session, url, idx):
    """Fetch a single URL and save HTML to file."""
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            html = await response.text()

            filename = os.path.join(OUTPUT_DIR, f"page_{idx}.html")
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html)

            print(f"[OK] {url} -> {filename}")
    except Exception as e:
        print(f"[ERROR] {url}: {e}")


async def main():
    # Read list of URLs
    with open(URLS_FILE, "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    # Create output folder
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Run parallel downloads
    async with aiohttp.ClientSession() as session:
        tasks = [
            asyncio.create_task(fetch(session, url, idx))
            for idx, url in enumerate(urls)
        ]
        await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())

