from typing import Optional
from pydantic import BaseModel, Field

class BOMComponent(BaseModel):
    """Schema for a single component in the input BOM."""
    qty: int = Field(..., description="Quantity needed")
    description: str = Field(..., description="Part description")
    possible_mpn: Optional[str] = Field(None, description="Manufacturer part number (if known)")
    package: str = Field(..., description="Package type")
    notes: Optional[str] = Field(None, description="Additional notes or source information")

class InputBOM(BaseModel):
    """Schema for the input BOM file."""
    components: list[BOMComponent] = Field(..., description="List of components in the BOM")
    project_description: Optional[str] = Field(None, description="Optional project description")

class MatchedComponent(BOMComponent):
    """Schema for a matched component, extending the base BOMComponent."""
    mouser_part_number: Optional[str] = Field(None, description="Mouser part number")
    manufacturer_part_number: Optional[str] = Field(None, description="Manufacturer part number")
    manufacturer_name: Optional[str] = Field(None, description="Manufacturer name")
    mouser_description: Optional[str] = Field(None, description="Mouser's description of the part")
    datasheet_url: Optional[str] = Field(None, description="URL to the part's datasheet")
    price: Optional[float] = Field(None, description="Unit price in USD")
    availability: Optional[str] = Field(None, description="Number of parts available")
    match_status: Optional[str] = Field(None, description="Status of the match (e.g., 'exact', 'close', 'no_match')")

class MatchedBOM(BaseModel):
    """Schema for the matched BOM file."""
    components: list[MatchedComponent] = Field(..., description="List of matched components")
    project_description: Optional[str] = Field(None, description="Project description")
    match_date: str = Field(..., description="ISO-8601 timestamp of when the match was performed")
    match_status: str = Field(..., description="Overall status of the BOM matching process") 