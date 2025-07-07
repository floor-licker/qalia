#!/usr/bin/env python3
"""
Automated Test Case Generation

Converts exploration session data into runnable test files for various frameworks.
Generates Playwright, Jest, Cypress, and Selenium test files from exploration results.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
import logging

logger = logging.getLogger(__name__)


class TestFramework(Enum):
    """Supported test frameworks."""
    PLAYWRIGHT = "playwright"
    CYPRESS = "cypress"
    JEST = "jest"
    SELENIUM = "selenium"
    WEBDRIVER_IO = "webdriverio"


class TestPriority(Enum):
    """Test priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class TestAssertion:
    """Individual test assertion."""
    type: str  # visible, text, url, count, etc.
    selector: str
    expected: str
    timeout: int = 5000
    description: str = ""


@dataclass
class TestStep:
    """Individual test step."""
    action: str  # click, fill, wait, etc.
    selector: str
    value: Optional[str] = None
    timeout: int = 5000
    description: str = ""
    assertions: List[TestAssertion] = field(default_factory=list)


@dataclass
class TestCase:
    """Complete test case definition."""
    name: str
    description: str
    priority: TestPriority
    user_story: str
    preconditions: List[str]
    steps: List[TestStep]
    cleanup: List[TestStep] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    estimated_duration: int = 30  # seconds
    retry_count: int = 3
    
    # Metadata
    source_action_sequence: List[Dict] = field(default_factory=list)
    journey_name: str = ""
    workflow_category: str = ""


@dataclass
class TestSuite:
    """Collection of related test cases."""
    name: str
    description: str
    test_cases: List[TestCase]
    setup: List[TestStep] = field(default_factory=list)
    teardown: List[TestStep] = field(default_factory=list)
    base_url: str = ""
    
    # Configuration
    parallel_execution: bool = False
    max_retries: int = 3
    timeout: int = 30000  # ms


class TestCaseGenerator:
    """
    Generate test cases from exploration session data.
    
    Converts discovered user workflows into structured test cases
    that can be exported to various testing frameworks.
    """
    
    def __init__(self, base_url: str, session_data: Dict[str, Any], openai_api_key: str = None):
        """
        Initialize test case generator.
        
        Args:
            base_url: Base URL of the application
            session_data: Complete exploration session data
            openai_api_key: Optional OpenAI API key for structured test generation
        """
        self.base_url = base_url
        self.session_data = session_data
        self.domain = self._extract_domain(base_url)
        self.openai_api_key = openai_api_key
        
        # Determine generation mode
        self.use_structured_approach = bool(openai_api_key)
        if self.use_structured_approach:
            logger.info("🧠 Using structured LLM-based test generation")
        else:
            logger.info("📄 Using traditional action-based test generation")
        
        # Extract key data
        self.exploration_summary = session_data.get('exploration_summary', {})
        self.detailed_results = session_data.get('detailed_results', {})
        self.executed_actions = self.detailed_results.get('executed_actions', [])
        
        # NEW: Extract state graph data for comprehensive coverage
        self.state_graph_data = self._load_state_graph_data()
        self.discovered_states = self.state_graph_data.get('states', {})
        self.state_transitions = self.state_graph_data.get('transitions', [])
        
        # Analysis results
        self.user_journeys = {}
        self.test_suites = []
        self.all_test_cases = []
        
        # NEW: State coverage tracking
        self.covered_states = set()
        self.state_coverage_tests = []
        
        logger.info(f"🧪 Test generator initialized for {base_url}")
        logger.info(f"📊 Found {len(self.executed_actions)} actions to analyze")
        logger.info(f"🗺️ Found {len(self.discovered_states)} states to cover")
    
    def generate_test_cases(self) -> List[TestSuite]:
        """
        Generate comprehensive test cases from session data.
        
        Returns:
            List of test suites containing generated test cases
        """
        logger.info("🔍 Analyzing session data for test case generation...")
        logger.info(f"🧪 POST-EXPLORATION: Test generation starting with {len(self.executed_actions)} captured actions from exploration phase")
        
        # Choose generation strategy based on available resources
        if self.use_structured_approach:
            return self._generate_structured_test_cases()
        else:
            return self._generate_traditional_test_cases()
    
    def _generate_structured_test_cases(self) -> List[TestSuite]:
        """Generate test cases using the structured LLM approach."""
        try:
            from generators.structured_test_planner import StructuredTestPlanner
            from generators.structured_test_codegen import TestScenario, ActionType
            
            logger.info("🧠 Using structured LLM test generation...")
            
            # Generate structured scenarios using LLM
            planner = StructuredTestPlanner(self.openai_api_key)
            structured_scenarios = planner.generate_test_scenarios(self.session_data, self.base_url)
            
            if not structured_scenarios:
                logger.warning("⚠️ LLM generated no scenarios, falling back to traditional approach")
                return self._generate_traditional_test_cases()
            
            logger.info(f"✅ LLM generated {len(structured_scenarios)} structured scenarios")
            
            # Convert structured scenarios to our TestCase format
            for scenario in structured_scenarios:
                test_case = self._convert_scenario_to_test_case(scenario)
                if test_case:
                    self.all_test_cases.append(test_case)
            
            # Still add state coverage tests using traditional logic
            self._analyze_state_coverage_from_scenarios(structured_scenarios)
            state_coverage_tests = self._generate_state_coverage_tests()
            self.all_test_cases.extend(state_coverage_tests)
            
            # Organize into test suites
            self.test_suites = self._organize_into_suites()
            
            logger.info(f"✅ Generated {len(self.all_test_cases)} test cases in {len(self.test_suites)} suites using structured approach")
            return self.test_suites
            
        except ImportError as e:
            logger.warning(f"⚠️ Structured test components not available: {e}")
            return self._generate_traditional_test_cases()
        except Exception as e:
            logger.error(f"❌ Structured test generation failed: {e}")
            logger.info("🔄 Falling back to traditional test generation")
            return self._generate_traditional_test_cases()
    
    def _generate_traditional_test_cases(self) -> List[TestSuite]:
        """Generate test cases using the traditional action-based approach."""
        logger.info("📄 Using traditional action-based test generation...")
        
        # Extract user journeys from actions
        self.user_journeys = self._extract_user_journeys()
        logger.info(f"🗺️ Identified {len(self.user_journeys)} user journeys")
        
        # Generate test cases for each journey
        for journey_name, journey_actions in self.user_journeys.items():
            test_cases = self._generate_journey_test_cases(journey_name, journey_actions)
            self.all_test_cases.extend(test_cases)
        
        # NEW: Track which states are covered by journey tests
        self._analyze_state_coverage_from_journeys()
        
        # NEW: Generate additional tests for uncovered states
        state_coverage_tests = self._generate_state_coverage_tests()
        self.all_test_cases.extend(state_coverage_tests)
        
        # Generate additional specialized test cases
        self.all_test_cases.extend(self._generate_error_handling_tests())
        self.all_test_cases.extend(self._generate_performance_tests())
        self.all_test_cases.extend(self._generate_accessibility_tests())
        
        # Organize into test suites
        self.test_suites = self._organize_into_suites()
        
        # NEW: Validate complete state coverage
        coverage_report = self._validate_state_coverage()
        logger.info(f"🎯 State Coverage: {coverage_report['coverage_percentage']:.1f}% ({coverage_report['covered_states']}/{coverage_report['total_states']} states)")
        
        logger.info(f"✅ Generated {len(self.all_test_cases)} test cases in {len(self.test_suites)} suites")
        return self.test_suites
    
    def export_playwright_tests(self, output_dir: Path) -> List[Path]:
        """
        Export test cases as Playwright test files.
        
        Args:
            output_dir: Directory to save test files
            
        Returns:
            List of generated file paths
        """
        return self._export_tests(TestFramework.PLAYWRIGHT, output_dir)
    
    def export_cypress_tests(self, output_dir: Path) -> List[Path]:
        """Export test cases as Cypress test files."""
        return self._export_tests(TestFramework.CYPRESS, output_dir)
    
    def export_jest_tests(self, output_dir: Path) -> List[Path]:
        """Export test cases as Jest test files.""" 
        return self._export_tests(TestFramework.JEST, output_dir)
    
    def export_all_frameworks(self, output_dir: Path) -> Dict[str, List[Path]]:
        """
        Export test cases for all supported frameworks.
        
        Args:
            output_dir: Base directory to save test files
            
        Returns:
            Dictionary mapping framework names to generated file paths
        """
        results = {}
        
        for framework in TestFramework:
            framework_dir = output_dir / framework.value
            framework_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                generated_files = self._export_tests(framework, framework_dir)
                results[framework.value] = generated_files
                logger.info(f"✅ {framework.value}: {len(generated_files)} files generated")
            except Exception as e:
                logger.error(f"❌ Failed to generate {framework.value} tests: {e}")
                results[framework.value] = []
        
        return results
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        if '//' in url:
            domain = url.split('//')[1].split('/')[0]
        else:
            domain = url.split('/')[0]
        return domain.replace(':', '_').replace('.', '_')
    
    def _extract_user_journeys(self) -> Dict[str, List[Dict]]:
        """Extract logical user journeys from action sequence."""
        journeys = {}
        current_journey = []
        journey_name = "initial_exploration"
        
        for i, action in enumerate(self.executed_actions):
            action_data = action.get('action', {})
            action_text = action_data.get('text', '').upper()
            element_type = action_data.get('element_type', '')
            
            # Detect journey boundaries
            if self._is_journey_boundary(action_text, element_type, i):
                # Save current journey if it has actions
                if current_journey:
                    journeys[journey_name] = current_journey
                
                # Start new journey
                journey_name = self._determine_journey_name(action_text, element_type)
                current_journey = []
            
            # Add action to current journey
            action['sequence_number'] = i
            current_journey.append(action)
        
        # Add final journey
        if current_journey:
            journeys[journey_name] = current_journey
        
        return journeys
    
    def _is_journey_boundary(self, action_text: str, element_type: str, sequence: int) -> bool:
        """Determine if this action starts a new user journey."""
        # Major navigation triggers new journey
        journey_triggers = [
            'CONNECT', 'HOME', 'PROFILE', 'LOGIN', 'SIGNUP', 
            'DASHBOARD', 'SETTINGS', 'MENU', 'NAV'
        ]
        
        if any(trigger in action_text for trigger in journey_triggers):
            return True
        
        # Navigation links start new journeys
        if element_type == 'link' and sequence > 0:
            return True
        
        return False
    
    def _determine_journey_name(self, action_text: str, element_type: str) -> str:
        """Determine generic journey name - let LLM interpret actual purpose."""
        # Generic naming based on element type only
        if element_type == 'link':
            return f"navigation_sequence_{int(time.time())}"
        elif element_type == 'button':
            return f"interaction_sequence_{int(time.time())}"
        else:
            return f"action_sequence_{int(time.time())}"
    
    def _generate_journey_test_cases(self, journey_name: str, actions: List[Dict]) -> List[TestCase]:
        """Generate test cases for a specific user journey."""
        test_cases = []
        
        # Main happy path test
        main_test = self._create_happy_path_test(journey_name, actions)
        if main_test:
            test_cases.append(main_test)
        
        # Error handling variants
        error_tests = self._create_error_handling_variants(journey_name, actions)
        test_cases.extend(error_tests)
        
        # Boundary condition tests
        boundary_tests = self._create_boundary_tests(journey_name, actions)
        test_cases.extend(boundary_tests)
        
        return test_cases
    
    def _create_happy_path_test(self, journey_name: str, actions: List[Dict]) -> Optional[TestCase]:
        """Create the main happy path test for a journey."""
        if not actions:
            return None
        
        # Convert actions to test steps
        test_steps = []
        preconditions = [f"User is on {self.base_url}"]
        
        for action in actions:
            step = self._action_to_test_step(action)
            if step:
                test_steps.append(step)
        
        if not test_steps:
            return None
        
        # Determine priority based on journey type
        priority = self._get_journey_priority(journey_name)
        
        # Create test case
        test_case = TestCase(
            name=f"test_{journey_name}_happy_path",
            description=f"Verify {journey_name.replace('_', ' ')} works correctly",
            priority=priority,
            user_story=f"As a user, I want to {journey_name.replace('_', ' ')} successfully",
            preconditions=preconditions,
            steps=test_steps,
            tags=[journey_name, "happy_path", "automated"],
            estimated_duration=len(test_steps) * 3,  # 3 seconds per step
            source_action_sequence=actions,
            journey_name=journey_name,
            workflow_category=self._categorize_workflow(journey_name)
        )
        
        return test_case
    
    def _action_to_test_step(self, action: Dict) -> Optional[TestStep]:
        """Convert an exploration action to a test step."""
        action_data = action.get('action', {})
        action_type = action_data.get('action', '')
        element_type = action_data.get('element_type', '')
        selector = action_data.get('target', '')
        text = action_data.get('text', '')
        
        if not action_type or not selector:
            return None
        
        # Generate test-friendly selector
        test_selector = self._generate_test_selector(action_data)
        
        # Determine timeout based on action performance
        timeout = max(5000, int(action.get('duration', 0) * 1000) + 2000)
        
        # Create test step
        if action_type == 'click':
            description = f"Click {element_type}: {text}"
            step = TestStep(
                action='click',
                selector=test_selector,
                timeout=timeout,
                description=description
            )
            
            # Add assertions based on expected behavior
            if 'CONNECT' in text.upper():
                step.assertions.append(TestAssertion(
                    type='state_change',
                    selector='',
                    expected='true',
                    description="Application state should change after clicking CONNECT"
                ))
            elif element_type == 'link':
                step.assertions.append(TestAssertion(
                    type='url_change',
                    selector='',
                    expected='true',
                    description="URL should change after navigation"
                ))
            
        elif action_type == 'fill' or action_type == 'input':
            value = action_data.get('value', 'test-input')
            description = f"Fill {element_type}: {text}"
            step = TestStep(
                action='fill',
                selector=test_selector,
                value=value,
                timeout=timeout,
                description=description
            )
            
            # Assert input was filled
            step.assertions.append(TestAssertion(
                type='value',
                selector=test_selector,
                expected=value,
                description="Input should contain the entered value"
            ))
            
        else:
            # Generic interaction
            step = TestStep(
                action=action_type,
                selector=test_selector,
                timeout=timeout,
                description=f"{action_type} on {element_type}: {text}"
            )
        
        return step
    
    def _generate_test_selector(self, action_data: Dict) -> str:
        """Generate robust test selector."""
        text = action_data.get('text', '').strip()
        element_type = action_data.get('element_type', '')
        original_selector = action_data.get('target', '')
        
        # Priority order for selectors
        selectors = []
        
        # 1. Test-specific attributes (best)
        if text:
            clean_text = re.sub(r'[^a-zA-Z0-9]', '-', text.lower()).strip('-')
            selectors.extend([
                f'[data-testid="{clean_text}"]',
                f'[data-test="{clean_text}"]',
                f'[aria-label="{text}"]'
            ])
        
        # 2. Text-based selectors (good)
        if text and element_type:
            if element_type == 'button':
                selectors.append(f'button:has-text("{text}")')
            elif element_type == 'link':
                selectors.append(f'a:has-text("{text}")')
            else:
                selectors.append(f'{element_type}:has-text("{text}")')
        
        # 3. Generic text search (fallback)
        if text:
            selectors.append(f'text="{text}"')
        
        # 4. Original selector (last resort)
        if original_selector and original_selector not in selectors:
            selectors.append(original_selector)
        
        # Return comma-separated selector for fallback
        return ', '.join(selectors)
    
    def _get_journey_priority(self, journey_name: str) -> TestPriority:
        """Determine generic test priority - let LLM assess actual importance."""
        # All journeys get medium priority - let LLM determine actual importance
        return TestPriority.MEDIUM
    
    def _categorize_workflow(self, journey_name: str) -> str:
        """Categorize workflow generically - let LLM determine specific purpose."""
        # Generic categorization based on journey type only
        if 'navigation' in journey_name:
            return "navigation"
        elif 'interaction' in journey_name:
            return "interaction"
        else:
            return "general"
    
    def _create_error_handling_variants(self, journey_name: str, actions: List[Dict]) -> List[TestCase]:
        """Create error handling test variants."""
        # Implementation would create negative test cases
        # For now, return empty list
        return []
    
    def _create_boundary_tests(self, journey_name: str, actions: List[Dict]) -> List[TestCase]:
        """Create boundary condition tests."""
        # Implementation would create edge case tests
        # For now, return empty list
        return []
    
    def _generate_error_handling_tests(self) -> List[TestCase]:
        """Generate tests for error handling scenarios."""
        tests = []
        
        # Network error simulation test
        network_test = TestCase(
            name="test_network_error_handling",
            description="Verify application handles network errors gracefully",
            priority=TestPriority.HIGH,
            user_story="As a user, I want the app to handle network issues gracefully",
            preconditions=[f"User is on {self.base_url}"],
            steps=[
                TestStep(
                    action='evaluate',
                    selector='',
                    value='() => { window.navigator.serviceWorker.ready.then(reg => reg.unregister()); }',
                    description="Simulate network issues"
                )
            ],
            tags=["error_handling", "network", "negative_test"]
        )
        tests.append(network_test)
        
        return tests
    
    def _generate_performance_tests(self) -> List[TestCase]:
        """Generate performance-related tests."""
        tests = []
        
        # Page load performance test
        load_test = TestCase(
            name="test_page_load_performance",
            description="Verify page loads within acceptable time",
            priority=TestPriority.MEDIUM,
            user_story="As a user, I want pages to load quickly",
            preconditions=["Clean browser state"],
            steps=[
                TestStep(
                    action='goto',
                    selector='',
                    value=self.base_url,
                    timeout=10000,
                    description="Navigate to home page",
                    assertions=[TestAssertion(
                        type='load_time',
                        selector='',
                        expected='< 3000ms',
                        description="Page should load in under 3 seconds"
                    )]
                )
            ],
            tags=["performance", "load_time"]
        )
        tests.append(load_test)
        
        return tests
    
    def _generate_accessibility_tests(self) -> List[TestCase]:
        """Generate accessibility tests."""
        tests = []
        
        # Basic accessibility test
        a11y_test = TestCase(
            name="test_basic_accessibility",
            description="Verify basic accessibility compliance",
            priority=TestPriority.MEDIUM,
            user_story="As a user with disabilities, I want the app to be accessible",
            preconditions=[f"User is on {self.base_url}"],
            steps=[
                TestStep(
                    action='axe_check',
                    selector='',
                    description="Run axe-core accessibility scan",
                    assertions=[TestAssertion(
                        type='axe_violations',
                        selector='',
                        expected='0',
                        description="No accessibility violations should be found"
                    )]
                )
            ],
            tags=["accessibility", "a11y", "compliance"]
        )
        tests.append(a11y_test)
        
        return tests
    
    def _organize_into_suites(self) -> List[TestSuite]:
        """Organize test cases into logical test suites."""
        suites = {}
        
        # Group by workflow category
        for test_case in self.all_test_cases:
            category = test_case.workflow_category
            if category not in suites:
                suites[category] = []
            suites[category].append(test_case)
        
        # Create TestSuite objects
        test_suites = []
        for category, tests in suites.items():
            # Special handling for state coverage suite
            if category == "state_coverage":
                suite = TestSuite(
                    name=f"{category}_tests",
                    description=f"State coverage tests ensuring all discovered states are reachable",
                    test_cases=tests,
                    base_url=self.base_url,
                    parallel_execution=True,  # State coverage tests can run in parallel
                    max_retries=2  # Lower retries for coverage tests
                )
            else:
                suite = TestSuite(
                    name=f"{category}_tests",
                    description=f"Test suite for {category.replace('_', ' ')} functionality",
                    test_cases=tests,
                    base_url=self.base_url,
                    parallel_execution=len(tests) > 1,
                    max_retries=3
                )
            test_suites.append(suite)
        
        return test_suites
    
    def _export_tests(self, framework: TestFramework, output_dir: Path) -> List[Path]:
        """Export tests for specified framework."""
        output_dir.mkdir(parents=True, exist_ok=True)
        generated_files = []
        
        for suite in self.test_suites:
            if framework == TestFramework.PLAYWRIGHT:
                file_path = self._generate_playwright_file(suite, output_dir)
            elif framework == TestFramework.CYPRESS:
                file_path = self._generate_cypress_file(suite, output_dir)
            elif framework == TestFramework.JEST:
                file_path = self._generate_jest_file(suite, output_dir)
            else:
                logger.warning(f"Framework {framework.value} not yet implemented")
                continue
            
            if file_path:
                generated_files.append(file_path)
        
        # Generate configuration files
        config_files = self._generate_config_files(framework, output_dir)
        generated_files.extend(config_files)
        
        return generated_files
    
    def _generate_playwright_file(self, suite: TestSuite, output_dir: Path) -> Path:
        """Generate Playwright test file for a test suite."""
        file_path = output_dir / f"{suite.name}.spec.ts"
        
        content = f'''import {{ test, expect, Page }} from '@playwright/test';

/**
 * {suite.description}
 * 
 * Generated from Qalia exploration session
 * Base URL: {suite.base_url}
 * Generated: {datetime.now().isoformat()}
 */

test.describe('{suite.name}', () => {{
  let page: Page;

  test.beforeEach(async ({{ page: testPage }}) => {{
    page = testPage;
    await page.goto('{suite.base_url}');
  }});
'''

        # Add each test case
        for test_case in suite.test_cases:
            content += f'''
  
  test('{test_case.name}', async () => {{
    // {test_case.description}
    // User Story: {test_case.user_story}
    // Priority: {test_case.priority.value}
    
'''
            
            # Add test steps
            for step in test_case.steps:
                content += f"    // {step.description}\n"
                
                if step.action == 'click':
                    content += f"    await page.click('{step.selector}', {{ timeout: {step.timeout} }});\n"
                elif step.action == 'fill':
                    content += f"    await page.fill('{step.selector}', '{step.value}', {{ timeout: {step.timeout} }});\n"
                elif step.action == 'goto':
                    content += f"    await page.goto('{step.value}', {{ timeout: {step.timeout} }});\n"
                elif step.action == 'wait':
                    content += f"    await page.waitForTimeout({step.timeout});\n"
                elif step.action == 'evaluate':
                    content += f"    await page.evaluate({step.value});\n"
                elif step.action == 'axe_check':
                    content += f'''    const results = await page.evaluate(() => {{
      return window.axe.run();
    }});
    expect(results.violations).toHaveLength(0);
'''
                
                # Add assertions
                for assertion in step.assertions:
                    if assertion.type == 'visible':
                        content += f"    await expect(page.locator('{assertion.selector}')).toBeVisible({{ timeout: {assertion.timeout} }});\n"
                    elif assertion.type == 'text':
                        content += f"    await expect(page.locator('{assertion.selector}')).toContainText('{assertion.expected}');\n"
                    elif assertion.type == 'value':
                        content += f"    await expect(page.locator('{assertion.selector}')).toHaveValue('{assertion.expected}');\n"
                    elif assertion.type == 'url_change':
                        content += f"    await expect(page).toHaveURL(/{self.domain}/);\n"
                    elif assertion.type == 'load_time':
                        content += f"    // Performance assertion: {assertion.description}\n"
                
                content += "\n"
            
            content += "  });\n"

        content += "\n});\n"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    
    def _generate_cypress_file(self, suite: TestSuite, output_dir: Path) -> Path:
        """Generate Cypress test file for a test suite."""
        file_path = output_dir / f"{suite.name}.cy.js"
        
        content = f'''/**
 * {suite.description}
 * 
 * Generated from Qalia exploration session
 * Base URL: {suite.base_url}
 * Generated: {datetime.now().isoformat()}
 */

describe('{suite.name}', () => {{
  beforeEach(() => {{
    cy.visit('{suite.base_url}');
  }});
'''

        # Add each test case
        for test_case in suite.test_cases:
            content += f'''
  
  it('{test_case.name}', () => {{
    // {test_case.description}
    // User Story: {test_case.user_story}
    // Priority: {test_case.priority.value}
    
'''
            
            # Add test steps
            for step in test_case.steps:
                content += f"    // {step.description}\n"
                
                if step.action == 'click':
                    content += f"    cy.get('{step.selector}').click({{ timeout: {step.timeout} }});\n"
                elif step.action == 'fill':
                    content += f"    cy.get('{step.selector}').type('{step.value}', {{ timeout: {step.timeout} }});\n"
                elif step.action == 'goto':
                    content += f"    cy.visit('{step.value}');\n"
                elif step.action == 'wait':
                    content += f"    cy.wait({step.timeout});\n"
                
                # Add assertions
                for assertion in step.assertions:
                    if assertion.type == 'visible':
                        content += f"    cy.get('{assertion.selector}').should('be.visible');\n"
                    elif assertion.type == 'text':
                        content += f"    cy.get('{assertion.selector}').should('contain.text', '{assertion.expected}');\n"
                    elif assertion.type == 'value':
                        content += f"    cy.get('{assertion.selector}').should('have.value', '{assertion.expected}');\n"
                
                content += "\n"
            
            content += "  });\n"

        content += "\n});\n"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    
    def _generate_jest_file(self, suite: TestSuite, output_dir: Path) -> Path:
        """Generate Jest + Puppeteer test file for a test suite."""
        file_path = output_dir / f"{suite.name}.test.js"
        
        content = f'''/**
 * {suite.description}
 * 
 * Generated from Qalia exploration session
 * Base URL: {suite.base_url}
 * Generated: {datetime.now().isoformat()}
 */

const puppeteer = require('puppeteer');

describe('{suite.name}', () => {{
  let browser;
  let page;

  beforeAll(async () => {{
    browser = await puppeteer.launch({{ headless: true }});
  }});

  afterAll(async () => {{
    await browser.close();
  }});

  beforeEach(async () => {{
    page = await browser.newPage();
    await page.goto('{suite.base_url}');
  }});

  afterEach(async () => {{
    await page.close();
  }});
'''

        # Add each test case
        for test_case in suite.test_cases:
            content += f'''
  
  test('{test_case.name}', async () => {{
    // {test_case.description}
    // User Story: {test_case.user_story}
    // Priority: {test_case.priority.value}
    
'''
            
            # Add test steps
            for step in test_case.steps:
                content += f"    // {step.description}\n"
                
                if step.action == 'click':
                    content += f"    await page.click('{step.selector}', {{ timeout: {step.timeout} }});\n"
                elif step.action == 'fill':
                    content += f"    await page.type('{step.selector}', '{step.value}');\n"
                elif step.action == 'goto':
                    content += f"    await page.goto('{step.value}');\n"
                elif step.action == 'wait':
                    content += f"    await page.waitForTimeout({step.timeout});\n"
                
                # Add assertions
                for assertion in step.assertions:
                    if assertion.type == 'visible':
                        content += f"    const element = await page.waitForSelector('{assertion.selector}', {{ timeout: {assertion.timeout} }});\n"
                        content += f"    expect(element).toBeTruthy();\n"
                    elif assertion.type == 'text':
                        content += f"    const text = await page.$eval('{assertion.selector}', el => el.textContent);\n"
                        content += f"    expect(text).toContain('{assertion.expected}');\n"
                
                content += "\n"
            
            content += "  }, 30000);\n"  # 30 second timeout

        content += "\n});\n"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    
    def _generate_config_files(self, framework: TestFramework, output_dir: Path) -> List[Path]:
        """Generate configuration files for the test framework."""
        config_files = []
        
        if framework == TestFramework.PLAYWRIGHT:
            # Generate playwright.config.ts
            config_path = output_dir / "playwright.config.ts"
            config_content = f'''import {{ defineConfig, devices }} from '@playwright/test';

export default defineConfig({{
  testDir: './',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {{
    baseURL: '{self.base_url}',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  }},
  projects: [
    {{
      name: 'chromium',
      use: {{ ...devices['Desktop Chrome'] }},
    }},
    {{
      name: 'firefox',
      use: {{ ...devices['Desktop Firefox'] }},
    }},
    {{
      name: 'webkit',
      use: {{ ...devices['Desktop Safari'] }},
    }},
  ],
}});
'''
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            config_files.append(config_path)
            
            # Generate package.json
            package_path = output_dir / "package.json"
            package_content = f'''{{
  "name": "qalia-generated-tests",
  "version": "1.0.0",
  "description": "Auto-generated tests from Qalia exploration",
  "scripts": {{
    "test": "playwright test",
    "test:headed": "playwright test --headed",
    "test:debug": "playwright test --debug",
    "report": "playwright show-report"
  }},
  "devDependencies": {{
    "@playwright/test": "^1.40.0",
    "@types/node": "^20.0.0"
  }}
}}
'''
            with open(package_path, 'w', encoding='utf-8') as f:
                f.write(package_content)
            config_files.append(package_path)
        
        elif framework == TestFramework.CYPRESS:
            # Generate cypress.config.js
            config_path = output_dir / "cypress.config.js"
            config_content = f'''const {{ defineConfig }} = require('cypress')

module.exports = defineConfig({{
  e2e: {{
    baseUrl: '{self.base_url}',
    setupNodeEvents(on, config) {{
      // implement node event listeners here
    }},
    supportFile: false,
    video: true,
    screenshotOnRunFailure: true,
  }},
}})
'''
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            config_files.append(config_path)
        
        return config_files
    
    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate summary report of generated test cases."""
        total_tests = len(self.all_test_cases)
        priority_breakdown = {}
        category_breakdown = {}
        
        for test_case in self.all_test_cases:
            # Count by priority
            priority = test_case.priority.value
            priority_breakdown[priority] = priority_breakdown.get(priority, 0) + 1
            
            # Count by category
            category = test_case.workflow_category
            category_breakdown[category] = category_breakdown.get(category, 0) + 1
        
        # NEW: State coverage analysis
        coverage_report = self._validate_state_coverage()
        
        return {
            "generation_summary": {
                "total_test_cases": total_tests,
                "total_test_suites": len(self.test_suites),
                "total_journeys_analyzed": len(self.user_journeys),
                "generation_timestamp": datetime.now().isoformat()
            },
            "test_breakdown": {
                "by_priority": priority_breakdown,
                "by_category": category_breakdown
            },
            "state_coverage": {
                "total_states_discovered": coverage_report['total_states'],
                "states_covered_by_tests": coverage_report['covered_states'],
                "coverage_percentage": coverage_report['coverage_percentage'],
                "uncovered_states_count": coverage_report['uncovered_states'],
                "is_complete_coverage": coverage_report['is_complete'],
                "uncovered_state_samples": coverage_report['uncovered_state_list']
            },
            "test_suites": [
                {
                    "name": suite.name,
                    "description": suite.description,
                    "test_count": len(suite.test_cases),
                    "estimated_duration": sum(tc.estimated_duration for tc in suite.test_cases),
                    "is_state_coverage": "state_coverage" in suite.name
                }
                for suite in self.test_suites
            ],
            "metadata": {
                "base_url": self.base_url,
                "source_session": self.session_data.get('session_info', {}).get('session_id', 'unknown'),
                "total_source_actions": len(self.executed_actions),
                "state_tracking_enabled": len(self.discovered_states) > 0
            }
        }

    def _load_state_graph_data(self) -> Dict[str, Any]:
        """
        Load state graph data from XML state fingerprint or session data.
        
        Returns:
            Dictionary containing states and transitions data
        """
        try:
            # Try to parse XML state fingerprint if available
            if hasattr(self.session_data, 'state_fingerprint_xml'):
                return self._parse_state_xml(self.session_data.state_fingerprint_xml)
            
            # Try to load from session data structure
            session_info = self.session_data.get('session_info', {})
            session_dir = session_info.get('session_dir')
            
            if session_dir:
                from pathlib import Path
                state_xml_path = Path(session_dir) / "reports" / f"state_fingerprint_{self.domain}.xml"
                if state_xml_path.exists():
                    with open(state_xml_path, 'r', encoding='utf-8') as f:
                        xml_content = f.read()
                    return self._parse_state_xml(xml_content)
            
            # Fallback: derive states from action data
            return self._derive_states_from_actions()
            
        except Exception as e:
            logger.warning(f"Failed to load state graph data: {e}")
            return {'states': {}, 'transitions': []}

    def _parse_state_xml(self, xml_content: str) -> Dict[str, Any]:
        """
        Parse XML state fingerprint to extract states and transitions.
        
        Args:
            xml_content: XML content with state fingerprint data
            
        Returns:
            Dictionary with parsed states and transitions
        """
        import xml.etree.ElementTree as ET
        
        try:
            root = ET.fromstring(xml_content)
            states = {}
            transitions = []
            
            # Parse states
            states_elem = root.find('States')
            if states_elem is not None:
                for state_elem in states_elem.findall('State'):
                    fingerprint = state_elem.get('fingerprint')
                    state_type = state_elem.get('type')
                    
                    url_elem = state_elem.find('URL')
                    url = url_elem.text if url_elem is not None else ''
                    
                    # Extract interactive elements for this state
                    interactive_elements = []
                    elements_elem = state_elem.find('InteractiveElements')
                    if elements_elem is not None:
                        for elem_type in elements_elem.findall('ElementType'):
                            for element in elem_type.findall('Element'):
                                selector = element.get('selector', '')
                                text_elem = element.find('Text')
                                text = text_elem.text if text_elem is not None else ''
                                
                                interactive_elements.append({
                                    'type': elem_type.get('type'),
                                    'selector': selector,
                                    'text': text
                                })
                    
                    states[fingerprint] = {
                        'fingerprint': fingerprint,
                        'url': url,
                        'type': state_type,
                        'interactive_elements': interactive_elements
                    }
            
            # Parse transitions
            transitions_elem = root.find('Transitions')
            if transitions_elem is not None:
                for trans_elem in transitions_elem.findall('Transition'):
                    from_state_elem = trans_elem.find('FromState')
                    to_state_elem = trans_elem.find('ToState')
                    action_elem = trans_elem.find('Action')
                    
                    if from_state_elem is not None and to_state_elem is not None:
                        transition = {
                            'from_state': from_state_elem.text,
                            'to_state': to_state_elem.text,
                            'success': trans_elem.get('success', 'true').lower() == 'true'
                        }
                        
                        if action_elem is not None:
                            target_elem = action_elem.find('Target')
                            transition['action'] = {
                                'type': action_elem.get('type'),
                                'target': target_elem.text if target_elem is not None else ''
                            }
                        
                        transitions.append(transition)
            
            return {'states': states, 'transitions': transitions}
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse state XML: {e}")
            return {'states': {}, 'transitions': []}

    def _derive_states_from_actions(self) -> Dict[str, Any]:
        """
        Derive state information from executed actions as fallback.
        
        Returns:
            Dictionary with derived states and transitions
        """
        states = {}
        transitions = []
        
        # Group actions by URL to create basic states
        url_states = {}
        for i, action in enumerate(self.executed_actions):
            action_data = action.get('action', {})
            url = action.get('url', self.base_url)
            
            # Create a simple state fingerprint based on URL
            state_fingerprint = f"url_state_{abs(hash(url)) % 10000}"
            
            if state_fingerprint not in url_states:
                url_states[state_fingerprint] = {
                    'fingerprint': state_fingerprint,
                    'url': url,
                    'type': 'page',
                    'interactive_elements': []
                }
            
            # Add interactive element if not already present
            if action_data.get('target'):
                element = {
                    'type': action_data.get('element_type', 'unknown'),
                    'selector': action_data.get('target'),
                    'text': action_data.get('text', '')
                }
                if element not in url_states[state_fingerprint]['interactive_elements']:
                    url_states[state_fingerprint]['interactive_elements'].append(element)
        
        return {'states': url_states, 'transitions': transitions}

    def _analyze_state_coverage_from_journeys(self) -> None:
        """
        Analyze which states are covered by existing journey-based tests.
        """
        logger.info("🔍 Analyzing state coverage from user journey tests...")
        
        for test_case in self.all_test_cases:
            # Extract state transitions from test steps
            for step in test_case.steps:
                if step.action == 'goto':
                    # Direct navigation to URL - find matching state
                    target_url = step.value
                    matching_state = self._find_state_by_url(target_url)
                    if matching_state:
                        self.covered_states.add(matching_state['fingerprint'])
                        
                elif step.action in ['click', 'fill']:
                    # Interaction that might lead to state transition
                    state_transitions = self._find_transitions_by_action(step)
                    for transition in state_transitions:
                        self.covered_states.add(transition['to_state'])
        
        logger.info(f"📊 Journey tests cover {len(self.covered_states)} states")

    def _generate_state_coverage_tests(self) -> List[TestCase]:
        """
        Generate tests using greedy path extension to cover maximum states per test.
        
        This improved algorithm finds longer paths that visit multiple uncovered states,
        rather than generating individual tests for each state.
        
        Returns:
            List of test cases optimized for maximum state coverage
        """
        uncovered_states = set(self._get_uncovered_states())
        coverage_tests = []
        
        logger.info(f"🎯 Starting greedy path coverage for {len(uncovered_states)} uncovered states...")
        
        iteration = 1
        while uncovered_states:
            # Find the longest path that covers multiple uncovered states
            optimal_path = self._find_maximal_coverage_path(uncovered_states)
            
            if not optimal_path:
                logger.warning(f"⚠️ No path found for remaining {len(uncovered_states)} states")
                break
            
            # Generate one test for this multi-state path
            test_case = self._create_multi_state_coverage_test(optimal_path, iteration)
            if test_case:
                coverage_tests.append(test_case)
                
                # Remove covered states from uncovered set
                covered_by_this_path = set(optimal_path['visited_uncovered_states'])
                uncovered_states -= covered_by_this_path
                self.covered_states.update(covered_by_this_path)
                
                logger.debug(f"✅ Path {iteration}: covers {len(covered_by_this_path)} states in {optimal_path['total_steps']} steps")
            
            iteration += 1
            
            # Safety check to prevent infinite loops
            if iteration > len(self.discovered_states):
                logger.warning("⚠️ Breaking coverage loop - possible infinite recursion")
                break
        
        logger.info(f"📝 Generated {len(coverage_tests)} optimized coverage tests (vs {len(self._get_uncovered_states()) + len(coverage_tests)} with BFS)")
        return coverage_tests

    def _find_maximal_coverage_path(self, uncovered_states: set) -> Optional[Dict[str, Any]]:
        """
        Find the longest path from base state that visits maximum uncovered states.
        
        Uses greedy path extension to prioritize multi-state coverage.
        
        Args:
            uncovered_states: Set of state fingerprints not yet covered
            
        Returns:
            Dictionary with path information and coverage statistics
        """
        best_path = None
        max_coverage = 0
        
        # Try to find extended paths to each uncovered state
        for target_state in uncovered_states:
            try:
                path_info = self._find_extended_path_to_state(target_state, uncovered_states)
                
                if path_info:
                    states_covered = len(path_info['visited_uncovered_states'])
                    
                    # Prioritize paths that cover more states
                    if states_covered > max_coverage:
                        max_coverage = states_covered
                        best_path = path_info
                        
            except Exception as e:
                logger.debug(f"Path finding failed for state {target_state[:8]}: {e}")
                continue
        
        return best_path

    def _find_extended_path_to_state(self, target_state: str, uncovered_states: set) -> Optional[Dict[str, Any]]:
        """
        Find path to target state and greedily extend it to visit more uncovered states.
        
        Args:
            target_state: Primary target state to reach
            uncovered_states: Set of all uncovered states to potentially visit
            
        Returns:
            Extended path information with maximum state coverage
        """
        # First, find basic path to target state
        base_path = self._find_path_to_state(target_state)
        
        if not base_path:
            return None
        
        # Extend this path to visit additional uncovered states
        extended_path = self._extend_path_greedily(base_path, uncovered_states)
        
        # Analyze what states this path visits
        visited_states = self._extract_states_from_path(extended_path)
        visited_uncovered = [state for state in visited_states if state in uncovered_states]
        
        return {
            'transitions': extended_path,
            'visited_uncovered_states': visited_uncovered,
            'visited_all_states': visited_states,
            'total_steps': len(extended_path),
            'target_state': target_state,
            'coverage_efficiency': len(visited_uncovered) / len(extended_path) if extended_path else 0
        }

    def _extend_path_greedily(self, base_path: List[Dict[str, Any]], uncovered_states: set) -> List[Dict[str, Any]]:
        """
        Greedily extend a path to visit as many uncovered states as possible.
        
        Args:
            base_path: Initial path transitions
            uncovered_states: States we want to visit
            
        Returns:
            Extended path with additional transitions to uncovered states
        """
        extended_path = base_path.copy()
        
        # Determine current state at end of base path
        if extended_path:
            current_state = extended_path[-1]['to_state']
        else:
            # Start from base state if no initial path
            current_state = self._find_base_state()
        
        # Track visited states to avoid cycles
        visited_states = set()
        for transition in extended_path:
            visited_states.add(transition['from_state'])
            visited_states.add(transition['to_state'])
        
        # Greedily extend path to visit more uncovered states
        max_extensions = 10  # Prevent excessively long paths
        extensions = 0
        
        while extensions < max_extensions:
            # Find next reachable uncovered state
            next_state = self._find_next_reachable_uncovered_state(
                current_state, uncovered_states, visited_states
            )
            
            if not next_state:
                break  # No more reachable uncovered states
            
            # Find transition to next state
            transition = self._find_transition_between_states(current_state, next_state)
            
            if transition:
                extended_path.append(transition)
                visited_states.add(next_state)
                current_state = next_state
                extensions += 1
            else:
                break  # No valid transition found
        
        return extended_path

    def _find_next_reachable_uncovered_state(self, current_state: str, uncovered_states: set, visited_states: set) -> Optional[str]:
        """
        Find the next uncovered state reachable from current state.
        
        Prioritizes states that lead to even more uncovered states (lookahead).
        
        Args:
            current_state: Current position in the path
            uncovered_states: States we want to visit
            visited_states: States already visited in this path
            
        Returns:
            Next best uncovered state to visit, or None
        """
        reachable_uncovered = []
        
        # Find all uncovered states directly reachable from current state
        for transition in self.state_transitions:
            if (transition['from_state'] == current_state and 
                transition.get('success', True) and
                transition['to_state'] in uncovered_states and
                transition['to_state'] not in visited_states):
                
                target_state = transition['to_state']
                
                # Calculate lookahead score: how many more uncovered states can we reach from there?
                lookahead_score = self._calculate_lookahead_score(target_state, uncovered_states, visited_states)
                
                reachable_uncovered.append({
                    'state': target_state,
                    'transition': transition,
                    'lookahead_score': lookahead_score
                })
        
        if not reachable_uncovered:
            return None
        
        # Sort by lookahead score (prioritize states that lead to more uncovered states)
        reachable_uncovered.sort(key=lambda x: x['lookahead_score'], reverse=True)
        
        return reachable_uncovered[0]['state']

    def _calculate_lookahead_score(self, state: str, uncovered_states: set, visited_states: set) -> int:
        """
        Calculate how many additional uncovered states are reachable from given state.
        
        This helps prioritize paths that lead to more coverage opportunities.
        """
        score = 0
        
        # Count directly reachable uncovered states
        for transition in self.state_transitions:
            if (transition['from_state'] == state and 
                transition.get('success', True) and
                transition['to_state'] in uncovered_states and
                transition['to_state'] not in visited_states):
                score += 1
        
        return score

    def _find_transition_between_states(self, from_state: str, to_state: str) -> Optional[Dict[str, Any]]:
        """Find transition between two specific states."""
        for transition in self.state_transitions:
            if (transition['from_state'] == from_state and 
                transition['to_state'] == to_state and
                transition.get('success', True)):
                return transition
        return None

    def _extract_states_from_path(self, path: List[Dict[str, Any]]) -> List[str]:
        """Extract all states visited in a transition path."""
        if not path:
            return [self._find_base_state()]
        
        states = [path[0]['from_state']]  # Starting state
        for transition in path:
            states.append(transition['to_state'])
        
        return states

    def _find_base_state(self) -> str:
        """Find the base state (usually corresponds to base URL)."""
        # Try to find state matching base URL
        for state_fp, state_data in self.discovered_states.items():
            state_url = state_data.get('url', '')
            if (state_url == self.base_url or 
                state_url == self.base_url + '/' or
                state_url.rstrip('/') == self.base_url.rstrip('/')):
                return state_fp
        
        # Fallback: use first state if base URL state not found
        if self.discovered_states:
            return list(self.discovered_states.keys())[0]
        
        return None

    def _create_multi_state_coverage_test(self, path_info: Dict[str, Any], iteration: int) -> Optional[TestCase]:
        """
        Create a test case that covers multiple states using the extended path.
        
        Args:
            path_info: Extended path information with multiple state coverage
            iteration: Test iteration number for naming
            
        Returns:
            TestCase that visits multiple states in one test
        """
        if not path_info or not path_info['transitions']:
            return None
        
        steps = []
        transitions = path_info['transitions']
        visited_states = path_info['visited_uncovered_states']
        
        # Convert each transition to a test step
        for i, transition in enumerate(transitions):
            action = transition.get('action', {})
            action_type = action.get('type', 'click')
            target = action.get('target', '')
            
            if action_type and target:
                step = TestStep(
                    action=action_type,
                    selector=target,
                    description=f"Step {i+1}: {action_type} on {target}",
                    timeout=6000  # Slightly longer timeout for complex paths
                )
                steps.append(step)
        
        if not steps:
            return None
        
        # Add verification for key states reached
        self._add_multi_state_assertions(steps, visited_states, path_info)
        
        # Create descriptive test name and metadata
        state_count = len(visited_states)
        primary_state = path_info.get('target_state', 'unknown')[:8]
        
        test_case = TestCase(
            name=f"test_coverage_path_{iteration}_{state_count}_states",
            description=f"Navigate through {state_count} states via extended path (primary: {primary_state})",
            priority=TestPriority.MEDIUM,
            user_story=f"As a test, I want to verify {state_count} states are reachable in a single navigation flow",
            preconditions=[f"User starts at {self.base_url}"],
            steps=steps,
            tags=["state_coverage", "multi_state", "path_traversal", f"covers_{state_count}_states"],
            estimated_duration=len(steps) * 3,  # 3 seconds per step
            workflow_category="state_coverage"
        )
        
        return test_case

    def _add_multi_state_assertions(self, steps: List[TestStep], visited_states: List[str], path_info: Dict[str, Any]) -> None:
        """
        Add assertions to verify we reached the intended states.
        
        Args:
            steps: Test steps to add assertions to
            visited_states: States that should be visited
            path_info: Path information for additional context
        """
        if not steps or not visited_states:
            return
        
        # Add assertion to final step to verify we reached the end state
        final_state_fp = visited_states[-1]
        final_state_data = self.discovered_states.get(final_state_fp, {})
        
        # Verify URL if available
        final_url = final_state_data.get('url')
        if final_url and final_url != self.base_url:
            steps[-1].assertions.append(TestAssertion(
                type='url',
                selector='',
                expected=final_url,
                description=f"Verify we reached final state URL: {final_url}"
            ))
        
        # Verify presence of key interactive elements in final state
        interactive_elements = final_state_data.get('interactive_elements', [])
        if interactive_elements:
            # Use first interactive element as state verification
            key_element = interactive_elements[0]
            element_selector = key_element.get('selector', '')
            element_text = key_element.get('text', 'element')
            
            if element_selector:
                steps[-1].assertions.append(TestAssertion(
                    type='visible',
                    selector=element_selector,
                    expected='true',
                    description=f"Verify state-specific element is present: {element_text}"
                ))
        
        # Add intermediate assertions for complex paths
        if len(steps) > 5:
            # Add assertion at midpoint to verify path progress
            mid_step_index = len(steps) // 2
            mid_state_index = min(mid_step_index, len(visited_states) - 1)
            
            if mid_state_index > 0:
                mid_state_data = self.discovered_states.get(visited_states[mid_state_index], {})
                mid_url = mid_state_data.get('url')
                
                if mid_url and mid_url != self.base_url:
                    steps[mid_step_index].assertions.append(TestAssertion(
                        type='url',
                        selector='',
                        expected=mid_url,
                        description=f"Verify intermediate state reached: {mid_url}"
                    ))

    def _get_uncovered_states(self) -> List[str]:
        """Get list of state fingerprints that are not yet covered by tests."""
        all_states = set(self.discovered_states.keys())
        uncovered = all_states - self.covered_states
        return list(uncovered)

    def _find_state_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Find state data matching the given URL."""
        for state_data in self.discovered_states.values():
            if state_data.get('url') == url:
                return state_data
        return None

    def _find_transitions_by_action(self, step: TestStep) -> List[Dict[str, Any]]:
        """Find state transitions that match the given test step action."""
        matching_transitions = []
        
        for transition in self.state_transitions:
            action = transition.get('action', {})
            
            # Match by action type and target selector
            if (action.get('type') == step.action and 
                action.get('target') == step.selector):
                matching_transitions.append(transition)
        
        return matching_transitions

    def _find_path_to_state(self, target_state: str) -> Optional[List[Dict[str, Any]]]:
        """
        Find a sequence of actions to reach the target state from base URL.
        
        Args:
            target_state: State fingerprint to reach
             
        Returns:
            List of transitions forming a path to the target state, or None if no path found
        """
        # Simple BFS to find shortest path to target state
        from collections import deque
        
        # Find initial state (base URL state)
        initial_state = self._find_base_state()
        
        if not initial_state:
            return None
        
        if initial_state == target_state:
            return []  # Already at target state
        
        # BFS to find path
        queue = deque([(initial_state, [])])
        visited = {initial_state}
        
        while queue:
            current_state, path = queue.popleft()
            
            # Find all outgoing transitions from current state
            for transition in self.state_transitions:
                if (transition['from_state'] == current_state and 
                    transition.get('success', True)):  # Only successful transitions
                    
                    next_state = transition['to_state']
                    new_path = path + [transition]
                    
                    if next_state == target_state:
                        return new_path  # Found path to target
                    
                    if next_state not in visited:
                        visited.add(next_state)
                        queue.append((next_state, new_path))
        
        return None  # No path found

    def _validate_state_coverage(self) -> Dict[str, Any]:
        """
        Validate that all discovered states are covered by tests.
        
        Returns:
            Coverage report with statistics
        """
        total_states = len(self.discovered_states)
        covered_states = len(self.covered_states)
        uncovered_states = self._get_uncovered_states()
        
        coverage_percentage = (covered_states / total_states * 100) if total_states > 0 else 100
        
        coverage_report = {
            'total_states': total_states,
            'covered_states': covered_states,
            'uncovered_states': len(uncovered_states),
            'coverage_percentage': coverage_percentage,
            'uncovered_state_list': uncovered_states[:5],  # First 5 uncovered states
            'is_complete': len(uncovered_states) == 0
        }
        
        if uncovered_states:
            logger.warning(f"⚠️ {len(uncovered_states)} states remain uncovered:")
            for state_fp in uncovered_states[:3]:  # Show first 3
                state_data = self.discovered_states[state_fp]
                logger.warning(f"   - {state_fp[:8]}: {state_data.get('url', 'unknown URL')} ({state_data.get('type', 'unknown')} state)")
        else:
            logger.info("🎉 Complete state coverage achieved!")
        
        return coverage_report

    def _convert_scenario_to_test_case(self, scenario) -> Optional[TestCase]:
        """
        Convert a structured TestScenario to our internal TestCase format.
        
        Args:
            scenario: TestScenario from StructuredTestPlanner
            
        Returns:
            TestCase object or None if conversion failed
        """
        try:
            # Convert actions to test steps
            test_steps = []
            for action in scenario.actions:
                step = self._convert_structured_action_to_step(action)
                if step:
                    test_steps.append(step)
            
            if not test_steps:
                logger.warning(f"⚠️ No valid steps for scenario: {scenario.name}")
                return None
            
            # Map priority
            priority_map = {
                'critical': TestPriority.CRITICAL,
                'high': TestPriority.HIGH,
                'medium': TestPriority.MEDIUM,
                'low': TestPriority.LOW
            }
            priority = priority_map.get(scenario.priority, TestPriority.MEDIUM)
            
            # Create TestCase
            test_case = TestCase(
                name=scenario.name,
                description=scenario.description,
                priority=priority,
                user_story=scenario.user_story,
                preconditions=scenario.preconditions,
                steps=test_steps,
                tags=scenario.tags + ['structured_generation'],
                estimated_duration=scenario.estimated_duration_seconds,
                retry_count=scenario.max_retries,
                workflow_category=scenario.category
            )
            
            return test_case
            
        except Exception as e:
            logger.error(f"❌ Failed to convert scenario {scenario.name}: {e}")
            return None
    
    def _convert_structured_action_to_step(self, action) -> Optional[TestStep]:
        """
        Convert a structured Action to a TestStep.
        
        Args:
            action: Action from structured scenario
            
        Returns:
            TestStep object or None if conversion failed
        """
        try:
            # Build selector based on strategy
            selector = self._build_selector_from_structured_action(action)
            
            # Convert action type
            action_map = {
                'click': 'click',
                'fill': 'fill',
                'select': 'select',
                'navigate': 'goto',
                'wait_for': 'wait',
                'verify': 'assert',
                'hover': 'hover',
                'screenshot': 'screenshot'
            }
            
            test_action = action_map.get(action.type.value if hasattr(action.type, 'value') else action.type, action.type)
            
            # Create test step
            step = TestStep(
                action=test_action,
                selector=selector,
                value=getattr(action, 'input_value', None),
                timeout=action.wait_timeout,
                description=action.description
            )
            
            # Convert verifications to assertions
            if hasattr(action, 'verifications') and action.verifications:
                for verification in action.verifications:
                    assertion = self._convert_verification_to_assertion(verification)
                    if assertion:
                        step.assertions.append(assertion)
            
            return step
            
        except Exception as e:
            logger.error(f"❌ Failed to convert action: {e}")
            return None
    
    def _build_selector_from_structured_action(self, action) -> str:
        """Build a selector string from structured action data."""
        try:
            strategy = action.selector_strategy
            value = action.selector_value
            
            if strategy == 'text':
                return f'text="{value}"'
            elif strategy == 'role':
                return f'[role="{value}"]'
            elif strategy == 'aria_label':
                return f'[aria-label="{value}"]'
            elif strategy == 'id':
                return f'#{value}'
            elif strategy == 'css':
                return value
            elif strategy == 'xpath':
                return f'xpath={value}'
            else:
                return value  # Fallback to raw value
                
        except Exception:
            return getattr(action, 'selector_value', '')
    
    def _convert_verification_to_assertion(self, verification) -> Optional[TestAssertion]:
        """Convert a structured verification to a TestAssertion."""
        try:
            return TestAssertion(
                type=verification.type,
                selector=getattr(verification, 'selector_value', ''),
                expected=verification.expected_value,
                description=verification.description,
                timeout=getattr(verification, 'timeout', 5000)
            )
        except Exception as e:
            logger.debug(f"Failed to convert verification: {e}")
            return None
    
    def _analyze_state_coverage_from_scenarios(self, scenarios) -> None:
        """
        Analyze which states are covered by the structured scenarios.
        
        Args:
            scenarios: List of TestScenario objects
        """
        try:
            for scenario in scenarios:
                # Extract expected states from scenario
                if hasattr(scenario, 'expected_states_visited'):
                    for state_id in scenario.expected_states_visited:
                        self.covered_states.add(state_id)
                
                # Also try to infer coverage from actions
                for action in scenario.actions:
                    # Look for state references in action descriptions or URLs
                    if hasattr(action, 'verifications'):
                        for verification in action.verifications:
                            if verification.type in ['url_contains', 'url_exact']:
                                # Try to find matching state by URL
                                url_pattern = verification.expected_value
                                matching_states = self._find_states_by_url_pattern(url_pattern)
                                self.covered_states.update(matching_states)
            
            logger.info(f"📊 Structured scenarios cover {len(self.covered_states)} states")
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to analyze state coverage from scenarios: {e}")
    
    def _find_states_by_url_pattern(self, url_pattern: str) -> set:
        """Find state fingerprints that match a URL pattern."""
        matching_states = set()
        try:
            for state_fp, state_data in self.discovered_states.items():
                state_url = state_data.get('url', '')
                if url_pattern in state_url:
                    matching_states.add(state_fp)
        except Exception as e:
            logger.debug(f"Failed to match URL pattern {url_pattern}: {e}")
        return matching_states


# Usage example
async def generate_tests_from_session(session_dir: Path, output_dir: Path, openai_api_key: str = None) -> Dict[str, Any]:
    """
    Generate test cases from a saved exploration session.
    
    Args:
        session_dir: Path to exploration session directory
        output_dir: Path to save generated test files
        openai_api_key: Optional OpenAI API key for structured generation
        
    Returns:
        Summary of generated tests
    """
    # Load session data
    session_report_path = session_dir / "reports" / "session_report.json"
    if not session_report_path.exists():
        raise FileNotFoundError(f"Session report not found: {session_report_path}")
    
    with open(session_report_path, 'r', encoding='utf-8') as f:
        session_data = json.load(f)
    
    # Extract base URL
    base_url = session_data.get('session_info', {}).get('base_url', 'https://example.com')
    
    # Generate test cases with optional structured approach
    generator = TestCaseGenerator(base_url, session_data.get('exploration_results', {}), openai_api_key)
    test_suites = generator.generate_test_cases()
    
    # Export to all frameworks
    results = generator.export_all_frameworks(output_dir)
    
    # Generate summary
    summary = generator.generate_summary_report()
    
    # Save summary
    summary_path = output_dir / "generation_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, default=str)
    
    generation_mode = "structured LLM" if openai_api_key else "traditional action-based"
    logger.info(f"✅ Test generation complete using {generation_mode} approach! Generated {summary['generation_summary']['total_test_cases']} tests")
    logger.info(f"📄 Summary saved: {summary_path}")
    
    return summary


if __name__ == "__main__":
    import asyncio
    import sys
    
    if len(sys.argv) != 3:
        print("Usage: python test_case_generator.py <session_dir> <output_dir>")
        sys.exit(1)
    
    session_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    
    asyncio.run(generate_tests_from_session(session_dir, output_dir)) 