from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class BOMComponent(BaseModel):
    """Schema for a single component in the input BOM."""
    qty: int = Field(..., description="Quantity needed")
    description: str = Field(..., description="Part description")
    possible_mpn: Optional[str] = Field(None, description="Manufacturer part number (if known)")
    package: Optional[str] = Field(None, description="Package type")
    notes: Optional[str] = Field(None, description="Additional notes or source information")

class InputBOM(BaseModel):
    """Schema for the input BOM file."""
    project_name: str = Field(..., description="Project name")
    project_description: Optional[str] = Field(None, description="Optional project description")
    components: List[BOMComponent] = Field(..., description="List of components in the BOM")

class PotentialMatch(BaseModel):
    rank: int = Field(..., description="Rank assigned by LLM (1-5)")
    manufacturer_part_number: str = Field(..., description="Suggested Manufacturer Part Number")
    reason: Optional[str] = Field(None, description="LLM's reason for suggesting this part")
    selection_state: str = Field(..., description="Current state (proposed, selected, rejected)")
    mouser_part_number: Optional[str] = Field(None, description="Corresponding Mouser Part Number if found")
    manufacturer_name: Optional[str] = Field(None, description="Manufacturer Name")
    mouser_description: Optional[str] = Field(None, description="Mouser's description")
    datasheet_url: Optional[str] = Field(None, description="Datasheet URL")
    price: Optional[float] = Field(None, description="Unit price")
    availability: Optional[str] = Field(None, description="Availability information")
    component_id: Optional[int] = Field(None, description="Internal component DB ID, if applicable")

class MatchedComponent(BOMComponent):
    """Schema for a matched component, extending the base BOMComponent."""
    match_status: str = Field(..., description="Status of the match (e.g., 'exact', 'close', 'no_match')")
    mouser_part_number: Optional[str] = Field(None, description="Mouser part number")
    manufacturer_part_number: Optional[str] = Field(None, description="Manufacturer part number")
    manufacturer_name: Optional[str] = Field(None, description="Manufacturer name")
    mouser_description: Optional[str] = Field(None, description="Mouser's description of the part")
    datasheet_url: Optional[str] = Field(None, description="URL to the part's datasheet")
    price: Optional[float] = Field(None, description="Unit price in USD")
    availability: Optional[str] = Field(None, description="Number of parts available")
    potential_matches: Optional[List[PotentialMatch]] = Field(None, description="List of potential matches suggested by the LLM")

class MatchedBOM(BaseModel):
    """Schema for the matched BOM file."""
    project_name: str = Field(..., description="Project name")
    components: List[MatchedComponent] = Field(..., description="List of matched components")
    project_description: Optional[str] = Field(None, description="Project description")
    match_date: str = Field(..., description="ISO-8601 timestamp of when the match was performed")
    match_status: str = Field(..., description="Overall status of the BOM matching process") 