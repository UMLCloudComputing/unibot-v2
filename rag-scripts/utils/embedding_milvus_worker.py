from pymilvus import Collection
from flush_to_milvus import flush_to_milvus
from setup_milvus import setup_milvus

def embedding_milvus_worker(chunk_queue, num_producers, batch_size):
    """I/O-bound: Embeds via Ollama and saves to Milvus."""
    print("[INFO] Embedding/Milvus Worker started.") 

    # Create connection to Milvus DB
    collection = setup_milvus(is_worker=True)

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
            batch_data = []
    print(f"[INFO] Embedding/MilvusWorker shutting down. Total chunks inserted: {total_inserted}")
