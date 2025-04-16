"""Module for handling parts cache using Pinecone DB."""

import os
import json
from pinecone import Pinecone
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

print("Initializing parts cache module...")

# Load environment variables
load_dotenv()
print("Environment variables loaded")

# Initialize Pinecone
PINECONE_API_KEY = os.getenv('PINECONE_DB_API_KEY')
PINECONE_INDEX_NAME = "mouserparts"

print(f"Pinecone configuration: Index={PINECONE_INDEX_NAME}")

# Initialize Pinecone client
pc = Pinecone(api_key=PINECONE_API_KEY)
print("Pinecone client initialized")

def save_to_cache(part_data: Dict[str, Any], search_term: str) -> None:
    """Save part data to Pinecone cache.
    
    Args:
        part_data: Dictionary containing part information
        search_term: The search term used to find this part
    """
    print(f"Saving part to cache. Search term: {search_term}")
    print(f"Part data keys: {list(part_data.keys())}")
    
    # Create a unique ID for the part
    part_id = f"{part_data.get('MouserPartNumber', '')}_{part_data.get('ManufacturerPartNumber', '')}"
    print(f"Generated part ID: {part_id}")
    
    # Get the index
    index = pc.Index(PINECONE_INDEX_NAME)
    
    # Generate embedding using Pinecone's built-in embedding
    embedding = pc.inference.embed(
        model="llama-text-embed-v2",
        inputs=[search_term],
        parameters={
            "input_type": "passage"
        }
    )[0]
    
    # Prepare metadata
    metadata = {
        'part_data': json.dumps(part_data),
        'search_term': search_term
    }
    
    # Upsert to Pinecone
    print("Upserting to Pinecone...")
    index.upsert(
        vectors=[{
            "id": part_id,
            "values": embedding.values,
            "metadata": metadata
        }]
    )
    print("Successfully saved to cache")

def search_cache(search_term: str, threshold: float = 0.6) -> Optional[Dict[str, Any]]:
    """Search for parts in the cache.
    
    Args:
        search_term: The search term to look for
        threshold: Similarity threshold (default: 0.6)
        
    Returns:
        Dictionary containing part information if found, None otherwise
    """
    print(f"Searching cache for: {search_term} (threshold: {threshold})")
    
    # Get the index
    index = pc.Index(PINECONE_INDEX_NAME)
    
    # Generate embedding using Pinecone's built-in embedding
    embedding = pc.inference.embed(
        model="llama-text-embed-v2",
        inputs=[search_term],
        parameters={
            "input_type": "query"
        }
    )[0]
    
    # Search in Pinecone
    print("Querying Pinecone...")
    results = index.query(
        vector=embedding.values,
        top_k=1,
        include_values=False,
        include_metadata=True
    )
    
    if not results.matches:
        print("No matches found in cache")
        return None
    
    # Check if the best match meets the threshold
    best_match = results.matches[0]
    print(f"Best match score: {best_match.score}")
    
    if best_match.score < threshold:
        print(f"Best match score {best_match.score} below threshold {threshold}")
        return None
    
    print("Found matching part in cache")
    # Return the cached part data
    return json.loads(best_match.metadata['part_data']) 