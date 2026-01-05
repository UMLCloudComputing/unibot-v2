# pip install asyncio aiohttp

import asyncio
import aiohttp
import os
import argparse

OUTPUT_DIR = "html_data"


async def fetch(session, url, idx):
    """Fetch a single URL and save HTML to file."""
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            html = await response.text()

            filename = os.path.join(url)
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html)

            print(f"[OK] {url} -> {filename}")
    except Exception as e:
        print(f"[ERROR] {url}: {e}")


async def main(URLS_FILE):
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
    parser = argparse.ArgumentParser(decription="Download multiple files in parallel and asynchronously from a file with a list of URLs")
    parser.add_argument(
        "--file",
        type=str,
        required=True,
        help="Path to the text file containe one source_url per line."
    )
    args.parser.parse_args()
    asyncio.run(main(args.file))

