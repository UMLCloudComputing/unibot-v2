import argparse
import os
import asyncio
import aiohttp
import boto3
import io
from urllib.parse import urlparse
from pathlib import Path

VERBOSE=True
s3_client = boto3.client("s3")
BUCKET_NAME=None
target_folder = "html-data"

os.makedirs(target_folder, exist_ok=True)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Download data to an S3 bucket given a list of URLs"
    )

    # Required positional arguments
    parser.add_argument(
        "--links_file_path",
        help="Path to the links file (required)."
    )
    parser.add_argument(
        "--s3_bucket_name",
        help="S3 bucket name. HTML data uploaded here. (required)"
    )
   
    args = parser.parse_args()
    
    return args 

def log(message):
    """Print message only if verbose is enabled."""
    VERBOSE=True
    if VERBOSE:
        print(f"[VERBOSE] {message}")

def extract_s3_key_from_url(url: str) -> str:
    """Derive a meaningful S3 key from a URL, even if it ends with a slash."""
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]  # drop empty components
    if parts:
        key = parts[-1]  # last non-empty segment
    else:
        # fallback if URL has no path, e.g. "https://example.com"
        key = parsed.netloc
    return key

async def fetch_data(links_path: str, s3_bucket_name: str | None):
    print("Downloading data...")
    with open(links_path, "r") as f:
        urls = [line.strip() for line in f if line.strip()]
    if s3_bucket_name:
        async with aiohttp.ClientSession() as session:
            tasks = [download_and_upload_stream(session, url, s3_bucket_name) for url in urls]
            await asyncio.gather(*tasks)
    else:
        async with aiohttp.ClientSession() as session:
            tasks = [download_file(session, url) for url in urls]
            await asyncio.gather(*tasks)
                
class StreamToS3(io.RawIOBase):
    def __init__(self, s3_client, bucket, key):
        self.s3_client = s3_client
        self.bucket = bucket
        self.key = key
        self.buffer = bytearray()

    def write(self, b):
        self.buffer.extend(b)
        if len(self.buffer) > 8*1024*1024:  # upload in 8MB chunks
            self.flush()
        return len(b)

    def flush(self):
        if self.buffer:
            self.s3_client.put_object(Bucket=self.bucket, Key=self.key, Body=self.buffer)
            self.buffer = bytearray()

    def close(self):
        self.flush()

async def download_and_upload_stream(session, url, bucket):
    key = extract_s3_key_from_url(url)
    async with session.get(url) as response:
        response.raise_for_status()
        s3_stream = StreamToS3(s3_client, bucket, key)
        async for chunk in response.content.iter_chunked(8192):
            s3_stream.write(chunk)
        s3_stream.close()

async def download_file(session, url):
    """Download a single file from URL asynchronously."""
    filename = Path(target_folder) / Path(url).name

    counter = 1
    while filename.exists():
        filename = target_folder / f"{filename.stem}_{counter}{filename.suffix}"
        counter += 1

    try:
        async with session.get(url) as response:
            response.raise_for_status()
            print(f"Downloading {url} -> {filename}")
            with open(filename, "wb") as f:
                async for chunk in response.content.iter_chunked(8192):
                    f.write(chunk)
    except aiohttp.ClientError as e:
        print(f"Failed to download {url}: {e}")

def main():
    args = parse_args()
    log(f"Links file: {args.links_file_path}")
    log(f"S3 Bucket Name: {args.s3_bucket_name}")
    
    asyncio.run(fetch_data(args.links_file_path, args.s3_bucket_name))


if __name__ == "__main__":
    main()

