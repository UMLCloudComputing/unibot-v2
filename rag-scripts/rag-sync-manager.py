import sqlite3
import hashlib
import requests
import logging
import os
from dotenv import load_dotenv
from tqdm import tqdm
from datetime import datetime

load_dotenv()

# --- Configuration ---
URL_LIST_FILE = os.getenv('URL_LIST_FILE')
LOG_OUTPUT_PATH = os.getenv('LOG_OUTPUT_PATH')
OP_FILES_PATH = os.getenv('OP_FILES_PATH')

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(LOG_OUTPUT_PATH + "rag_sync.log")]
)

def get_content_hash(url):
    """Fetches URL content and returns a SHA-256 hash."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return hashlib.sha256(response.text.encode('utf-8')).hexdigest()
    except Exception as e:
        logging.error(f"FETCH_ERROR: {url} | {e}")
        return None

def write_action_file(filepath, url_list):
    """Writes a list of URLs to a text file for downstream processing."""
    try:
        with open(filepath, 'w') as f:
            for url in url_list:
                f.write(f"{url}\n")
        logging.info(f"FILE_EXPORT: Created '{filepath}' with {len(url_list)} entries.")
    except Exception as e:
        logging.error(f"EXPORT_ERROR: Failed to write {filepath} | {e}")

def sync_rag_state():
    logging.info("START: Comparing source links against database state...")
    
    conn = sqlite3.connect(OP_FILES_PATH + "rag_tracker.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS url_tracker 
                      (url TEXT PRIMARY KEY, content_hash TEXT, last_updated DATETIME)''')

    # Load Source File
    try:
        with open(URL_LIST_FILE, 'r') as f:
            current_urls = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logging.error(f"CRITICAL: {URL_LIST_FILE} not found.")
        return

    # Load DB State
    cursor.execute("SELECT url, content_hash FROM url_tracker")
    db_state = {row[0]: row[1] for row in cursor.fetchall()}

    to_delete = []
    to_add = []

    # Identify Adds and Hash-based Updates
    print(f"Syncing {len(current_urls)} URLs...")
    for url in tqdm(current_urls, desc="Checking Content", unit="url"):
        new_hash = get_content_hash(url)
        if not new_hash: continue

        if url not in db_state:
            logging.info(f"ACTION: ADD detected for {url}")
            to_add.append(url)
            cursor.execute("INSERT INTO url_tracker VALUES (?, ?, ?)", (url, new_hash, datetime.now().isoformat()))
        elif db_state[url] != new_hash:
            logging.info(f"ACTION: UPDATE (Delete-then-Add) detected for {url}")
            to_delete.append(url)
            to_add.append(url)
            cursor.execute("UPDATE url_tracker SET content_hash = ?, last_updated = ? WHERE url = ?", (new_hash, datetime.now().isoformat(), url))
        else:
            logging.info(f"SKIP: No changes for {url}")

    # Identify URLs removed from source file
    for url in db_state:
        if url not in current_urls:
            logging.info(f"ACTION: REMOVE detected for {url}")
            to_delete.append(url)
            cursor.execute("DELETE FROM url_tracker WHERE url = ?", (url,))

    conn.commit()
    conn.close()

    # Write the result files
    write_action_file(OP_FILES_PATH + "to_delete.txt", to_delete)
    write_action_file(OP_FILES_PATH + "to_add.txt", to_add)
    
    logging.info("FINISH: Process complete.")
    print(f"\nSync Complete.")
    print(f" - To Add/Update: {len(to_add)}")
    print(f" - To Delete: {len(to_delete)}")
    print(f"Check {OP_FILES_PATH}/to_add.txt and {OP_FILES_PATH}/to_delete for details.")

if __name__ == "__main__":
    sync_rag_state()
