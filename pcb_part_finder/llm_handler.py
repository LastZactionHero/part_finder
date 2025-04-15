"""Module for handling LLM (Anthropic Claude) interactions."""

import os
import re
from typing import List, Dict, Any, Optional
import anthropic

class LlmApiError(Exception):
    """Custom exception for LLM API errors."""
    pass

def get_anthropic_client() -> Optional[anthropic.Anthropic]:
    """Get the Anthropic API client.
    
    Returns:
        An initialized Anthropic client.
        
    Raises:
        LlmApiError: If the API key is not found.
    """
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise LlmApiError("Anthropic API key not found")
    return anthropic.Anthropic(api_key=api_key)

def get_llm_response(prompt: str, model: str = "claude-3-sonnet-20240229", temperature: float = 0.2) -> Optional[str]:
    """Get a response from the LLM.
    
    Args:
        prompt: The input prompt for the LLM.
        model: The model to use (default: claude-3-sonnet-20240229).
        temperature: The temperature parameter (default: 0.2).
        
    Returns:
        The LLM's response text.
        
    Raises:
        LlmApiError: If the API call fails.
    """
    client = get_anthropic_client()
    if not client:
        raise LlmApiError("Anthropic API key not found")
        
    try:
        response = client.messages.create(
            model=model,
            max_tokens=500,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except anthropic.APIError as e:
        raise LlmApiError(f"Anthropic API error: {e}")

def format_search_term_prompt(part_info: Dict[str, str]) -> str:
    """Format the prompt for generating search terms.
    
    Args:
        part_info: Dictionary containing part information from the input CSV.
        
    Returns:
        The formatted prompt string.
    """
    return f"""Your task is to generate a small number of diverse search terms (approximately 3) for finding electronic components on Mouser.com based on the following input fields: 'Description', 'Possible MPN', and 'Package'. The goal is to create search terms that are likely to yield relevant results. Consider the following strategies when generating these terms:

1. Prioritize the 'Possible MPN': If a 'Possible MPN' is provided, use it as one of the search terms, ideally as an exact match.
2. Create concise keyword-based searches from the 'Description', focusing on the most important features and component type.
3. Combine keywords from the 'Description' with the 'Package' information to narrow or broaden the search effectively. For example, if the description mentions a type of IC and the package is 'SMD', include 'SMD' in one of the search terms.
4. Vary the level of detail in the generated search terms. Some should be more specific, while others should be broader to capture a wider range of potential matches.
5. Consider common abbreviations or alternative names for components or packages if they are likely to be used in Mouser's search.

Here is the input for the current part:
Description: {part_info.get('Description', '')}
Possible MPN: {part_info.get('Possible MPN', '')}
Package: {part_info.get('Package', '')}

Generate the search terms as a comma-separated list."""

def parse_search_terms(llm_response: Optional[str]) -> List[str]:
    """Parse search terms from the LLM response.
    
    Args:
        llm_response: The raw response string from the LLM.
        
    Returns:
        A list of search terms.
    """
    if not llm_response:
        return []
    
    # Split by comma and clean up each term
    terms = [term.strip() for term in llm_response.split(',')]
    # Remove empty terms
    return [term for term in terms if term]

def format_product_attribute(attr: Dict[str, Any]) -> str:
    """Format a single product attribute as a string."""
    name = attr.get('AttributeName', '')
    value = attr.get('AttributeValue', '')
    return f"{name}: {value}"

def format_evaluation_prompt(part_info: Dict[str, str], project_notes: str, selected_parts: List[Dict[str, str]], mouser_results: List[Dict[str, Any]]) -> str:
    """
    Format the prompt for evaluating Mouser search results.
    
    Args:
        part_info: Dictionary containing part information from the input CSV
        project_notes: Content of the project notes file
        selected_parts: List of previously selected parts
        mouser_results: List of Mouser search results
        
    Returns:
        Formatted prompt string
    """
    print("Here!")
    print(selected_parts)
    # Format selected parts
    selected_parts_str = "\n".join([
        f"{part['Description']}: {part['Manufacturer Part Number']}"
        for part in selected_parts
    ]) if selected_parts else "None"
    print("Here2!")

    print(mouser_results[0])
    # Format Mouser results
    mouser_results_str = "\n\n".join([
        f"Manufacturer: {part.get('Manufacturer', 'N/A')}\n"
        f"Manufacturer Part Number: {part.get('ManufacturerPartNumber', 'N/A')}\n"
        f"Mouser Part Number: {part.get('MouserPartNumber', 'N/A')}\n"
        f"Description: {part.get('Description', 'N/A')}\n"
        f"Price: {part.get('Price', 'N/A')}\n" 
        f"Availability: {part.get('Availability', 'N/A')}\n"
        f"Datasheet URL: {part.get('DataSheetUrl', 'N/A')}\n"
        f"Product Attributes: N/A"
        for part in mouser_results
    ])
    print("There!")
    
    return f"""Here is a list of potential parts from Mouser for the original part described below. Your task is to evaluate this list and select the single best part that matches the requirements and context provided.

Original Part Details:
Quantity: {part_info.get('Qty', '')}
Description: {part_info.get('Description', '')}
Possible MPN: {part_info.get('Possible MPN', '')}
Package: {part_info.get('Package', '')}
Notes/Source: {part_info.get('Notes/Source', '')}

Project Notes:
{project_notes}

Previously Selected Parts:
{selected_parts_str}

Mouser Search Results:
{mouser_results_str}

When evaluating the Mouser parts, prioritize parts that are currently in stock or have a short lead time. The most important factor is that the selected part closely matches the requirements and specifications mentioned in the 'Notes/Source' field provided for the original part. Favor parts with readily available datasheets. Consider the manufacturer if project preferences are indicated in the 'Project Notes' or 'Previously Selected Parts'. While important, price should be a secondary consideration after availability and functional suitability are established. Ensure the specifications and package of the selected part are compatible with the original requirement.

Return your answer in the following format so it can be easily parsed. Use EXACTLY the Manufacturer Part Number as shown in the list above, do not add manufacturer name or any other text:
[ManufacturerPartNumber:XXXXX]"""

def extract_mpn_from_eval(llm_response: Optional[str]) -> Optional[str]:
    """
    Extract the Manufacturer Part Number from the LLM evaluation response.
    
    Args:
        llm_response: The raw response from the LLM
        
    Returns:
        The extracted MPN, or None if not found
    """
    if not llm_response:
        return None
        
    match = re.search(r'\[ManufacturerPartNumber:(.*?)\]', llm_response)
    if match:
        return match.group(1).strip()
    return None 