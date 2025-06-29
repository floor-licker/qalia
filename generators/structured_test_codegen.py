#!/usr/bin/env python3
"""
Structured Test Code Generator

Converts structured test specifications (from StructuredTestPlanner) into
consistent, high-quality test code for different frameworks.

This provides:
- Consistent code structure across all frameworks
- Best practices enforcement (semantic selectors, proper waits, etc.)
- Maintainable and readable test code
- Framework-specific optimizations
"""

import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

from .structured_test_planner import TestScenario, TestAction, ActionType, VerificationType

logger = logging.getLogger(__name__)


class StructuredTestCodeGenerator:
    """Generates test code from structured test scenarios."""
    
    def __init__(self, base_url: str):
        """Initialize the code generator."""
        self.base_url = base_url
    
    def generate_playwright_tests(
        self, 
        scenarios: List[Any], 
        output_dir: Path
    ) -> List[Path]:
        """Generate Playwright test files from structured scenarios."""
        logger.info(f"🎭 Generating Playwright tests for {len(scenarios)} scenarios...")
        
        generated_files = []
        
        # Group scenarios by category for better organization
        scenarios_by_category = self._group_scenarios_by_category(scenarios)
        
        for category, category_scenarios in scenarios_by_category.items():
            file_path = output_dir / f"{category}_tests.spec.ts"
            content = self._generate_playwright_file_content(category_scenarios, category)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            generated_files.append(file_path)
            logger.info(f"✅ Generated Playwright file: {file_path.name}")
        
        return generated_files
    
    def generate_cypress_tests(
        self, 
        scenarios: List[TestScenario], 
        output_dir: Path
    ) -> List[Path]:
        """Generate Cypress test files from structured scenarios."""
        logger.info(f"🌲 Generating Cypress tests for {len(scenarios)} scenarios...")
        
        generated_files = []
        scenarios_by_category = self._group_scenarios_by_category(scenarios)
        
        for category, category_scenarios in scenarios_by_category.items():
            file_path = output_dir / f"{category}_tests.cy.js"
            content = self._generate_cypress_file_content(category_scenarios, category)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            generated_files.append(file_path)
            logger.info(f"✅ Generated Cypress file: {file_path.name}")
        
        return generated_files
    
    def generate_jest_tests(
        self, 
        scenarios: List[TestScenario], 
        output_dir: Path
    ) -> List[Path]:
        """Generate Jest test files from structured scenarios."""
        logger.info(f"🃏 Generating Jest tests for {len(scenarios)} scenarios...")
        
        generated_files = []
        scenarios_by_category = self._group_scenarios_by_category(scenarios)
        
        for category, category_scenarios in scenarios_by_category.items():
            file_path = output_dir / f"{category}_tests.test.js"
            content = self._generate_jest_file_content(category_scenarios, category)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            generated_files.append(file_path)
            logger.info(f"✅ Generated Jest file: {file_path.name}")
        
        return generated_files
    
    def _group_scenarios_by_category(self, scenarios: List[Any]) -> Dict[str, List[Any]]:
        """Group scenarios by category for better file organization."""
        groups = {}
        
        for scenario in scenarios:
            category = getattr(scenario, 'category', 'general') or 'general'
            if category not in groups:
                groups[category] = []
            groups[category].append(scenario)
        
        return groups
    
    def _generate_playwright_file_content(
        self, 
        scenarios: List[Any], 
        category: str
    ) -> str:
        """Generate Playwright test file content."""
        
        content = f'''import {{ test, expect, Page }} from '@playwright/test';

/**
 * {category.title()} Test Suite
 * 
 * Generated by Qalia AI using structured test planning
 * Base URL: {self.base_url}
 * Generated: {datetime.now().isoformat()}
 * 
 * This file contains {len(scenarios)} test scenarios for {category} functionality.
 */

test.describe('{category.title()} Tests', () => {{
  test.beforeEach(async ({{ page }}) => {{
    // Navigate to base URL before each test
    await page.goto('{self.base_url}');
    
    // Wait for page to be fully loaded
    await page.waitForLoadState('networkidle');
  }});
'''

        # Generate each test scenario
        for scenario in scenarios:
            content += self._generate_playwright_test_scenario(scenario)
        
        content += "\n});\n"
        return content
    
    def _generate_playwright_test_scenario(self, scenario: Any) -> str:
        """Generate a single Playwright test scenario."""
        
        test_content = f'''
  
  test('{scenario.name}', async ({{ page }}) => {{
    // {scenario.description}
    // User Story: {scenario.user_story}
    // Priority: {scenario.priority}
    // Estimated Duration: {scenario.estimated_duration_seconds}s
    
'''
        
        # Add preconditions as comments
        if hasattr(scenario, 'preconditions') and scenario.preconditions:
            test_content += "    // Preconditions:\n"
            for precondition in scenario.preconditions:
                test_content += f"    // - {precondition}\n"
            test_content += "\n"
        
        # Generate test steps
        for action in scenario.actions:
            test_content += self._generate_playwright_action(action)
        
        test_content += f"  }});\n"
        
        return test_content
    
    def _generate_playwright_action(self, action: Any) -> str:
        """Generate Playwright code for a single test action."""
        code = f"\n    // {action.description}\n"
        
        # Convert selector strategy to Playwright locator
        locator = self._convert_to_playwright_locator(action.selector_strategy, action.selector_value)
        
        action_type = action.type.value if hasattr(action.type, 'value') else str(action.type)
        
        if action_type == 'navigate':
            code += f"    await page.goto('{action.input_value or action.selector_value}');\n"
            code += f"    await page.waitForLoadState('networkidle');\n"
            
        elif action_type == 'click':
            code += f"    await page.locator('{locator}').click({{ timeout: {action.wait_timeout} }});\n"
            
        elif action_type == 'fill':
            code += f"    await page.locator('{locator}').fill('{action.input_value}', {{ timeout: {action.wait_timeout} }});\n"
            
        elif action_type == 'select':
            code += f"    await page.locator('{locator}').selectOption('{action.input_value}', {{ timeout: {action.wait_timeout} }});\n"
            
        elif action_type == 'hover':
            code += f"    await page.locator('{locator}').hover({{ timeout: {action.wait_timeout} }});\n"
            
        elif action_type == 'wait_for':
            code += f"    await page.locator('{locator}').waitFor({{ state: 'visible', timeout: {action.wait_timeout} }});\n"
            
        elif action_type == 'screenshot':
            code += f"    await page.screenshot({{ path: 'screenshot_{action.step_number}.png' }});\n"
        
        # Add verifications
        if hasattr(action, 'verifications'):
            for verification in action.verifications:
                code += self._generate_playwright_verification(verification)
        
        return code
    
    def _generate_playwright_verification(self, verification: Dict[str, Any]) -> str:
        """Generate Playwright verification/assertion code."""
        verification_type = verification.get('type', '')
        selector_strategy = verification.get('selector_strategy', 'css')
        selector_value = verification.get('selector_value', '')
        expected_value = verification.get('expected_value', '')
        
        locator = self._convert_to_playwright_locator(selector_strategy, selector_value)
        
        if verification_type == 'element_visible':
            return f"    await expect(page.locator('{locator}')).toBeVisible();\n"
        elif verification_type == 'element_hidden':
            return f"    await expect(page.locator('{locator}')).toBeHidden();\n"
        elif verification_type == 'text_contains':
            return f"    await expect(page.locator('{locator}')).toContainText('{expected_value}');\n"
        elif verification_type == 'text_exact':
            return f"    await expect(page.locator('{locator}')).toHaveText('{expected_value}');\n"
        elif verification_type == 'url_contains':
            return f"    await expect(page).toHaveURL(/{expected_value}/);\n"
        elif verification_type == 'url_exact':
            return f"    await expect(page).toHaveURL('{expected_value}');\n"
        elif verification_type == 'form_value':
            return f"    await expect(page.locator('{locator}')).toHaveValue('{expected_value}');\n"
        elif verification_type == 'page_title':
            return f"    await expect(page).toHaveTitle(/{expected_value}/);\n"
        else:
            return f"    // TODO: Implement verification for {verification_type}\n"
    
    def _convert_to_playwright_locator(self, strategy: str, value: str) -> str:
        """Convert selector strategy and value to Playwright locator."""
        if strategy == 'text':
            # Escape quotes in text
            escaped_value = value.replace("'", "\\'")
            return f"text={escaped_value}"
        elif strategy == 'role':
            return f"role={value}"
        elif strategy == 'aria_label':
            return f"[aria-label=\"{value}\"]"
        elif strategy == 'id':
            return f"#{value}"
        elif strategy == 'css':
            return value  # Already a CSS selector
        elif strategy == 'xpath':
            return f"xpath={value}"
        else:
            # Default to CSS selector
            return value
    
    def _generate_cypress_file_content(
        self, 
        scenarios: List[TestScenario], 
        category: str
    ) -> str:
        """Generate Cypress test file content."""
        
        content = f'''/**
 * {category.title()} Test Suite
 * 
 * Generated by Qalia AI using structured test planning
 * Base URL: {self.base_url}
 * Generated: {datetime.now().isoformat()}
 * 
 * This file contains {len(scenarios)} test scenarios for {category} functionality.
 */

describe('{category.title()} Tests', () => {{
  beforeEach(() => {{
    // Navigate to base URL before each test
    cy.visit('{self.base_url}');
  }});
'''

        # Generate each test scenario
        for scenario in scenarios:
            content += self._generate_cypress_test_scenario(scenario)
        
        content += "\n});\n"
        return content
    
    def _generate_cypress_test_scenario(self, scenario: TestScenario) -> str:
        """Generate a single Cypress test scenario."""
        
        test_content = f'''
  
  it('{scenario.name}', () => {{
    // {scenario.description}
    // User Story: {scenario.user_story}
    // Priority: {scenario.priority}
    
'''
        
        # Generate test steps
        for action in scenario.actions:
            test_content += self._generate_cypress_action(action)
        
        test_content += f"  }});\n"
        
        return test_content
    
    def _generate_cypress_action(self, action: TestAction) -> str:
        """Generate Cypress code for a single test action."""
        code = f"\n    // {action.description}\n"
        
        # Convert selector strategy to Cypress command
        selector = self._convert_to_cypress_selector(action.selector_strategy, action.selector_value)
        
        if action.type == ActionType.NAVIGATE:
            code += f"    cy.visit('{action.input_value or action.selector_value}');\n"
            
        elif action.type == ActionType.CLICK:
            code += f"    cy.{selector}.click({{ timeout: {action.wait_timeout} }});\n"
            
        elif action.type == ActionType.FILL:
            code += f"    cy.{selector}.clear().type('{action.input_value}', {{ timeout: {action.wait_timeout} }});\n"
            
        elif action.type == ActionType.SELECT:
            code += f"    cy.{selector}.select('{action.input_value}', {{ timeout: {action.wait_timeout} }});\n"
            
        elif action.type == ActionType.HOVER:
            code += f"    cy.{selector}.trigger('mouseover');\n"
            
        elif action.type == ActionType.WAIT_FOR:
            code += f"    cy.{selector}.should('be.visible');\n"
        
        # Add verifications
        for verification in action.verifications:
            code += self._generate_cypress_verification(verification)
        
        return code
    
    def _generate_cypress_verification(self, verification: Dict[str, Any]) -> str:
        """Generate Cypress verification/assertion code."""
        verification_type = verification['type']
        selector_strategy = verification['selector_strategy']
        selector_value = verification['selector_value']
        expected_value = verification.get('expected_value', '')
        
        selector = self._convert_to_cypress_selector(selector_strategy, selector_value)
        
        if verification_type == 'element_visible':
            return f"    cy.{selector}.should('be.visible');\n"
        elif verification_type == 'element_hidden':
            return f"    cy.{selector}.should('not.be.visible');\n"
        elif verification_type == 'text_contains':
            return f"    cy.{selector}.should('contain.text', '{expected_value}');\n"
        elif verification_type == 'text_exact':
            return f"    cy.{selector}.should('have.text', '{expected_value}');\n"
        elif verification_type == 'url_contains':
            return f"    cy.url().should('include', '{expected_value}');\n"
        elif verification_type == 'url_exact':
            return f"    cy.url().should('eq', '{expected_value}');\n"
        elif verification_type == 'form_value':
            return f"    cy.{selector}.should('have.value', '{expected_value}');\n"
        elif verification_type == 'page_title':
            return f"    cy.title().should('contain', '{expected_value}');\n"
        else:
            return f"    // TODO: Implement verification for {verification_type}\n"
    
    def _convert_to_cypress_selector(self, strategy: str, value: str) -> str:
        """Convert selector strategy and value to Cypress command."""
        if strategy == 'text':
            return f"contains('{value}')"
        elif strategy == 'role':
            return f"get('[role=\"{value}\"]')"
        elif strategy == 'aria_label':
            return f"get('[aria-label=\"{value}\"]')"
        elif strategy == 'id':
            return f"get('#{value}')"
        elif strategy == 'css':
            return f"get('{value}')"
        elif strategy == 'xpath':
            return f"xpath('{value}')"  # Requires cypress-xpath plugin
        else:
            # Default to get with CSS selector
            return f"get('{value}')"
    
    def _generate_jest_file_content(
        self, 
        scenarios: List[TestScenario], 
        category: str
    ) -> str:
        """Generate Jest test file content."""
        
        content = f'''/**
 * {category.title()} Test Suite
 * 
 * Generated by Qalia AI using structured test planning
 * Base URL: {self.base_url}
 * Generated: {datetime.now().isoformat()}
 * 
 * This file contains {len(scenarios)} test scenarios for {category} functionality.
 */

const puppeteer = require('puppeteer');

describe('{category.title()} Tests', () => {{
  let browser;
  let page;

  beforeAll(async () => {{
    browser = await puppeteer.launch({{ 
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    }});
  }});

  afterAll(async () => {{
    await browser.close();
  }});

  beforeEach(async () => {{
    page = await browser.newPage();
    await page.goto('{self.base_url}', {{ waitUntil: 'networkidle2' }});
  }});

  afterEach(async () => {{
    await page.close();
  }});
'''

        # Generate each test scenario
        for scenario in scenarios:
            content += self._generate_jest_test_scenario(scenario)
        
        content += "\n});\n"
        return content
    
    def _generate_jest_test_scenario(self, scenario: TestScenario) -> str:
        """Generate a single Jest test scenario."""
        
        test_content = f'''
  
  test('{scenario.name}', async () => {{
    // {scenario.description}
    // User Story: {scenario.user_story}
    // Priority: {scenario.priority}
    
'''
        
        # Generate test steps
        for action in scenario.actions:
            test_content += self._generate_jest_action(action)
        
        test_content += f"  }}, {scenario.estimated_duration_seconds * 1000});\n"  # Convert to milliseconds
        
        return test_content
    
    def _generate_jest_action(self, action: TestAction) -> str:
        """Generate Jest/Puppeteer code for a single test action."""
        code = f"\n    // {action.description}\n"
        
        # Convert selector strategy to Puppeteer selector
        selector = self._convert_to_puppeteer_selector(action.selector_strategy, action.selector_value)
        
        if action.type == ActionType.NAVIGATE:
            code += f"    await page.goto('{action.input_value or action.selector_value}', {{ waitUntil: 'networkidle2' }});\n"
            
        elif action.type == ActionType.CLICK:
            code += f"    await page.waitForSelector('{selector}', {{ timeout: {action.wait_timeout} }});\n"
            code += f"    await page.click('{selector}');\n"
            
        elif action.type == ActionType.FILL:
            code += f"    await page.waitForSelector('{selector}', {{ timeout: {action.wait_timeout} }});\n"
            code += f"    await page.type('{selector}', '{action.input_value}');\n"
            
        elif action.type == ActionType.SELECT:
            code += f"    await page.waitForSelector('{selector}', {{ timeout: {action.wait_timeout} }});\n"
            code += f"    await page.select('{selector}', '{action.input_value}');\n"
            
        elif action.type == ActionType.HOVER:
            code += f"    await page.waitForSelector('{selector}', {{ timeout: {action.wait_timeout} }});\n"
            code += f"    await page.hover('{selector}');\n"
            
        elif action.type == ActionType.WAIT_FOR:
            code += f"    await page.waitForSelector('{selector}', {{ visible: true, timeout: {action.wait_timeout} }});\n"
        
        # Add verifications
        for verification in action.verifications:
            code += self._generate_jest_verification(verification)
        
        return code
    
    def _generate_jest_verification(self, verification: Dict[str, Any]) -> str:
        """Generate Jest/Puppeteer verification/assertion code."""
        verification_type = verification['type']
        selector_strategy = verification['selector_strategy']
        selector_value = verification['selector_value']
        expected_value = verification.get('expected_value', '')
        
        selector = self._convert_to_puppeteer_selector(selector_strategy, selector_value)
        
        if verification_type == 'element_visible':
            return f"    const element = await page.waitForSelector('{selector}', {{ visible: true }});\n    expect(element).toBeTruthy();\n"
        elif verification_type == 'text_contains':
            return f"    const text = await page.$eval('{selector}', el => el.textContent);\n    expect(text).toContain('{expected_value}');\n"
        elif verification_type == 'url_contains':
            return f"    expect(page.url()).toContain('{expected_value}');\n"
        elif verification_type == 'form_value':
            return f"    const value = await page.$eval('{selector}', el => el.value);\n    expect(value).toBe('{expected_value}');\n"
        else:
            return f"    // TODO: Implement verification for {verification_type}\n"
    
    def _convert_to_puppeteer_selector(self, strategy: str, value: str) -> str:
        """Convert selector strategy and value to Puppeteer selector."""
        if strategy == 'text':
            # Puppeteer doesn't have built-in text selectors, use xpath
            return f"xpath///*[contains(text(), '{value}')]"
        elif strategy == 'role':
            return f"[role=\"{value}\"]"
        elif strategy == 'aria_label':
            return f"[aria-label=\"{value}\"]"
        elif strategy == 'id':
            return f"#{value}"
        elif strategy == 'css':
            return value  # Already a CSS selector
        elif strategy == 'xpath':
            return f"xpath{value}"
        else:
            # Default to CSS selector
            return value 