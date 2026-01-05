# pip install pymilvus docling ollama

import multiprocessing as mp
import ollama
import time
from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker

from utils.setup_milvus import setup_milvus
from utils.docling_worker import docling_worker
from utils.embedding_milvus_worker import embedding_milvus_worker

# --- CONFIGURATION ---
MILVUS_HOST = "milvus"
MILVUS_PORT = "19530"
COLLECTION_NAME = "document_embeddings"
DIMENSION = 768  
BATCH_SIZE = 32

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add document vectors to Milvus DB from a file with a list of URLs")
    
    parser.add_argument(
        "--file",
        type=str,
        required=True,
        help="Path to the text file containing one source_url per line."
    )

    args = parser.parse_args()

    files_to_process = open(args.file)  
        
    num_parsers = mp.cpu_count() // 2 # Conservative use of CPU cores
    
    print(f"[INFO] Initializing ETL Pipeline with {num_parsers} parser(s)...")
    
    file_q = mp.Queue()
    chunk_q = mp.Queue()

    # Start Workers
    parsers = [mp.Process(target=docling_worker, args=(file_q, chunk_q, i)) for i in range(num_parsers)]
    for p in parsers: p.start()
    
    milvus_proc = mp.Process(target=embedding_milvus_worker, args=(chunk_q, num_parsers, BATCH_SIZE, COLLECTION_NAME))
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
