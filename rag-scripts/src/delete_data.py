import os
import logging
from dotenv import load_dotenv
from tqdm import tqdm
from pymilvus import MilvusClient

load_dotenv()

# --- CONFIGURATION ---
MILVUS_HOST = os.getenv("MILVUS_HOST")
MILVUS_PORT = os.getenv("MILVUS_PORT")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
LOG_OUTPUT_PATH = os.getenv("LOG_OUTPUT_PATH")
OP_FILES_PATH = os.getenv("OP_FILES_PATH")

# Construct the URI for MilvusClient
MILVUS_URI = f"http://{MILVUS_HOST}:{MILVUS_PORT}"

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    handlers=[logging.FileHandler(os.path.join(LOG_OUTPUT_PATH, "data_deletion.log"))],
)


def delete_by_urls(file_path):
    # 1. Initialize MilvusClient
    client = MilvusClient(uri=MILVUS_URI)

    if not client.has_collection(COLLECTION_NAME):
        logging.error(f"Collection '{COLLECTION_NAME}' does not exist.")
        return

    # 2. Validate and Read URLs from the provided file path
    if not os.path.exists(file_path):
        logging.error(f"{file_path} does not exist.")
        return

    try:
        with open(file_path, "r") as f:
            urls = [line.strip() for line in f if line.strip()]
    except Exception as e:
        logging.error(f"Failed to read file: {e}")
        return

    if not urls:
        logging.info("No URLs found to delete. No action taken.")
        return

    logging.info(f"Found {len(urls)} URLs for deletion.")

    # 3. Batching
    batch_size = 50
    total_deleted = 0

    pbar = tqdm(total=len(urls), desc="Deleting from Milvus", unit="url")

    for i in range(0, len(urls), batch_size):
        batch = urls[i : i + batch_size]

        # 1. QUERY: Find the Primary Keys (IDs) for these URLs
        # MilvusClient supports list-based filtering directly in the filter string
        filter_expr = f"source_url in {batch}"

        try:
            results = client.query(
                collection_name=COLLECTION_NAME,
                filter=filter_expr,
                output_fields=["id"],
            )

            if results:
                # 2. DELETE: Use the IDs for deletion
                ids_to_delete = [res["id"] for res in results]

                try:
                    # MilvusClient delete returns info about the deletion
                    delete_res = client.delete(
                        collection_name=COLLECTION_NAME, ids=ids_to_delete
                    )
                    # Note: MilvusClient delete_count is often returned in a dict or as an attribute
                    # depending on the specific server version/SDK combo.
                    total_deleted += len(ids_to_delete)

                except Exception as e:
                    logging.error(f"Failed to delete batch starting at index {i}: {e}.")

        except Exception as e:
            logging.error(f"Milvus Query Error on batch {i}: {e}")

        finally:
            pbar.update(len(batch))

    pbar.close()

    # MilvusClient handles flushing/consistency differently;
    # usually, data is searchable immediately depending on consistency level.
    # We no longer need to explicitly call collection.flush() in most use cases.

    logging.info(
        f"Successfully processed deletion for {total_deleted} records found within {len(urls)} target URLs."
    )

    # Close the client connection
    client.close()


if __name__ == "__main__":
    # Ensure correct path joining
    input_file = os.path.join(OP_FILES_PATH, "to_delete.txt")
    delete_by_urls(input_file)
