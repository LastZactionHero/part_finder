#!/usr/bin/env python3

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pcb_part_finder.core.output_writer import save_bom_results_to_db
from pcb_part_finder.db.models import BomItem, Component, BomItemMatch

def test_save_bom_results_to_db_success():
    """Test successful saving of BOM results."""
    # Setup mock data
    mock_bom_item = Mock(spec=BomItem)
    mock_bom_item.id = 1
    mock_bom_item.project_id = "test-project"
    
    mock_component = Mock(spec=Component)
    mock_component.id = 1
    mock_component.mouser_part_number = "123-456"
    
    mock_match = Mock(spec=BomItemMatch)
    
    # Setup mock session
    mock_session = Mock(spec=Session)
    mock_session.query.return_value.filter.return_value.first.side_effect = [
        mock_bom_item,  # First call returns BOM item
        mock_component,  # Second call returns existing component
        None  # Third call returns no match
    ]
    
    # Test data
    test_results = [{
        'bom_item_id': 1,
        'matches': [{
            'mouser_part_number': '123-456',
            'manufacturer': 'Test Manufacturer',
            'description': 'Test Component',
            'confidence_score': 0.95,
            'status': 'matched',
            'is_primary': True
        }]
    }]
    
    # Call the function
    success = save_bom_results_to_db("test-project", test_results, mock_session)
    
    # Verify results
    assert success is True
    mock_session.commit.assert_called_once()
    
    # Verify database operations
    assert mock_session.add.call_count == 2  # One for match, one for component
    assert mock_bom_item.primary_match_id is not None
    assert mock_bom_item.processed is True

def test_save_bom_results_to_db_bom_item_not_found():
    """Test handling of non-existent BOM item."""
    # Setup mock session
    mock_session = Mock(spec=Session)
    mock_session.query.return_value.filter.return_value.first.return_value = None
    
    # Test data
    test_results = [{
        'bom_item_id': 999,
        'matches': [{
            'mouser_part_number': '123-456'
        }]
    }]
    
    # Call the function
    success = save_bom_results_to_db("test-project", test_results, mock_session)
    
    # Verify results
    assert success is True  # Should still return True as this is a non-fatal error
    mock_session.commit.assert_called_once()

def test_save_bom_results_to_db_integrity_error():
    """Test handling of database integrity errors."""
    # Setup mock session
    mock_session = Mock(spec=Session)
    mock_session.flush.side_effect = IntegrityError(None, None, None)
    
    # Test data
    test_results = [{
        'bom_item_id': 1,
        'matches': [{
            'mouser_part_number': '123-456'
        }]
    }]
    
    # Call the function
    success = save_bom_results_to_db("test-project", test_results, mock_session)
    
    # Verify results
    assert success is True  # Should still return True as this is a non-fatal error
    mock_session.rollback.assert_called_once()

def test_save_bom_results_to_db_error():
    """Test handling of general database errors."""
    # Setup mock session
    mock_session = Mock(spec=Session)
    mock_session.commit.side_effect = Exception("Database error")
    
    # Test data
    test_results = [{
        'bom_item_id': 1,
        'matches': [{
            'mouser_part_number': '123-456'
        }]
    }]
    
    # Call the function
    success = save_bom_results_to_db("test-project", test_results, mock_session)
    
    # Verify results
    assert success is False
    mock_session.rollback.assert_called_once() 