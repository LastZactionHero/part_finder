#!/usr/bin/env python3

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from pcb_part_finder.core.data_loader import load_project_data_from_db
from pcb_part_finder.db.models import Project, BomItem

def test_load_project_data_from_db_success():
    """Test successful loading of project and BOM data."""
    # Setup mock data
    mock_project = Mock(spec=Project)
    mock_project.project_id = "test-project"
    
    mock_bom_items = [
        Mock(spec=BomItem),
        Mock(spec=BomItem)
    ]
    
    # Setup mock session
    mock_session = Mock(spec=Session)
    mock_session.query.return_value.filter.return_value.first.return_value = mock_project
    mock_session.query.return_value.filter.return_value.all.return_value = mock_bom_items
    
    # Call the function
    project, bom_items = load_project_data_from_db("test-project", mock_session)
    
    # Verify results
    assert project == mock_project
    assert bom_items == mock_bom_items
    
    # Verify database queries
    mock_session.query.assert_called()
    assert mock_session.query.call_count == 2  # Called once for project, once for BOM items

def test_load_project_data_from_db_project_not_found():
    """Test handling of non-existent project."""
    # Setup mock session
    mock_session = Mock(spec=Session)
    mock_session.query.return_value.filter.return_value.first.return_value = None
    
    # Call the function
    project, bom_items = load_project_data_from_db("non-existent", mock_session)
    
    # Verify results
    assert project is None
    assert bom_items == []
    
    # Verify database query
    mock_session.query.assert_called_once()

def test_load_project_data_from_db_error():
    """Test handling of database errors."""
    # Setup mock session that raises an exception
    mock_session = Mock(spec=Session)
    mock_session.query.side_effect = Exception("Database error")
    
    # Call the function
    project, bom_items = load_project_data_from_db("test-project", mock_session)
    
    # Verify results
    assert project is None
    assert bom_items == [] 