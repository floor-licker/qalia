# 🧪 Automated Test Case Generation

## Overview

The **Automated Test Case Generation** module converts exploration session data into runnable test files for multiple testing frameworks. This bridges the gap between discovery and automation by creating production-ready test suites from your QA-AI exploration sessions.

## Key Features

### 🎯 **Intelligent Test Generation**
- **User Journey Mapping**: Automatically identifies logical user workflows from exploration actions
- **Priority-Based Organization**: Categorizes tests by importance (Critical, High, Medium, Low)
- **Smart Selector Generation**: Creates robust, maintainable test selectors with fallback strategies
- **Context-Aware Assertions**: Generates appropriate assertions based on element types and expected behaviors

### 📝 **Multi-Framework Support**
- **Playwright** (TypeScript): Modern, reliable browser automation
- **Cypress** (JavaScript): Developer-friendly E2E testing
- **Jest + Puppeteer** (JavaScript): Unit and integration testing

### 🔄 **Workflow Categories**
- **Wallet Integration**: DeFi wallet connection flows
- **Authentication**: Login/signup workflows  
- **Navigation**: Page routing and state changes
- **User Management**: Profile and settings interactions
- **General Interaction**: Form submissions and element interactions

## Usage

### Basic Usage

```python
from generators import TestCaseGenerator

# Load exploration session data
with open('exploration_sessions/defi_space_20250611_100320/reports/session_report.json') as f:
    session_data = json.load(f)

# Create test generator
base_url = session_data['session_info']['base_url']
exploration_results = session_data['exploration_results']
generator = TestCaseGenerator(base_url, exploration_results)

# Generate test cases
test_suites = generator.generate_test_cases()

# Export to all frameworks
output_dir = Path("generated_tests")
results = generator.export_all_frameworks(output_dir)

print(f"Generated {len(test_suites)} test suites")
```

### Command Line Interface

```bash
# Generate tests from latest exploration session
python scripts/generate_tests_from_session.py --latest

# Generate tests from specific session
python scripts/generate_tests_from_session.py --session-dir exploration_sessions/defi_space_20250611_100320

# Generate only Playwright tests
python scripts/generate_tests_from_session.py --latest --framework playwright

# List available sessions
python scripts/generate_tests_from_session.py --list

# Dry run to see what would be generated
python scripts/generate_tests_from_session.py --latest --dry-run
```

### Integration with Exploration

```python
from scripts.run_exploration import run_exploration
from generators import TestCaseGenerator

# Run exploration
results = await run_exploration("https://app.defi.space")

# Automatically generate tests
generator = TestCaseGenerator(results['base_url'], results)
test_suites = generator.generate_test_cases()
generator.export_all_frameworks(Path("generated_tests"))
```

## Generated Test Structure

### Example Output Structure
```
generated_tests/
├── playwright/
│   ├── wallet_integration_tests.spec.ts
│   ├── navigation_tests.spec.ts
│   ├── user_management_tests.spec.ts
│   ├── playwright.config.ts
│   └── package.json
├── cypress/
│   ├── wallet_integration_tests.cy.js
│   ├── navigation_tests.cy.js
│   ├── cypress.config.js
│   └── package.json
├── jest/
│   ├── wallet_integration_tests.test.js
│   ├── navigation_tests.test.js
│   └── package.json
└── generation_summary.json
```

### Example Generated Test (Playwright)

```typescript
import { test, expect } from '@playwright/test';

/**
 * Wallet Integration Tests
 * 
 * Generated from QA-AI exploration session
 * Base URL: https://defi.space
 */

test.describe('wallet_integration_tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('https://defi.space');
  });

  test('test_wallet_connection_flow_happy_path', async ({ page }) => {
    // Verify wallet connection flow works correctly
    // User Story: As a user, I want to wallet connection flow successfully
    // Priority: critical
    
    // Click button: CONNECT
    await page.click('[data-testid="connect"], button:has-text("CONNECT"), text="CONNECT"', { timeout: 7000 });
    await expect(page.locator('[role="dialog"], .modal, [data-testid*="modal"]')).toBeVisible({ timeout: 5000 });
    
    // Click : Argent
    await page.click('[data-testid="argent"], :has-text("Argent"), text="Argent"', { timeout: 5000 });
    
    // Click : Braavos  
    await page.click('[data-testid="braavos"], :has-text("Braavos"), text="Braavos"', { timeout: 5000 });
  });
});
```

## Test Case Categories

### 🔥 **Critical Priority Tests**
- **Wallet Connection Flows**: Essential for DeFi applications
- **Authentication Systems**: Core user access functionality
- **Payment/Transaction Flows**: Business-critical operations

### ⚡ **High Priority Tests**
- **Profile Management**: User account functionality
- **Dashboard Operations**: Core application features
- **Data Submission Forms**: Important user interactions

### 📊 **Medium Priority Tests**
- **Navigation Flows**: Page routing and state changes
- **Content Display**: Information presentation
- **Search and Filter**: User experience features

### 📝 **Low Priority Tests**
- **UI Interactions**: General element interactions
- **Accessibility**: A11y compliance checks
- **Performance**: Load time and responsiveness

## Advanced Features

### Smart Selector Generation

The system generates robust selectors with multiple fallback strategies:

1. **Test-specific attributes** (preferred):
   - `[data-testid="connect-wallet"]`
   - `[data-test="wallet-button"]`
   - `[aria-label="Connect Wallet"]`

2. **Text-based selectors** (good):
   - `button:has-text("CONNECT")`
   - `a:has-text("Profile")`

3. **Generic text search** (fallback):
   - `text="CONNECT"`

4. **Original selector** (last resort):
   - Original CSS selector from exploration

### Intelligent Assertions

Based on element type and context:

- **Modal Triggers**: Verify modal appears after button click
- **Navigation Links**: Check URL change or state transition
- **Form Inputs**: Validate input values are set correctly
- **State Changes**: Monitor application state consistency

### Performance-Aware Timeouts

Dynamically calculated based on exploration performance:

```typescript
// If action took 3.2s during exploration
await page.click(selector, { timeout: 5200 }); // 3.2s + 2s buffer

// Standard timeout for fast actions
await page.click(selector, { timeout: 5000 }); // Default 5s
```

## Error Handling and Edge Cases

### Negative Test Generation
- **Network Error Scenarios**: Simulate connection issues
- **Invalid Input Testing**: Boundary condition validation
- **Authentication Failures**: Access control verification

### Retry Logic
- **Configurable Retry Counts**: Based on exploration flakiness
- **Adaptive Timeouts**: Learned from exploration performance
- **Smart Failure Recovery**: Multiple selector strategies

## Configuration Options

### TestCase Configuration
```python
@dataclass
class TestCase:
    name: str
    description: str
    priority: TestPriority        # CRITICAL, HIGH, MEDIUM, LOW
    user_story: str
    preconditions: List[str]
    steps: List[TestStep]
    tags: List[str]              # For test organization
    estimated_duration: int      # Seconds
    retry_count: int = 3
```

### TestSuite Configuration
```python
@dataclass  
class TestSuite:
    name: str
    description: str
    test_cases: List[TestCase]
    base_url: str
    parallel_execution: bool = False
    max_retries: int = 3
    timeout: int = 30000         # ms
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Generated QA Tests
on: [push, pull_request]

jobs:
  playwright-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: |
          cd generated_tests/playwright
          npm install
          npx playwright install
      
      - name: Run Playwright tests
        run: |
          cd generated_tests/playwright
          npx playwright test
      
      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: generated_tests/playwright/playwright-report/
```

### Running Generated Tests

```bash
# Playwright
cd generated_tests/playwright
npm install
npx playwright install
npx playwright test
npx playwright test --headed    # With browser UI
npx playwright show-report      # View HTML report

# Cypress  
cd generated_tests/cypress
npm install
npx cypress run
npx cypress open               # Interactive mode

# Jest
cd generated_tests/jest  
npm install
npm test
npm test -- --verbose         # Detailed output
```

## Best Practices

### 🎯 **Test Organization**
- Tests are grouped by user workflow/journey
- Each test suite focuses on a specific functional area
- Clear naming conventions for easy maintenance

### 🔧 **Maintenance**
- Generated selectors include multiple fallback options
- Tests include meaningful descriptions and user stories
- Configurable timeouts based on actual performance data

### 📊 **Reporting**
- Comprehensive generation summaries
- Test execution metrics and timing
- Framework-specific configuration files included

### 🚀 **Scalability**
- Parallel test execution where appropriate
- Configurable retry logic for flaky tests
- Framework-agnostic test case representation

## API Reference

### TestCaseGenerator

```python
class TestCaseGenerator:
    def __init__(self, base_url: str, session_data: Dict[str, Any])
    def generate_test_cases(self) -> List[TestSuite]
    def export_playwright_tests(self, output_dir: Path) -> List[Path]
    def export_cypress_tests(self, output_dir: Path) -> List[Path]
    def export_jest_tests(self, output_dir: Path) -> List[Path]
    def export_all_frameworks(self, output_dir: Path) -> Dict[str, List[Path]]
    def generate_summary_report(self) -> Dict[str, Any]
```

### Utility Functions

```python
async def generate_tests_from_session(
    session_dir: Path, 
    output_dir: Path
) -> Dict[str, Any]
```

## Troubleshooting

### Common Issues

**Q: No test cases generated**
- Check that exploration session has executed actions
- Verify session_report.json contains `executed_actions` data
- Use `--dry-run` to see analysis without generating files

**Q: Generated selectors not working**
- Review the selector fallback chain in generated tests
- Consider adding `data-testid` attributes to your application
- Customize selector generation logic if needed

**Q: Tests are flaky**
- Increase timeouts based on your application's performance
- Review retry configuration in generated test files
- Consider adding wait conditions for dynamic content

### Debug Mode

```bash
# Enable verbose logging
python scripts/generate_tests_from_session.py --latest --verbose

# Dry run analysis
python scripts/generate_tests_from_session.py --latest --dry-run
```

## Contributing

To extend the test generation system:

1. **Add New Framework Support**: Implement new export methods
2. **Enhance Selector Strategies**: Improve robust selector generation  
3. **Add Test Categories**: Extend workflow categorization
4. **Improve Assertions**: Create smarter assertion generation

See the main project documentation for contribution guidelines.

---

**🎉 Ready to generate production-ready tests from your exploration sessions!** 