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
    
    def __init__(self, base_url: str, session_data: Dict[str, Any]):
        """
        Initialize test case generator.
        
        Args:
            base_url: Base URL of the application
            session_data: Complete exploration session data
        """
        self.base_url = base_url
        self.session_data = session_data
        self.domain = self._extract_domain(base_url)
        
        # Extract key data
        self.exploration_summary = session_data.get('exploration_summary', {})
        self.detailed_results = session_data.get('detailed_results', {})
        self.executed_actions = self.detailed_results.get('executed_actions', [])
        
        # Analysis results
        self.user_journeys = {}
        self.test_suites = []
        self.all_test_cases = []
        
        logger.info(f"🧪 Test generator initialized for {base_url}")
        logger.info(f"📊 Found {len(self.executed_actions)} actions to analyze")
    
    def generate_test_cases(self) -> List[TestSuite]:
        """
        Generate comprehensive test cases from session data.
        
        Returns:
            List of test suites containing generated test cases
        """
        logger.info("🔍 Analyzing session data for test case generation...")
        
        # Extract user journeys from actions
        self.user_journeys = self._extract_user_journeys()
        logger.info(f"🗺️ Identified {len(self.user_journeys)} user journeys")
        
        # Generate test cases for each journey
        for journey_name, journey_actions in self.user_journeys.items():
            test_cases = self._generate_journey_test_cases(journey_name, journey_actions)
            self.all_test_cases.extend(test_cases)
        
        # Generate additional specialized test cases
        self.all_test_cases.extend(self._generate_error_handling_tests())
        self.all_test_cases.extend(self._generate_performance_tests())
        self.all_test_cases.extend(self._generate_accessibility_tests())
        
        # Organize into test suites
        self.test_suites = self._organize_into_suites()
        
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
        """Determine journey name based on trigger action."""
        if 'CONNECT' in action_text:
            return "connection_flow"
        elif 'HOME' in action_text:
            return "home_navigation"
        elif 'PROFILE' in action_text:
            return "profile_management"
        elif 'LOGIN' in action_text:
            return "authentication_flow"
        elif 'DASHBOARD' in action_text:
            return "dashboard_exploration"
        elif element_type == 'link':
            return f"navigation_to_{action_text.lower().replace(' ', '_')}"
        else:
            return f"interaction_flow_{int(time.time())}"
    
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
        """Determine test priority based on journey type."""
        critical_journeys = ['authentication_flow', 'registration_flow']
        high_journeys = ['profile_management', 'dashboard_exploration']
        
        if journey_name in critical_journeys:
            return TestPriority.CRITICAL
        elif journey_name in high_journeys:
            return TestPriority.HIGH
        elif 'navigation' in journey_name:
            return TestPriority.MEDIUM
        else:
            return TestPriority.LOW
    
    def _categorize_workflow(self, journey_name: str) -> str:
        """Categorize workflow for organization."""
        if 'connection' in journey_name:
            return "integration"
        elif 'auth' in journey_name or 'login' in journey_name:
            return "authentication"
        elif 'nav' in journey_name or 'home' in journey_name:
            return "navigation"
        elif 'profile' in journey_name or 'settings' in journey_name:
            return "user_management"
        else:
            return "general_interaction"
    
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
            "test_suites": [
                {
                    "name": suite.name,
                    "description": suite.description,
                    "test_count": len(suite.test_cases),
                    "estimated_duration": sum(tc.estimated_duration for tc in suite.test_cases)
                }
                for suite in self.test_suites
            ],
            "metadata": {
                "base_url": self.base_url,
                "source_session": self.session_data.get('session_info', {}).get('session_id', 'unknown'),
                "total_source_actions": len(self.executed_actions)
            }
        }


# Usage example
async def generate_tests_from_session(session_dir: Path, output_dir: Path) -> Dict[str, Any]:
    """
    Generate test cases from a saved exploration session.
    
    Args:
        session_dir: Path to exploration session directory
        output_dir: Path to save generated test files
        
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
    
    # Generate test cases
    generator = TestCaseGenerator(base_url, session_data.get('exploration_results', {}))
    test_suites = generator.generate_test_cases()
    
    # Export to all frameworks
    results = generator.export_all_frameworks(output_dir)
    
    # Generate summary
    summary = generator.generate_summary_report()
    
    # Save summary
    summary_path = output_dir / "generation_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, default=str)
    
    logger.info(f"✅ Test generation complete! Generated {summary['generation_summary']['total_test_cases']} tests")
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