# pip install pymilvus docling ollama

import multiprocessing as mp
import ollama
import time
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker

# --- CONFIGURATION ---
MILVUS_HOST = "milvus"
MILVUS_PORT = "19530"
COLLECTION_NAME = "document_embeddings"
DIMENSION = 768  
BATCH_SIZE = 32

def setup_milvus():
    print(f"[INFO] Connecting to Milvus at {MILVUS_HOST}:{MILVUS_PORT}...")
    connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)
    
    if not utility.has_collection(COLLECTION_NAME):
        print(f"[INFO] Collection '{COLLECTION_NAME}' not found. Creating new schema...")
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="source_url", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=DIMENSION)
        ]
        schema = CollectionSchema(fields, "Document chunks from Docling")
        collection = Collection(COLLECTION_NAME, schema)
        
        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128},
        }
        print(f"[INFO] Creating index on '{COLLECTION_NAME}'...")
        collection.create_index(field_name="vector", index_params=index_params)
    else:
        print(f"[INFO] Existing collection '{COLLECTION_NAME}' found.")
        collection = Collection(COLLECTION_NAME)
    
    collection.load()
    print(f"[INFO] Milvus collection loaded and ready.")
    return collection

def docling_worker(file_queue, chunk_queue, worker_id):
    """CPU-bound: Parses files."""
    print(f"[INFO] Docling Worker-{worker_id} started.")
    converter = DocumentConverter()
    chunker = HybridChunker()

    while True:
        file_path = file_queue.get()
        if file_path is None:
            print(f"[INFO] Docling Worker-{worker_id} received shutdown signal.")
            chunk_queue.put(None)
            break
        
        print(f"[INFO] Worker-{worker_id} parsing: {file_path}")
        start_time = time.time()
        try:
            result = converter.convert(file_path)
            chunks = list(chunker.chunk(result.document))
            
            for chunk in chunks:
                chunk_queue.put({
                    "text": chunk.text,
                    "source_url": file_path
                })
            
            elapsed = time.time() - start_time
            print(f"[INFO] Worker-{worker_id} finished {file_path} ({len(chunks)} chunks) in {elapsed:.2f}s")
        except Exception as e:
            print(f"[ERROR] Worker-{worker_id} failed on {file_path}: {e}")

def embedding_milvus_worker(chunk_queue, num_producers, batch_size):
    """I/O-bound: Embeds via Ollama and saves to Milvus."""
    print("[INFO] Embedding/Milvus Worker started.")
    collection = setup_milvus()
    batch_data = []
    finished_producers = 0
    total_inserted = 0
    
    while True:
        item = chunk_queue.get()
        
        if item is None:
            finished_producers += 1
            if finished_producers == num_producers:
                if batch_data:
                    flush_to_milvus(collection, batch_data)
                    total_inserted += len(batch_data)
                break
            continue

        batch_data.append(item)

        if len(batch_data) >= batch_size:
            flush_to_milvus(collection, batch_data)
            total_inserted += len(batch_data)
            batch_data = []

    print(f"[INFO] Embedding/Milvus Worker shutting down. Total chunks inserted: {total_inserted}")

def flush_to_milvus(collection, batch):
    """Logic for Ollama API call and Milvus insertion."""
    texts = [item["text"] for item in batch]
    urls = [item["source_url"] for item in batch]
    
    print(f"[INFO] Requesting embeddings from Ollama for batch of {len(batch)}...")
    try:
        start_time = time.time()
        response = ollama.embed(model='nomic-embed-text', input=texts)
        embeddings = response['embeddings']
        
        data = [urls, texts, embeddings]
        collection.insert(data)
        
        elapsed = time.time() - start_time
        print(f"[INFO] Successfully inserted {len(batch)} vectors to Milvus in {elapsed:.2f}s")
    except Exception as e:
        print(f"[ERROR] Batch processing failed: {e}")

if __name__ == "__main__":
    files_to_process = ["doc1.pdf", "doc2.pdf"] # Replace with your targets
    num_parsers = mp.cpu_count() // 2 # Conservative use of CPU cores
    
    print(f"[INFO] Initializing ETL Pipeline with {num_parsers} parser(s)...")
    
    file_q = mp.Queue()
    chunk_q = mp.Queue()

    # Start Workers
    parsers = [mp.Process(target=docling_worker, args=(file_q, chunk_q, i)) for i in range(num_parsers)]
    for p in parsers: p.start()
    
    milvus_proc = mp.Process(target=embedding_milvus_worker, args=(chunk_q, num_parsers, BATCH_SIZE))
    milvus_proc.start()

    # Load work
    for f in files_to_process:
        file_q.put(f)
    
    # Send shutdown signals
    for _ in range(num_parsers):
        file_q.put(None)

    # Join
    for p in parsers: p.join()
    milvus_proc.join()
    print("[INFO] Pipeline execution finished successfully.")
