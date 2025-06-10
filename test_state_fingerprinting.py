#!/usr/bin/env python3
"""
Test script to verify enhanced state fingerprinting with interactive elements.
"""

import sys
import logging
from typing import Dict, Any, List
from bs4 import BeautifulSoup

# Add current directory to path for imports
sys.path.append('.')

from state_fingerprint import StateExtractor, StateGraph, UIState
from utils import extract_interactive_elements, extract_page_info

def setup_logging():
    """Set up basic logging."""
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def create_test_html() -> str:
    """Create sample HTML for testing."""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
    </head>
    <body>
        <h1>Test Application</h1>
        <nav>
            <a href="/home">Home</a>
            <a href="/profile">Profile</a>
            <a href="/settings">Settings</a>
        </nav>
        
        <form action="/login" method="post">
            <input type="email" name="email" placeholder="Enter email" />
            <input type="password" name="password" placeholder="Password" />
            <button type="submit">Login</button>
        </form>
        
        <div class="content">
            <button id="load-data" class="btn btn-primary">Load Data</button>
            <select name="category">
                <option value="tech">Technology</option>
                <option value="science">Science</option>
            </select>
        </div>
    </body>
    </html>
    '''

def test_enhanced_state_fingerprinting():
    """Test the enhanced state fingerprinting with interactive elements."""
    print("🧪 Testing Enhanced State Fingerprinting...")
    
    # Setup
    state_extractor = StateExtractor()
    state_graph = StateGraph()
    
    # Create test data
    test_url = "https://example.com/test"
    html_content = create_test_html()
    
    # Extract page info and interactive elements
    page_info = extract_page_info(html_content, test_url)
    interactive_elements = extract_interactive_elements(html_content, test_url)
    
    print(f"📊 Extracted {len(interactive_elements)} interactive elements:")
    for i, elem in enumerate(interactive_elements, 1):
        print(f"  {i}. {elem['type']}: {elem.get('text', elem.get('name', elem.get('selector', 'no identifier')))}")
    
    # Create UI state with interactive elements
    ui_state = state_extractor.extract_ui_state(
        page=None,  # Not needed for this test
        url=test_url,
        page_info=page_info,
        console_logs=["[info] Page loaded successfully"],
        network_errors=[],
        interactive_elements=interactive_elements
    )
    
    # Test state fingerprinting
    fingerprint = ui_state.fingerprint()
    print(f"🔑 Generated state fingerprint: {fingerprint}")
    
    # Test state graph
    state_graph.add_state(ui_state)
    print(f"📈 Added state to graph. Total states: {len(state_graph.states)}")
    
    # Test XML export with interactive elements
    xml_content = state_graph.export_to_xml(domain="example.com", output_file="test_state_fingerprint.xml")
    
    print("✅ State fingerprinting test completed!")
    print("📄 XML export saved to: test_state_fingerprint.xml")
    
    # Print a preview of the XML
    print("\n📄 XML Preview (first 1000 chars):")
    print(xml_content[:1000] + "..." if len(xml_content) > 1000 else xml_content)

def test_untested_elements():
    """Test the get_untested_elements functionality."""
    print("\n🧪 Testing Untested Elements Detection...")
    
    # Create UI state with test elements
    test_elements = [
        {'type': 'button', 'selector': '#login-btn', 'text': 'Login'},
        {'type': 'input', 'selector': 'input[name="email"]', 'name': 'email'},
        {'type': 'link', 'selector': 'a[href="/profile"]', 'text': 'Profile'}
    ]
    
    ui_state = UIState(
        url="https://example.com/test",
        page_hash="test123",
        interactive_elements=test_elements
    )
    
    # Simulate some tested elements
    tested_signatures = {
        'button:#login-btn',  # This button was tested
        'input:input[name="email"]'  # This input was tested
    }
    
    untested = ui_state.get_untested_elements(tested_signatures)
    
    print(f"📊 Total elements: {len(test_elements)}")
    print(f"🧪 Tested elements: {len(tested_signatures)}")
    print(f"❓ Untested elements: {len(untested)}")
    
    for elem in untested:
        print(f"  - {elem['type']}: {elem.get('text', elem.get('name', elem.get('selector')))}")
    
    print("✅ Untested elements test completed!")

if __name__ == "__main__":
    setup_logging()
    
    try:
        test_enhanced_state_fingerprinting()
        test_untested_elements()
        print("\n🎉 All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 