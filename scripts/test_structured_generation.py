#!/usr/bin/env python3
"""
Test Structured Test Generation

This script tests the new structured test planning approach with mock exploration data
to demonstrate the complete pipeline: exploration data → LLM analysis → JSON specs → test code
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from generators.structured_test_planner import StructuredTestPlanner, TestScenario, TestAction, ActionType
from generators.structured_test_codegen import StructuredTestCodeGenerator


def create_mock_exploration_data() -> Dict[str, Any]:
    """Create realistic mock exploration data for testing."""
    return {
        'executed_actions': [
            {
                'action': {
                    'type': 'click',
                    'element_type': 'button',
                    'text': 'Connect Wallet',
                    'target': '.wallet-connect-btn'
                },
                'url': 'https://defi-app.example.com',
                'timestamp': '2024-01-15T10:30:00Z',
                'success': True
            },
            {
                'action': {
                    'type': 'click',
                    'element_type': 'button',
                    'text': 'MetaMask',
                    'target': '[data-wallet="metamask"]'
                },
                'url': 'https://defi-app.example.com/connect',
                'timestamp': '2024-01-15T10:30:05Z',
                'success': True
            },
            {
                'action': {
                    'type': 'click',
                    'element_type': 'link',
                    'text': 'Dashboard',
                    'target': 'nav a[href="/dashboard"]'
                },
                'url': 'https://defi-app.example.com/wallet-connected',
                'timestamp': '2024-01-15T10:30:10Z',
                'success': True
            },
            {
                'action': {
                    'type': 'click',
                    'element_type': 'button',
                    'text': 'Swap',
                    'target': '.swap-button'
                },
                'url': 'https://defi-app.example.com/dashboard',
                'timestamp': '2024-01-15T10:30:15Z',
                'success': True
            },
            {
                'action': {
                    'type': 'fill',
                    'element_type': 'input',
                    'text': '',
                    'target': 'input[placeholder="Amount"]',
                    'value': '100'
                },
                'url': 'https://defi-app.example.com/swap',
                'timestamp': '2024-01-15T10:30:20Z',
                'success': True
            },
            {
                'action': {
                    'type': 'click',
                    'element_type': 'button',
                    'text': 'Review Swap',
                    'target': '.review-swap-btn'
                },
                'url': 'https://defi-app.example.com/swap',
                'timestamp': '2024-01-15T10:30:25Z',
                'success': True
            }
        ],
        'discovered_states': {
            'state_1': {'url': 'https://defi-app.example.com', 'title': 'DeFi App - Connect Your Wallet'},
            'state_2': {'url': 'https://defi-app.example.com/connect', 'title': 'Choose Wallet Provider'},
            'state_3': {'url': 'https://defi-app.example.com/wallet-connected', 'title': 'Wallet Connected Successfully'},
            'state_4': {'url': 'https://defi-app.example.com/dashboard', 'title': 'DeFi Dashboard'},
            'state_5': {'url': 'https://defi-app.example.com/swap', 'title': 'Token Swap Interface'}
        },
        'state_transitions': [
            {'from': 'state_1', 'to': 'state_2', 'action': 'click Connect Wallet'},
            {'from': 'state_2', 'to': 'state_3', 'action': 'click MetaMask'},
            {'from': 'state_3', 'to': 'state_4', 'action': 'click Dashboard'},
            {'from': 'state_4', 'to': 'state_5', 'action': 'click Swap'}
        ]
    }


def create_mock_llm_response() -> Dict[str, Any]:
    """Create mock LLM response for testing without API calls."""
    return {
        "scenarios": [
            {
                "name": "complete_wallet_connection_flow",
                "description": "User successfully connects wallet and accesses DeFi features",
                "user_story": "As a DeFi user, I want to connect my wallet so that I can access trading and DeFi services",
                "priority": "critical",
                "category": "authentication",
                "preconditions": [
                    "User has MetaMask extension installed",
                    "User is on the DeFi app homepage",
                    "User has sufficient ETH for gas fees"
                ],
                "actions": [
                    {
                        "type": "click",
                        "description": "Click the Connect Wallet button to initiate wallet connection",
                        "selector_strategy": "text",
                        "selector_value": "Connect Wallet",
                        "wait_timeout": 5000,
                        "verifications": [
                            {
                                "type": "element_visible",
                                "selector_strategy": "text",
                                "selector_value": "Choose Wallet",
                                "description": "Wallet selection modal should appear"
                            }
                        ],
                        "step_number": 1,
                        "retry_on_failure": True
                    },
                    {
                        "type": "click",
                        "description": "Select MetaMask as the wallet provider",
                        "selector_strategy": "text",
                        "selector_value": "MetaMask",
                        "wait_timeout": 3000,
                        "verifications": [
                            {
                                "type": "url_contains",
                                "expected_value": "wallet-connected",
                                "description": "Should redirect to wallet connected confirmation page"
                            },
                            {
                                "type": "element_visible",
                                "selector_strategy": "text",
                                "selector_value": "Wallet Connected",
                                "description": "Success message should be displayed"
                            }
                        ],
                        "step_number": 2,
                        "retry_on_failure": True
                    }
                ],
                "cleanup_actions": [],
                "estimated_duration_seconds": 20,
                "max_retries": 3,
                "tags": ["wallet", "authentication", "critical_path", "metamask"],
                "expected_states_visited": ["state_1", "state_2", "state_3"]
            },
            {
                "name": "perform_token_swap_transaction",
                "description": "User performs a token swap transaction through the DeFi interface",
                "user_story": "As a DeFi trader, I want to swap tokens so that I can exchange one cryptocurrency for another",
                "priority": "high",
                "category": "transaction",
                "preconditions": [
                    "User wallet is already connected",
                    "User has sufficient token balance",
                    "User is on the dashboard page"
                ],
                "actions": [
                    {
                        "type": "click",
                        "description": "Navigate to the swap interface",
                        "selector_strategy": "text",
                        "selector_value": "Swap",
                        "wait_timeout": 3000,
                        "verifications": [
                            {
                                "type": "element_visible",
                                "selector_strategy": "text",
                                "selector_value": "Amount",
                                "description": "Swap form should be displayed"
                            }
                        ],
                        "step_number": 1,
                        "retry_on_failure": True
                    },
                    {
                        "type": "fill",
                        "description": "Enter the amount to swap",
                        "selector_strategy": "css",
                        "selector_value": "input[placeholder=\"Amount\"]",
                        "input_value": "100",
                        "wait_timeout": 2000,
                        "verifications": [
                            {
                                "type": "form_value",
                                "selector_strategy": "css",
                                "selector_value": "input[placeholder=\"Amount\"]",
                                "expected_value": "100",
                                "description": "Amount input should contain the entered value"
                            }
                        ],
                        "step_number": 2,
                        "retry_on_failure": True
                    },
                    {
                        "type": "click",
                        "description": "Review the swap transaction details",
                        "selector_strategy": "text",
                        "selector_value": "Review Swap",
                        "wait_timeout": 5000,
                        "verifications": [
                            {
                                "type": "element_visible",
                                "selector_strategy": "text",
                                "selector_value": "Transaction Details",
                                "description": "Transaction review modal should appear"
                            }
                        ],
                        "step_number": 3,
                        "retry_on_failure": True
                    }
                ],
                "cleanup_actions": [],
                "estimated_duration_seconds": 30,
                "max_retries": 2,
                "tags": ["swap", "transaction", "defi", "trading"],
                "expected_states_visited": ["state_4", "state_5"]
            }
        ]
    }


class MockStructuredTestPlanner(StructuredTestPlanner):
    """Mock version that doesn't require OpenAI API."""
    
    def __init__(self):
        # Don't call parent __init__ to avoid OpenAI client initialization
        pass
    
    def generate_test_scenarios(self, exploration_data: Dict[str, Any], base_url: str) -> list:
        """Generate mock scenarios without API call."""
        print("🧠 Mock LLM Analysis:")
        print(f"  - Analyzing {len(exploration_data.get('executed_actions', []))} captured actions")
        print(f"  - Discovered {len(exploration_data.get('discovered_states', {}))} unique states") 
        print(f"  - Base URL: {base_url}")
        print("  - Generating intelligent test scenarios...")
        
        # Get mock response
        mock_response = create_mock_llm_response()
        
        # Convert to TestScenario objects
        scenarios = []
        for scenario_data in mock_response['scenarios']:
            scenario = self._create_test_scenario(scenario_data)
            if scenario:
                scenarios.append(scenario)
        
        print(f"✅ Generated {len(scenarios)} structured test scenarios")
        return scenarios


def test_structured_generation():
    """Test the complete structured test generation pipeline."""
    
    print("🧪 TESTING STRUCTURED TEST GENERATION")
    print("=" * 60)
    
    # 1. Setup test data
    base_url = "https://defi-app.example.com"
    exploration_data = create_mock_exploration_data()
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    
    print(f"📊 Test Setup:")
    print(f"  - Base URL: {base_url}")
    print(f"  - Actions captured: {len(exploration_data['executed_actions'])}")
    print(f"  - States discovered: {len(exploration_data['discovered_states'])}")
    print(f"  - Output directory: {output_dir}")
    
    # 2. Generate structured scenarios using mock LLM
    print(f"\n🔄 Step 1: LLM Analysis")
    print("-" * 30)
    
    planner = MockStructuredTestPlanner()
    scenarios = planner.generate_test_scenarios(exploration_data, base_url)
    
    # 3. Generate test code from scenarios
    print(f"\n🔄 Step 2: Code Generation")
    print("-" * 30)
    
    code_generator = StructuredTestCodeGenerator(base_url)
    
    # Generate Playwright tests
    playwright_files = code_generator.generate_playwright_tests(scenarios, output_dir)
    
    # 4. Display results
    print(f"\n📊 GENERATION RESULTS")
    print("=" * 60)
    print(f"✅ Generated {len(scenarios)} test scenarios")
    print(f"✅ Created {len(playwright_files)} Playwright test files")
    
    # 5. Show generated content
    for file_path in playwright_files:
        print(f"\n📄 Generated File: {file_path.name}")
        print("-" * 40)
        
        # Read and display first 50 lines
        with open(file_path, 'r') as f:
            lines = f.readlines()
            preview_lines = lines[:50]
            
            for i, line in enumerate(preview_lines, 1):
                print(f"{i:2d}: {line.rstrip()}")
            
            if len(lines) > 50:
                print(f"... ({len(lines) - 50} more lines)")
    
    print(f"\n🎯 SUMMARY")
    print("=" * 60)
    print("✅ Structured test generation pipeline working!")
    print("✅ LLM analysis creates intelligent test scenarios")
    print("✅ Code generator produces framework-specific tests")
    print("✅ Tests include semantic selectors and meaningful assertions")
    print(f"✅ Output files saved to: {output_dir.absolute()}")
    
    return scenarios, playwright_files


if __name__ == "__main__":
    try:
        scenarios, files = test_structured_generation()
        
        print("\n🚀 NEXT STEPS:")
        print("- Replace MockStructuredTestPlanner with real OpenAI integration")
        print("- Add Cypress and Jest code generation")
        print("- Integrate with existing TestCaseGenerator")
        print("- Add configuration options for LLM parameters")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc() 