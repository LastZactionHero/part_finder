-- Add component_id column to potential_bom_matches table
ALTER TABLE potential_bom_matches 
ADD COLUMN component_id INTEGER REFERENCES components(component_id);

-- Create index for the new column
CREATE INDEX idx_potential_bom_matches_component_id ON potential_bom_matches(component_id);

-- Rebuild relationships in case there are existing records needing updates
-- This command would be run separately after component_id is backfilled:
-- UPDATE potential_bom_matches pbm
-- SET component_id = c.component_id
-- FROM components c
-- WHERE c.manufacturer_part_number = pbm.manufacturer_part_number
-- AND pbm.component_id IS NULL; 