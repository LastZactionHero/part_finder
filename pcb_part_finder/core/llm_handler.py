"""Module for handling LLM (Anthropic Claude) interactions."""

import os
import re
from typing import List, Dict, Any, Optional
import anthropic
from google import genai
from google.genai import types

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

def get_llm_response_anthropic(prompt: str) -> Optional[str]:
    """Get a response from the Anthropic LLM.
    
    Args:
        prompt: The input prompt for the LLM.
        
    Returns:
        The LLM's response text.
        
    Raises:
        LlmApiError: If the API call fails.
    """
    model: str = "claude-3-sonnet-20240229"
    temperature: float = 0.2

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

def get_llm_response(prompt: str) -> Optional[str]:
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
    # return get_llm_response_anthropic(prompt, model, temperature)
    return get_llm_response_gemini(prompt)

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
Other Usage Notes: {part_info.get('Notes/Source', '')}

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

def format_evaluation_prompt(part_info: Dict[str, str], project_notes: str, bom_list: List[Dict[str, str]], mouser_results: List[Dict[str, Any]]) -> str:
    """
    Format the prompt for evaluating Mouser search results.
    
    Args:
        part_info: Dictionary containing part information from the input CSV for the current part.
        project_notes: Content of the project notes file.
        bom_list: List of all parts in the original Bill of Materials (BOM).
        mouser_results: List of Mouser search results for the current part.
        
    Returns:
        Formatted prompt string
    """
    # Format the original BOM list
    # Show Description, Package, and Possible MPN for context
    bom_list_str = "\n".join([
        f"- {part.get('Description', 'N/A')} (Package: {part.get('Package', 'N/A')}, MPN: {part.get('Possible MPN', 'N/A')})"
        for part in bom_list
    ]) if bom_list else "None"

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
    
    return f"""Here is a list of potential parts from Mouser for the original part described below. Your task is to evaluate this list and select the single best part that matches the requirements and context provided. Consider the other parts in the project listed in the BOM.

Original Part Details (Currently Evaluating):
Quantity: {part_info.get('Qty', '')}
Description: {part_info.get('Description', '')}
Possible MPN: {part_info.get('Possible MPN', '')}
Package: {part_info.get('Package', '')}
Notes/Source: {part_info.get('Notes/Source', '')}

Project Notes:
{project_notes}

Original Bill of Materials (BOM):
{bom_list_str}

Mouser Search Results:
{mouser_results_str}

When evaluating the Mouser parts, prioritize parts that are currently in stock or have a short lead time. The most important factor is that the selected part closely matches the requirements and specifications mentioned in the 'Notes/Source' field provided for the original part. Favor parts with readily available datasheets. Consider the manufacturer if project preferences are indicated in the 'Project Notes' or the overall 'Original Bill of Materials'. While important, price should be a secondary consideration after availability and functional suitability are established. Ensure the specifications and package of the selected part are compatible with the original requirement.

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

def get_gemini_client() -> Optional[genai.Client]:
    """Get the Gemini API client.
    
    Returns:
        An initialized Gemini client.
        
    Raises:
        LlmApiError: If the API key is not found.
    """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        raise LlmApiError("Gemini API key not found")
    return genai.Client(api_key=api_key)

def get_llm_response_gemini(prompt: str) -> Optional[str]:
    """Get a response from the Gemini LLM.
    
    Args:
        prompt: The input prompt for the LLM.
        
    Returns:
        The LLM's response text.
        
    Raises:
        LlmApiError: If the API call fails.
    """
    # model: str = "gemini-2.5-pro-preview-03-25"
    model: str = "gemini-2.5-flash-preview-04-17"
    temperature: float = 0.2
    client = get_gemini_client()
    if not client:
        raise LlmApiError("Gemini API key not found")
        
    try:
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            ),
        ]
        
        generate_content_config = types.GenerateContentConfig(
            response_mime_type="text/plain",
        )
        
        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=generate_content_config,
        )
        return response.text
    except Exception as e:
        raise LlmApiError(f"Gemini API error: {e}") 