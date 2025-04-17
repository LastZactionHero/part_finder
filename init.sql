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

-- Create indexes for better performance
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_bom_items_project_id ON bom_items(project_id);
CREATE INDEX idx_components_mouser_part_number ON components(mouser_part_number);
CREATE INDEX idx_components_manufacturer_part_number ON components(manufacturer_part_number);
CREATE INDEX idx_bom_item_matches_bom_item_id ON bom_item_matches(bom_item_id);
CREATE INDEX idx_bom_item_matches_component_id ON bom_item_matches(component_id); 