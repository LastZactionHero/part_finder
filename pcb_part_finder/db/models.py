from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey, DECIMAL, Index
from sqlalchemy.orm import relationship
import datetime
from typing import List

from .session import Base

class Project(Base):
    """
    SQLAlchemy model for the projects table.
    Represents a BOM analysis project.
    """
    __tablename__ = 'projects'

    project_id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    email = Column(String(255), nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    status = Column(String(50))
    start_time = Column(TIMESTAMP, nullable=True)
    end_time = Column(TIMESTAMP, nullable=True)

    # Relationship to BOM items
    bom_items = relationship(
        "BomItem",
        back_populates="project",
        cascade="all, delete-orphan"
    )

class BomItem(Base):
    """
    SQLAlchemy model for the bom_items table.
    Represents a single component in a BOM.
    """
    __tablename__ = 'bom_items'

    bom_item_id = Column(Integer, primary_key=True)
    project_id = Column(String(36), ForeignKey('projects.project_id'))
    quantity = Column(Integer)
    description = Column(Text)
    package = Column(String(255))
    notes = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)

    # Relationship back to project
    project = relationship("Project", back_populates="bom_items")
    
    # Relationship to matches
    matches = relationship("BomItemMatch", back_populates="bom_item")

class Component(Base):
    """
    SQLAlchemy model for the components table.
    Represents a matched component from Mouser.
    """
    __tablename__ = 'components'
    __table_args__ = (
        Index('idx_components_mouser_part_number', 'mouser_part_number'),
        Index('idx_components_manufacturer_part_number', 'manufacturer_part_number'),
    )

    component_id = Column(Integer, primary_key=True)
    mouser_part_number = Column(String(255), unique=True, index=True)
    manufacturer_part_number = Column(String(255), index=True, nullable=True)
    manufacturer_name = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    datasheet_url = Column(Text, nullable=True)
    package = Column(String(255), nullable=True)
    price = Column(DECIMAL(10, 2), nullable=True)
    availability = Column(String(50), nullable=True)
    last_updated = Column(
        TIMESTAMP,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow
    )

    # Relationship to matches
    matches = relationship("BomItemMatch", back_populates="component")

class BomItemMatch(Base):
    """
    SQLAlchemy model for the bom_item_matches table.
    Represents a match between a BOM item and a component.
    """
    __tablename__ = 'bom_item_matches'
    __table_args__ = (
        Index('idx_bom_item_matches_bom_item_id', 'bom_item_id'),
        Index('idx_bom_item_matches_component_id', 'component_id'),
    )

    match_id = Column(Integer, primary_key=True)
    bom_item_id = Column(Integer, ForeignKey('bom_items.bom_item_id'), index=True)
    component_id = Column(Integer, ForeignKey('components.component_id'), index=True, nullable=True)
    match_status = Column(String(50))
    matched_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)

    # Relationships
    bom_item = relationship("BomItem", back_populates="matches")
    component = relationship("Component", back_populates="matches") 