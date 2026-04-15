import asyncio
import time
import aiohttp
import matplotlib.pyplot as plt
import pytest
from queue import Queue
from src import chunk_url
from mock_server import mock_docling

async def benchmark_url_count():
    # Configuration
    counts = [10, 100, 500, 1000, 2500, 5000, 10000]
    runtimes = []
    async with mock_docling() as docling_base_url:
      async with aiohttp.ClientSession() as session:
          for count in counts:
            start_time = time.perf_counter()
            tasks = [
              chunk_url(session, f"http://url-{i}.com", Queue(), {}, docling_base_url)
              for i in range(count)
            ]
            await asyncio.gather(*tasks)
            end_time = time.perf_counter()
              
            duration = end_time - start_time
            runtimes.append(duration)
            print(f"Count: {count:5} chars | Time: {duration:.4f}s")

    return counts, runtimes

# --- Plotting logic ---
def plot_results(lengths, runtimes):
    plt.figure(figsize=(10, 5))
    plt.plot(lengths, runtimes, marker='o', linestyle='-')
    plt.title("chunk_url Runtime vs. URL Count")
    plt.xlabel("URL Count (#)")
    plt.ylabel("Execution Time (Seconds)")
    plt.grid(True)
    plt.savefig("url_benchmarks.png")

if __name__ == "__main__":
    lengths, runtimes = asyncio.run(benchmark_url_lengths())
    plot_results(lengths, runtimes)
