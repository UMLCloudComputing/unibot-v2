import asyncio
import time
import aiohttp
import matplotlib.pyplot as plt
from queue import Queue
from mock_server import mock_docling
from src import chunk_url, chunk_url_generator

# Assuming these are imported correctly from your project structure
# from src import chunk_url, chunk_url_generator
# from mock_server import mock_docling

counts = [10, 100, 500, 1000, 2500, 5000, 10000, 20000, 40000]


async def benchmark_chunk_url():
    runtimes = []
    # Using your mock server context manager
    async with mock_docling() as docling_base_url:
        async with aiohttp.ClientSession() as session:
            for count in counts:
                chunk_queue = Queue()
                start_time = time.perf_counter()

                # Internal Queue logic (Concurrent via gather)
                tasks = [
                    chunk_url(
                        session,
                        f"http://url-{i}.com",
                        {},
                        chunk_queue,
                        docling_base_url,
                    )
                    for i in range(count)
                ]
                await asyncio.gather(*tasks)

                duration = time.perf_counter() - start_time
                runtimes.append(duration)
                print(f"[Vanilla] Count: {count:5} | Time: {duration:.4f}s")

    return counts, runtimes


async def benchmark_chunk_url_generator():
    runtimes = []
    async with mock_docling() as docling_base_url:
        async with aiohttp.ClientSession() as session:
            for count in counts:
                chunk_queue = Queue()
                start_time = time.perf_counter()

                # To make this concurrent like the vanilla version,
                # we wrap the generator consumption in a helper function
                async def consume_generator(url):
                    async for chunk in chunk_url_generator(
                        session, url, {}, docling_base_url
                    ):
                        chunk_queue.put(chunk)

                tasks = [consume_generator(f"http://url-{i}.com") for i in range(count)]
                await asyncio.gather(*tasks)

                duration = time.perf_counter() - start_time
                runtimes.append(duration)
                print(f"[Generator] Count: {count:5} | Time: {duration:.4f}s")

    return counts, runtimes


def plot_results(data_vanilla, data_gen, filename):
    plt.figure(figsize=(16, 10))

    # data format: (counts, runtimes)
    plt.plot(
        data_vanilla[0],
        data_vanilla[1],
        marker="o",
        linestyle="-",
        color="#2980b9",
        label="Internal Queue (Vanilla)",
    )
    plt.plot(
        data_gen[0],
        data_gen[1],
        marker="s",
        linestyle="--",
        color="#e67e22",
        label="Generator (External Put)",
    )

    plt.title("Performance Comparison: Internal Queue vs. Async Generator", fontsize=14)
    plt.xlabel("Number of URLs Processed", fontsize=12)
    plt.ylabel("Total Execution Time (Seconds)", fontsize=12)
    plt.grid(True, which="both", linestyle="--", alpha=0.5)
    plt.legend()

    # Annotate the final points to see the gap clearly
    plt.annotate(
        f"{data_vanilla[1][-1]:.2f}s",
        (data_vanilla[0][-1], data_vanilla[1][-1]),
        textcoords="offset points",
        xytext=(0, 10),
        ha="center",
    )
    plt.annotate(
        f"{data_gen[1][-1]:.2f}s",
        (data_gen[0][-1], data_gen[1][-1]),
        textcoords="offset points",
        xytext=(0, 10),
        ha="center",
    )

    plt.tight_layout()
    plt.savefig(filename)
    print(f"\nBenchmark plot saved to {filename}")


async def main():
    print("Starting Vanilla Benchmark...")
    counts_v, runtimes_v = await benchmark_chunk_url()

    print("\nStarting Generator Benchmark...")
    counts_g, runtimes_g = await benchmark_chunk_url_generator()

    plot_results((counts_v, runtimes_v), (counts_g, runtimes_g), "bench_results.png")


if __name__ == "__main__":
    asyncio.run(main())
