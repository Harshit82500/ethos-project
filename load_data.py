import os
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from pymongo import MongoClient

# Load Environment
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Connections
w3 = Web3(Web3.HTTPProvider(os.getenv('ALCHEMY_URL')))
client = MongoClient("mongodb://localhost:27017/")
db = client["ethos_db"]
collection = db["raw_transactions"]

# Create an 'Index' in MongoDB so it doesn't allow duplicate Transaction Hashes
collection.create_index("hash", unique=True)

def fetch_bulk_data(num_blocks=10):
    if not w3.is_connected():
        print("❌ Failed to connect to Ethereum.")
        return

    # Get the starting point
    latest_block_num = w3.eth.block_number
    print(f"🚀 Starting Bulk Load from Block: {latest_block_num}")

    for i in range(num_blocks):
        target_block = latest_block_num - i
        print(f"📦 Fetching Block {target_block}...")
        
        block = w3.eth.get_block(target_block, full_transactions=True)
        
        processed_count = 0
        for tx in block.transactions:
            tx_data = dict(tx)
            
            # Clean the data for MongoDB
            for key, value in tx_data.items():
                if isinstance(value, bytes):
                    tx_data[key] = value.hex()
            
            try:
                # Insert and ignore if it's a duplicate
                collection.insert_one(tx_data)
                processed_count += 1
            except:
                pass # Skip duplicates silently
        
        print(f"✅ Saved {processed_count} transactions from block {target_block}")

if __name__ == "__main__":
    # Start small with 10 blocks, then you can increase to 100
    fetch_bulk_data(10)
    print("\n🎉 Bulk Load Complete! Your local database is growing.")