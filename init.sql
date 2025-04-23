-- Create tables
CREATE TABLE projects (
    project_id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    email VARCHAR(255),
    created_at TIMESTAMP,
    status VARCHAR(50),
    start_time TIMESTAMP,
    end_time TIMESTAMP
);

CREATE TABLE bom_items (
    bom_item_id SERIAL PRIMARY KEY,
    project_id VARCHAR(36) REFERENCES projects(project_id),
    quantity INTEGER,
    description TEXT,
    package VARCHAR(255),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE components (
    component_id SERIAL PRIMARY KEY,
    mouser_part_number VARCHAR(255) UNIQUE,
    manufacturer_part_number VARCHAR(255),
    manufacturer_name VARCHAR(255),
    description TEXT,
    datasheet_url TEXT,
    package VARCHAR(255),
    price DECIMAL(10,2),
    availability VARCHAR(50),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE bom_item_matches (
    match_id SERIAL PRIMARY KEY,
    bom_item_id INTEGER REFERENCES bom_items(bom_item_id),
    component_id INTEGER REFERENCES components(component_id),
    match_status VARCHAR(50),
    matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE mouser_api_cache (
    cache_id SERIAL PRIMARY KEY,
    search_term TEXT NOT NULL,
    search_type VARCHAR(50) NOT NULL, -- e.g., 'keyword', 'mpn'
    response_data JSONB, -- stores the raw JSON response from Mouser
    cached_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_bom_items_project_id ON bom_items(project_id);
CREATE INDEX idx_components_mouser_part_number ON components(mouser_part_number);
CREATE INDEX idx_components_manufacturer_part_number ON components(manufacturer_part_number);
CREATE INDEX idx_bom_item_matches_bom_item_id ON bom_item_matches(bom_item_id);
CREATE INDEX idx_bom_item_matches_component_id ON bom_item_matches(component_id);

CREATE UNIQUE INDEX idx_mouser_cache_term_type ON mouser_api_cache (search_term, search_type);
CREATE INDEX idx_mouser_cache_cached_at ON mouser_api_cache (cached_at);

-- Create table for potential BOM matches
CREATE TABLE potential_bom_matches (
    potential_match_id SERIAL PRIMARY KEY,
    bom_item_id INTEGER REFERENCES bom_items(bom_item_id),
    component_id INTEGER REFERENCES components(component_id),
    rank INTEGER NOT NULL,
    manufacturer_part_number VARCHAR(255) NOT NULL,
    reason TEXT,
    selection_state VARCHAR(50) NOT NULL DEFAULT 'proposed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for potential_bom_matches
CREATE INDEX idx_potential_bom_matches_bom_item_id ON potential_bom_matches (bom_item_id);
CREATE INDEX idx_potential_bom_matches_component_id ON potential_bom_matches (component_id); 