from dotenv import load_dotenv
from add_data_utils import chunk_url_sync, embedder_sync, milvus_worker
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from threading import Event
from pymilvus import MilvusClient, DataType
import os
import logging

_ = load_dotenv()

OP_FILES_PATH = os.getenv("OP_FILES_PATH", "data/")
DOCLING_BASE_URL = os.getenv("DOCLING_BASE_URL", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "")
MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = os.getenv("MILVUS_PORT", "19530")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "docs")
LOG_OUTPUT_PATH = os.getenv("LOG_OUTPUT_PATH", "logs/")


NUM_CHUNKERS = 10
NUM_EMBEDDERS = 5
NUM_INSERTERS = 5
BATCH_SIZE = 1024
DIMENSION = 768

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(threadName)s - %(message)s",
    handlers=[logging.FileHandler(LOG_OUTPUT_PATH + "add_data_t.log")],
)


def setup_milvus(
    host=MILVUS_HOST,
    port=MILVUS_PORT,
    collection_name=COLLECTION_NAME,
    dimension=DIMENSION,
):
    """
    Main Thread: Ensures collection exists, is indexed, and is loaded into memory.
    """
    client = MilvusClient(uri=f"http://{host}:{port}")

    if not client.has_collection(collection_name):
        schema = client.create_schema(auto_id=True, enable_dynamic_field=False)

        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True)
        schema.add_field(
            field_name="source_url", datatype=DataType.VARCHAR, max_length=512
        )
        schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)
        schema.add_field(
            field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=dimension
        )

        index_params = client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            metric_type="L2",
            index_type="IVF_FLAT",
            params={"nlist": 128},
        )

        client.create_collection(
            collection_name=collection_name, schema=schema, index_params=index_params
        )

    client.load_collection(collection_name)
    client.close()  # Close management connection


def main():

    url_queue = Queue()
    chunk_queue = Queue()
    embedding_queue = Queue()

    chunking_pool = ThreadPoolExecutor(NUM_CHUNKERS, "Chunker")
    embedding_pool = ThreadPoolExecutor(NUM_EMBEDDERS, "Embedder")
    inserter_pool = ThreadPoolExecutor(NUM_INSERTERS, "Inserter")

    with open(OP_FILES_PATH + "to_add.txt", "r") as f:
        for line in f:
            url_queue.put(line.strip())

    total_docs = url_queue.qsize()

    chunk_pbar = tqdm(
        total=total_docs, desc="[1/3] Chunking with Docling", unit="url", position=0
    )
    embedding_pbar = tqdm(
        total=None, desc="[2/3] Generating Embeddings", unit="chunk", position=1
    )
    milvus_pbar = tqdm(
        total=None, desc="[3/3] Inserting into Milvus", unit="chunk", position=2
    )

    embedder_stop_event = Event()

    setup_milvus()

    # Start chunking threads
    for _ in range(NUM_CHUNKERS):
        chunking_pool.submit(
            chunk_url_sync, DOCLING_BASE_URL, url_queue, chunk_queue, chunk_pbar
        )

    # Start embedding threads
    for _ in range(NUM_EMBEDDERS):
        embedding_pool.submit(
            embedder_sync,
            OLLAMA_BASE_URL,
            chunk_queue,
            embedding_queue,
            BATCH_SIZE,
            embedding_pbar,
        )

    # Start inserter threads
    for _ in range(NUM_INSERTERS):
        inserter_pool.submit(
            milvus_worker,
            embedding_queue,
            MILVUS_HOST,
            MILVUS_PORT,
            COLLECTION_NAME,
            embedder_stop_event,
            milvus_pbar,
        )

    # Threads should complete on their own once the queue is empty
    chunking_pool.shutdown(wait=True)
    embedding_pool.shutdown(wait=True)
    embedder_stop_event.set()
    inserter_pool.shutdown(wait=True)
    chunk_pbar.close()
    embedding_pbar.close()
    milvus_pbar.close()


if __name__ == "__main__":
    main()
