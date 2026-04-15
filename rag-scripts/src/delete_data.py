import argparse
import os
import logging
from dotenv import load_dotenv
from tqdm import tqdm
from pymilvus import connections, Collection, utility

load_dotenv()

# --- CONFIGURATION ---
MILVUS_HOST = os.getenv("MILVUS_HOST")
MILVUS_PORT = os.getenv("MILVUS_PORT")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
LOG_OUTPUT_PATH = os.getenv("LOG_OUTPUT_PATH")
OP_FILES_PATH = os.getenv("OP_FILES_PATH")

# Setup Logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(levelname)s: %(message)s',
    handlers=[logging.FileHandler(LOG_OUTPUT_PATH + "data_deletion.log")]
)

def delete_by_urls(file_path):
    # 1. Connect to Milvus
    connections.connect("default", host=MILVUS_HOST, port=MILVUS_PORT)

    if not utility.has_collection(COLLECTION_NAME):
        logging.error(f"Collection '{COLLECTION_NAME}' does not exist.")
        return

    # 2. Validate and Read URLs from the provided file path
    if not os.path.exists(file_path):
        logging.error(f"{file_path} does not exist.")
        return

    try:
        with open(file_path, 'r') as f:
            # Strip whitespace and ignore empty lines
            urls = [line.strip() for line in f if line.strip()]
    except Exception as e:
        logging.error(f"Failed to read file: {e}")
        return

    if not urls:
        logging.info("No URLs found to delete. No action taken.")
        return

    logging.info(f"Found {len(urls)} URLs for deletion.")

    # 3. Access and Load Collection
    collection = Collection(COLLECTION_NAME)
    collection.load() # Required for querying

    # 4. Batching
    batch_size=50
    total_deleted=0

    pbar = tqdm(total=len(urls), desc="Deleting from Milvus", unit="url")    
    
    for i in range(0, len(urls), batch_size):
        batch = urls[i:i + batch_size]
        formatted_urls = ", ".join([f'"{url}"' for url in batch])
        
        # 1. QUERY: Find the Primary Keys (IDs) for these URLs
        query_expr = f"source_url in [{formatted_urls}]"
        try:
            results = collection.query(
                expr=query_expr, 
                output_fields=["id"]
            )
        
            if results:
                # 2. DELETE: Use the IDs for the fast-lane deletion
                ids = [res["id"] for res in results]
            
                # Construct the ID-based expression
                id_expr = f"id in {ids}"
        
                try:
                    delete_res = collection.delete(expr=id_expr)
                    total_deleted += delete_res.delete_count
        
                except Exception as e:
                    logging.error(f"Failed to delete batch starting at index {i}: {e}.")
       
        except Exception as e:
            logging.error(f"Milvus Query Error on batch {i}: {e}")
    
        finally:
            pbar.update(len(batch))
     
    pbar.close()
    logging.info(f"Persisting changes (flushing)...")
    collection.flush()
    logging.info(f"Successfully deleted {total_deleted} records from {len(urls)} target URLs.")

if __name__ == "__main__":
    # Execute the deletion logic
    delete_by_urls(OP_FILES_PATH + "to_delete.txt")
