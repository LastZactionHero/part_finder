"""Module for handling parts cache using Pinecone DB."""

import os
import json
from pinecone import Pinecone
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from pcb_part_finder.core.llm_handler import get_llm_response

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
    return None
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

def search_cache(search_term: str, threshold: float = 0.5) -> Optional[Dict[str, Any]]:
    """Search for parts in the cache.
    
    Args:
        search_term: The search term to look for
        threshold: Similarity threshold (default: 0.5)
        
    Returns:
        Dictionary containing part information if found, None otherwise
    """
    print(f"Searching cache for: {search_term}")
    return None
    
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
    
    # Get the best match
    best_match = results.matches[0]
    print(f"Best match score: {best_match.score}, threshold: {threshold}")
    if best_match.score < threshold:
        print("Score is below threshold, returning None")
        return None

    print(f"Found potential match with score: {best_match.score}")
    
    # Use LLM to validate the match
    validation_prompt = f"""I am looking for electronic parts that match a specific search term. I've found a potential match in our cached database of Mouser API responses, but I need your help to validate if it's a good fit.

Original search term: {search_term}
Cached search term: {best_match.metadata['search_term']}
Cached part data: {best_match.metadata['part_data']}

Please analyze if this part is a good match for the original search term. Consider:
1. If the part's specifications match what was being searched for
2. If the part's description and attributes align with the search intent
3. If there are any significant mismatches that would make this an unsuitable match

Return ONLY either 'YES_MATCH' or 'NO_MATCH' based on your analysis."""

    try:
        llm_response = get_llm_response(validation_prompt)
        is_match = llm_response.strip().upper() == 'YES_MATCH'
        
        if not is_match:
            print("LLM validation determined this is not a good match")
            return None
            
        print("LLM validation confirmed this is a good match")
        return json.loads(best_match.metadata['part_data'])
        
    except Exception as e:
        print(f"Error during LLM validation: {e}")
        return None 