#!/usr/bin/env python3
"""
Structured Test Planner

Uses LLM to generate structured test specifications that are then parsed into
consistent test code. This approach provides:
- Consistent test structure across all frameworks
- Reduced LLM hallucination (no raw code generation)
- Better maintainability and debuggability
- Enforced best practices

The LLM returns JSON specifications, not code.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import openai

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Supported test action types."""
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    HOVER = "hover"
    WAIT_FOR = "wait_for"
    VERIFY = "verify"
    SCREENSHOT = "screenshot"


class VerificationType(Enum):
    """Types of verifications/assertions."""
    ELEMENT_VISIBLE = "element_visible"
    ELEMENT_HIDDEN = "element_hidden"
    TEXT_CONTAINS = "text_contains"
    TEXT_EXACT = "text_exact"
    URL_CONTAINS = "url_contains"
    URL_EXACT = "url_exact"
    ELEMENT_COUNT = "element_count"
    FORM_VALUE = "form_value"
    PAGE_TITLE = "page_title"


@dataclass
class TestAction:
    """Structured test action specification."""
    type: ActionType
    description: str
    
    # Element targeting
    selector_strategy: str  # "text", "role", "id", "css", "xpath"
    selector_value: str
    
    # Action-specific data
    input_value: Optional[str] = None
    wait_timeout: int = 5000
    
    # Verification
    verifications: List[Dict[str, Any]] = field(default_factory=list)
    
    # Metadata
    step_number: int = 0
    retry_on_failure: bool = True


@dataclass
class TestScenario:
    """Complete test scenario specification."""
    name: str
    description: str
    user_story: str
    priority: str  # "critical", "high", "medium", "low"
    category: str  # "navigation", "form", "interaction", "error_handling"
    
    # Test structure
    preconditions: List[str]
    actions: List[TestAction]
    cleanup_actions: List[TestAction] = field(default_factory=list)
    
    # Configuration
    estimated_duration_seconds: int = 30
    max_retries: int = 3
    tags: List[str] = field(default_factory=list)
    
    # State coverage (for our greedy path algorithm)
    expected_states_visited: List[str] = field(default_factory=list)


class StructuredTestPlanner:
    """Generates structured test plans using LLM intelligence."""
    
    def __init__(self, openai_api_key: str, model: str = "gpt-4"):
        """Initialize the test planner."""
        self.client = openai.OpenAI(api_key=openai_api_key)
        self.model = model
    
    def generate_test_scenarios(
        self, 
        exploration_data: Dict[str, Any],
        base_url: str
    ) -> List[TestScenario]:
        """
        Generate structured test scenarios from exploration data.
        
        Args:
            exploration_data: Raw exploration session data
            base_url: Base URL of the application
            
        Returns:
            List of structured test scenarios
        """
        logger.info("🧠 Generating structured test scenarios using LLM...")
        
        # Create comprehensive prompt for test scenario generation
        prompt = self._create_test_planning_prompt(exploration_data, base_url)
        
        try:
            # Get LLM response as structured JSON
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent output
                max_tokens=4000
            )
            
            # Parse LLM response into structured scenarios
            scenarios_data = self._parse_llm_response(response.choices[0].message.content)
            
            # Convert to TestScenario objects
            scenarios = []
            for scenario_data in scenarios_data:
                scenario = self._create_test_scenario(scenario_data)
                if scenario:
                    scenarios.append(scenario)
            
            logger.info(f"✅ Generated {len(scenarios)} structured test scenarios")
            return scenarios
            
        except Exception as e:
            logger.error(f"❌ Failed to generate test scenarios: {e}")
            return []
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for test planning."""
        return """You are an expert QA automation engineer specializing in web application testing.

Your task is to analyze web application exploration data and generate structured test scenarios.

CRITICAL REQUIREMENTS:
1. Return ONLY valid JSON - no markdown, no explanations, no extra text
2. Focus on USER WORKFLOWS, not individual actions
3. Create realistic, executable test scenarios
4. Use semantic selectors (text, role, aria-label) over CSS selectors
5. Include meaningful verifications for each scenario
6. Consider error conditions and edge cases

RESPONSE FORMAT:
Return a JSON array of test scenarios. Each scenario must follow this exact structure:

{
  "scenarios": [
    {
      "name": "descriptive_test_name",
      "description": "Clear description of what this test validates",
      "user_story": "As a [user type], I want to [action] so that [benefit]",
      "priority": "critical|high|medium|low",
      "category": "navigation|form|interaction|error_handling|integration",
      "preconditions": ["precondition 1", "precondition 2"],
      "actions": [
        {
          "type": "navigate|click|fill|select|hover|wait_for|verify|screenshot",
          "description": "Human-readable step description",
          "selector_strategy": "text|role|id|css|xpath|aria_label",
          "selector_value": "exact selector value",
          "input_value": "value to input (for fill/select actions)",
          "wait_timeout": 5000,
          "verifications": [
            {
              "type": "element_visible|text_contains|url_contains|etc",
              "selector_strategy": "text|role|css|xpath",
              "selector_value": "element to verify",
              "expected_value": "expected result",
              "description": "what this verification checks"
            }
          ],
          "step_number": 1,
          "retry_on_failure": true
        }
      ],
      "cleanup_actions": [],
      "estimated_duration_seconds": 30,
      "max_retries": 3,
      "tags": ["tag1", "tag2"],
      "expected_states_visited": ["state_id_1", "state_id_2"]
    }
  ]
}

Focus on creating COMPLETE USER JOURNEYS that test meaningful functionality."""
    
    def _create_test_planning_prompt(
        self, 
        exploration_data: Dict[str, Any], 
        base_url: str
    ) -> str:
        """Create the prompt for test scenario generation."""
        
        # Extract key information from exploration data
        executed_actions = exploration_data.get('executed_actions', [])
        discovered_states = exploration_data.get('discovered_states', {})
        state_transitions = exploration_data.get('state_transitions', [])
        
        # Summarize the application structure
        interactive_elements = []
        unique_pages = set()
        
        for action in executed_actions[:20]:  # Limit to first 20 actions
            action_data = action.get('action', {})
            element_type = action_data.get('element_type', '')
            text = action_data.get('text', '')
            url = action.get('url', '')
            
            if text and element_type:
                interactive_elements.append(f"{element_type}: '{text}'")
            if url:
                unique_pages.add(url)
        
        prompt = f"""Analyze this web application and generate structured test scenarios.

APPLICATION INFO:
- Base URL: {base_url}
- Pages discovered: {len(unique_pages)}
- Total interactions captured: {len(executed_actions)}
- Unique states discovered: {len(discovered_states)}

INTERACTIVE ELEMENTS FOUND:
{chr(10).join(interactive_elements[:15])}  # Show first 15 elements

KEY USER WORKFLOWS TO TEST:
Based on the exploration data, identify the main user workflows and create test scenarios for:

1. NAVIGATION FLOWS: How users move through the application
2. FORM INTERACTIONS: Any form submissions or input handling
3. CORE FUNCTIONALITY: Main features and interactions
4. ERROR SCENARIOS: What happens when things go wrong
5. EDGE CASES: Boundary conditions and unusual inputs

REQUIREMENTS:
- Generate 5-8 comprehensive test scenarios
- Each scenario should test a complete user journey
- Include both positive and negative test cases
- Use semantic selectors (prefer text/role over CSS)
- Add meaningful verifications at each step
- Consider accessibility and usability

Return the test scenarios as a JSON array following the specified format."""

        return prompt
    
    def _parse_llm_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse LLM response into structured data."""
        try:
            # Clean the response text
            cleaned_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith('```'):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            
            cleaned_text = cleaned_text.strip()
            
            # Parse JSON
            data = json.loads(cleaned_text)
            
            # Handle both array format and object with scenarios key
            if isinstance(data, dict) and 'scenarios' in data:
                return data['scenarios']
            elif isinstance(data, list):
                return data
            else:
                logger.error(f"Unexpected JSON structure: {type(data)}")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response text: {response_text[:500]}...")
            return []
    
    def _create_test_scenario(self, scenario_data: Dict[str, Any]) -> Optional[TestScenario]:
        """Convert scenario data to TestScenario object."""
        try:
            # Convert actions
            actions = []
            for action_data in scenario_data.get('actions', []):
                action = TestAction(
                    type=ActionType(action_data['type']),
                    description=action_data['description'],
                    selector_strategy=action_data['selector_strategy'],
                    selector_value=action_data['selector_value'],
                    input_value=action_data.get('input_value'),
                    wait_timeout=action_data.get('wait_timeout', 5000),
                    verifications=action_data.get('verifications', []),
                    step_number=action_data.get('step_number', 0),
                    retry_on_failure=action_data.get('retry_on_failure', True)
                )
                actions.append(action)
            
            # Convert cleanup actions
            cleanup_actions = []
            for cleanup_data in scenario_data.get('cleanup_actions', []):
                cleanup_action = TestAction(
                    type=ActionType(cleanup_data['type']),
                    description=cleanup_data['description'],
                    selector_strategy=cleanup_data['selector_strategy'],
                    selector_value=cleanup_data['selector_value'],
                    input_value=cleanup_data.get('input_value'),
                    wait_timeout=cleanup_data.get('wait_timeout', 5000)
                )
                cleanup_actions.append(cleanup_action)
            
            # Create scenario
            scenario = TestScenario(
                name=scenario_data['name'],
                description=scenario_data['description'],
                user_story=scenario_data['user_story'],
                priority=scenario_data['priority'],
                category=scenario_data['category'],
                preconditions=scenario_data.get('preconditions', []),
                actions=actions,
                cleanup_actions=cleanup_actions,
                estimated_duration_seconds=scenario_data.get('estimated_duration_seconds', 30),
                max_retries=scenario_data.get('max_retries', 3),
                tags=scenario_data.get('tags', []),
                expected_states_visited=scenario_data.get('expected_states_visited', [])
            )
            
            return scenario
            
        except Exception as e:
            logger.error(f"Failed to create test scenario: {e}")
            logger.error(f"Scenario data: {scenario_data}")
            return None


# Test the structured approach
if __name__ == "__main__":
    # Example usage
    planner = StructuredTestPlanner("dummy-key")
    
    # Mock exploration data
    mock_data = {
        'executed_actions': [
            {
                'action': {
                    'element_type': 'button',
                    'text': 'Connect Wallet',
                    'target': '.connect-btn'
                },
                'url': 'https://example.com'
            }
        ],
        'discovered_states': {},
        'state_transitions': []
    }
    
    # This would generate structured scenarios
    # scenarios = planner.generate_test_scenarios(mock_data, "https://example.com")
    print("✅ Structured Test Planner initialized") 