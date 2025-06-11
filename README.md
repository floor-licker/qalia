# 🤖 QA AI - Autonomous Website Testing

**Add AI-powered testing to any webapp in 5 minutes**

A GitHub Action that automatically explores your web application, generates comprehensive test suites using AI analysis, and integrates seamlessly into your CI/CD pipeline.

## 🚀 For Webapp Developers

**Stop writing tests manually. Let AI do it for you.**

Add this to your `.github/workflows/qa-testing.yml`:
```yaml
- name: QA AI Testing
  uses: floor-licker/qa-ai@v1
  with:
    app_url: 'https://your-app.com'
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

**That's it!** QA AI will explore your app and generate Playwright, Cypress, and Jest tests automatically.

📖 **[Full Integration Guide →](INTEGRATION_GUIDE.md)**

---

## 🎯 What QA AI Does

1. **🔍 Explores** your webapp autonomously using AI
2. **🧠 Analyzes** user journeys and interaction patterns  
3. **⚡ Generates** production-ready test suites
4. **📊 Reports** issues directly to your PRs
5. **🚨 Alerts** on accessibility, performance, and UX problems

---

## SYSTEM ARCHITECTURE

### MODULAR STRUCTURE
```
qa-ai/
├── core/                    # Fundamental building blocks
│   ├── browser/            # Browser management, events, lifecycle
│   ├── session/            # Session persistence, storage
│   └── state/              # State tracking, fingerprinting
├── exploration/            # Exploration logic and strategies
│   ├── strategies/         # systematic, intelligent, hybrid
│   ├── elements/           # discovery, extraction, classification
│   ├── actions/            # executor, retry_logic, validation
│   └── modals/             # detection, handling
├── reporting/              # Analysis and output generation
│   ├── formatters/         # xml, json, html formatters
│   ├── analyzers/          # bug, coverage, performance analysis
│   └── exporters/          # file, api export mechanisms
├── config/                 # Centralized configuration management
├── explorers/              # Ready-to-use implementations
│   ├── basic_explorer.py   # Simple systematic exploration
│   ├── advanced_explorer.py # Full-featured with AI
│   └── specialized_explorers/ # domain-specific (SPA, DeFi, etc.)
├── scripts/                # Command-line utilities
├── tests/                  # Organized unit and integration tests
└── examples/               # Usage demonstrations
```

### CORE COMPONENTS

**Browser Management (core/browser/)**
- BrowserManager: Browser lifecycle and configuration
- EventHandler: Console, network, error event handling
- BrowserLifecycle: Setup, teardown, resource management

**Session Management (core/session/)**
- SessionManager: Exploration session persistence
- SessionStorage: State storage and retrieval
- SessionConfig: Session-specific configurations

**State Management (core/state/)**
- StateFingerprinter: UI state fingerprinting beyond URLs
- StateTracker: State transition tracking and analysis
- StateGraph: Complete state transition mapping

**Exploration Strategies (exploration/strategies/)**
- SystematicStrategy: BFS/DFS methodical exploration
- IntelligentStrategy: AI-guided exploration using GPT-4
- HybridStrategy: Combined systematic and intelligent approaches

**Element Discovery (exploration/elements/)**
- ElementExtractor: Interactive element discovery from DOM
- ElementDiscovery: Live element discovery with visibility checks
- ElementClassification: Element type and priority classification

**Action Execution (exploration/actions/)**
- ActionExecutor: Action execution with retry logic
- RetryLogic: Adaptive timeout and failure handling
- ActionValidation: Pre and post-action validation

**Modal Handling (exploration/modals/)**
- ModalDetector: Modal presence detection
- ModalHandler: Modal interaction and dismissal

**Reporting System (reporting/)**
- XMLFormatter: ChatGPT-optimized XML output
- JSONFormatter: Structured JSON reports
- HTMLFormatter: Human-readable HTML reports
- BugAnalyzer: Bug detection and categorization
- CoverageAnalyzer: Exploration coverage analysis
- PerformanceAnalyzer: Performance metrics and optimization

## INSTALLATION

**Prerequisites:**
- Python 3.8+
- OpenAI API Key (for GPT-4 access)
- Internet connection

**Setup:**
```bash
# Clone repository
git clone <repository_url>
cd qa-ai

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Set up environment
cp env.template .env
# Edit .env with your OPENAI_API_KEY
```

## USAGE

### BASIC USAGE
```python
from explorers import BasicExplorer
from config import ExplorationConfig

# Create configuration
config = ExplorationConfig.for_systematic_exploration()

# Initialize explorer
explorer = BasicExplorer("https://example.com", config)

# Run exploration
results = await explorer.explore()
```

### COMMAND LINE USAGE
```bash
# Basic exploration
python scripts/run_exploration.py https://example.com

# Quick scan
python scripts/run_exploration.py https://example.com --quick-scan

# Advanced exploration with AI
python scripts/run_exploration.py https://example.com --strategy intelligent

# Custom configuration
python scripts/run_exploration.py https://example.com \
  --max-actions 100 \
  --headless \
  --output results.json
```

### SPECIALIZED EXPLORERS
```python
from explorers.specialized_explorers import SPAExplorer, DeFiExplorer

# Single Page Application exploration
spa_explorer = SPAExplorer("https://react-app.com")
spa_results = await spa_explorer.explore()

# DeFi application exploration
defi_explorer = DeFiExplorer("https://defi-app.com")
defi_results = await defi_explorer.explore()
```

## CONFIGURATION

### EXPLORATION CONFIGURATION
```python
from config import ExplorationConfig, StrategyConfig, ElementConfig

config = ExplorationConfig(
    strategy=StrategyConfig(
        strategy=ExplorationStrategy.SYSTEMATIC,
        max_actions_per_page=50,
        max_depth=3,
        breadth_first=True,
        prioritize_forms=True
    ),
    elements=ElementConfig(
        include_hidden=False,
        min_element_size=10,
        exclude_selectors=['.advertisement', '.tracking']
    ),
    max_total_actions=500,
    max_session_duration=3600,
    capture_screenshots_on_error=True
)
```

### BROWSER CONFIGURATION
```python
from config import BrowserConfig, ViewportConfig

browser_config = BrowserConfig(
    headless=True,
    viewport=ViewportConfig(width=1280, height=720),
    timeout=30000,
    user_agent="QA-Bot/2.0"
)
```

### REPORTING CONFIGURATION
```python
from config import ReportingConfig, OutputFormat

reporting_config = ReportingConfig(
    formats=[OutputFormat.XML, OutputFormat.JSON, OutputFormat.HTML],
    include_screenshots=True,
    detailed_analysis=True,
    export_path="./reports/"
)
```

## EXPLORATION STRATEGIES

### SYSTEMATIC STRATEGY
**Purpose:** Methodical exploration of all interactive elements
**Method:** BFS/DFS traversal with element prioritization
**Use Case:** Comprehensive coverage, regression testing
**Configuration:**
```python
config = ExplorationConfig.for_systematic_exploration()
```

### INTELLIGENT STRATEGY  
**Purpose:** AI-guided exploration using GPT-4 insights
**Method:** Context-aware action selection based on page analysis
**Use Case:** Complex applications, business logic testing
**Configuration:**
```python
config = ExplorationConfig.for_intelligent_exploration()
```

### HYBRID STRATEGY
**Purpose:** Combined systematic and intelligent exploration
**Method:** Systematic discovery with intelligent prioritization
**Use Case:** Balanced coverage and efficiency

## STATE-BASED EXPLORATION

### UI STATE FINGERPRINTING
**Components:**
- URL and page content hash
- Modal presence and state
- Dynamic content state
- Form field values and validation states
- Navigation context and scroll position

**State Fingerprint Structure:**
```python
UIState {
    url: str,
    page_hash: str,
    modal_state: {
        has_modal: bool,
        modal_type: str,
        modal_content_hash: str
    },
    dynamic_content: {
        loading_states: List[str],
        error_states: List[str],
        content_hashes: Dict[str, str]
    },
    form_state: {
        filled_fields: Dict[str, str],
        validation_states: Dict[str, str],
        submit_available: bool
    },
    navigation_state: {
        breadcrumbs: List[str],
        active_menu: str,
        scroll_position: int
    }
}
```

### STATE TRANSITION TRACKING
**StateTransition Structure:**
```python
StateTransition {
    from_state: str,        # Source state fingerprint
    to_state: str,          # Destination state fingerprint  
    action: Dict,           # Action that caused transition
    timestamp: datetime,    # When transition occurred
    success: bool,          # Whether transition was successful
    execution_time: float,  # Action execution duration
    observable_changes: List # Console logs, network activity
}
```

## BUG DETECTION

### AUTOMATIC BUG DETECTION
**Error Types Detected:**
- HTTP errors (4xx, 5xx status codes)
- JavaScript console errors and exceptions
- Failed network requests
- Navigation failures and timeouts
- Form submission failures
- Unexpected page redirects
- Performance issues and slow loading

### BUG CATEGORIZATION
**Severity Levels:**
- CRITICAL: Application crashes, security issues
- HIGH: Broken functionality, failed transactions
- MEDIUM: User experience issues, performance problems
- LOW: Minor UI glitches, cosmetic issues

### ERROR REPORTING
**Screenshot Capture:**
- Automatic screenshots on errors
- Context-aware naming convention
- Error details embedded in filename

**Error Analysis:**
- Error categorization and grouping
- Root cause analysis
- Reproduction steps generation

## OUTPUT FORMATS

### XML OUTPUT (ChatGPT Optimized)
```xml
<ExplorationReport domain="example.com" timestamp="2024-01-15T10:30:00Z">
    <Summary>
        <PagesExplored>5</PagesExplored>
        <ActionsPerformed>45</ActionsPerformed>
        <BugsFound>3</BugsFound>
        <WarningsFound>8</WarningsFound>
        <ExplorationDuration>180.5</ExplorationDuration>
    </Summary>
    <StateAnalysis>
        <UniqueStatesDiscovered>12</UniqueStatesDiscovered>
        <StateTransitions>28</StateTransitions>
        <ModalStatesExplored>4</ModalStatesExplored>
    </StateAnalysis>
    <BugDetails>
        <Bug severity="HIGH" type="navigation_failure">
            <Description>Login button click timeout</Description>
            <Location>https://example.com/login</Location>
            <Screenshot>103045_action_timeout_login_button.png</Screenshot>
        </Bug>
    </BugDetails>
</ExplorationReport>
```

### JSON OUTPUT (Structured Data)
```json
{
    "exploration_summary": {
        "total_pages_visited": 5,
        "total_actions_performed": 45,
        "bugs_found": 3,
        "warnings": 8,
        "exploration_duration": 180.5,
        "state_statistics": {
            "unique_states_discovered": 12,
            "state_transitions": 28,
            "modal_states_explored": 4
        }
    },
    "bugs": [...],
    "warnings": [...],
    "state_graph": {...}
}
```

## PERFORMANCE OPTIMIZATIONS

### ADAPTIVE TIMEOUTS
**Dynamic Timeout Adjustment:**
- Default actions: 5 seconds (6x faster than 30s)
- Modal blocked elements: 2 seconds
- Navigation: 8 seconds
- Form submission: 10 seconds

### INTELLIGENT PRIORITIZATION
**Element Priority Weights:**
- Buttons: 10 (highest priority)
- Links: 8
- Form inputs: 6
- Selects: 6
- Generic elements: 3

### BATCH PROCESSING
**Optimization Features:**
- Batch execution of actions (default: 5 elements)
- Reduced state checks (every 3rd action)
- Minimal delays (0.2-1.0s vs 2s)
- Smart element skipping for failed elements

### PERFORMANCE RESULTS
**Speed Improvements:**
- 60x faster overall exploration
- 6-15x faster element interactions
- 2x faster page loading
- 10x faster modal detection

## ERROR HANDLING

### RETRY STRATEGIES
**Adaptive Retry Logic:**
- Exponential backoff for transient failures
- Maximum retry limits per action type
- Fallback strategies for blocked elements
- Graceful degradation on persistent failures

### SCREENSHOT CAPTURE
**Automatic Screenshot Triggers:**
- HTTP errors with response codes
- Console errors and JavaScript exceptions
- Action execution failures and timeouts
- Navigation failures
- Modal interaction failures

**Screenshot Naming Convention:**
```
HHMMSS_error_type_context_details.png
Examples:
103045_console_error_payment_form_validation.png
103122_action_timeout_login_button_main_page.png
103201_navigation_error_checkout_process.png
```

## TESTING

### UNIT TESTS
```bash
# Run unit tests
python -m pytest tests/unit/

# Run specific module tests
python -m pytest tests/unit/core/
python -m pytest tests/unit/exploration/
python -m pytest tests/unit/reporting/
```

### INTEGRATION TESTS
```bash
# Run integration tests
python -m pytest tests/integration/

# Run specific integration tests
python tests/integration/test_defi_space.py
python tests/integration/test_session_with_screenshots.py
```

## DEVELOPMENT

### EXTENDING THE SYSTEM

**Adding New Exploration Strategy:**
```python
# exploration/strategies/custom_strategy.py
class CustomStrategy:
    async def explore_page(self, page, elements):
        # Implement custom exploration logic
        pass
```

**Adding New Element Extractor:**
```python
# exploration/elements/custom_extractor.py
class CustomElementExtractor:
    async def extract_from_page(self, page):
        # Implement custom element extraction
        pass
```

**Adding New Report Formatter:**
```python
# reporting/formatters/custom_formatter.py
class CustomFormatter:
    def format(self, results):
        # Implement custom formatting logic
        pass
```

### SPECIALIZED EXPLORERS

**Creating Domain-Specific Explorer:**
```python
# explorers/specialized_explorers/ecommerce_explorer.py
class EcommerceExplorer(BasicExplorer):
    def __init__(self, base_url):
        super().__init__(base_url)
        # Add ecommerce-specific configuration
        self.config.elements.priority_selectors.update({
            '.add-to-cart': ActionPriority.HIGH,
            '.checkout-button': ActionPriority.HIGH,
            '.product-link': ActionPriority.MEDIUM
        })
```

## COMMAND LINE REFERENCE

### SCRIPTS
```bash
# Main exploration script
python scripts/run_exploration.py [URL] [OPTIONS]

# Result analysis
python scripts/analyze_results.py [RESULTS_FILE]

# Report generation
python scripts/generate_reports.py [RESULTS_FILE] [FORMAT]
```

### OPTIONS
```
--strategy {systematic,intelligent,hybrid}  Exploration strategy
--max-actions INTEGER                        Maximum total actions
--max-actions-per-page INTEGER              Maximum actions per page
--timeout INTEGER                           Session timeout (seconds)
--headless                                  Run in headless mode
--viewport WIDTHxHEIGHT                    Browser viewport size
--output FILENAME                          Output file path
--format {xml,json,html}                   Output format
--verbose                                  Enable verbose logging
--clear-state                              Clear previous state
--quick-scan                               Use quick scan configuration
```

## TROUBLESHOOTING

### COMMON ISSUES

**OpenAI API Key Not Found**
```bash
# Set environment variable
export OPENAI_API_KEY="your_key_here"

# Or create .env file
echo "OPENAI_API_KEY=your_key_here" > .env
```

**Playwright Browser Not Found**
```bash
# Install browsers
playwright install chromium

# Or install all browsers
playwright install
```

**Element Not Found Errors**
- Check element selectors in configuration
- Increase action timeout
- Enable detailed logging for debugging

**Performance Issues**
- Reduce max_actions_per_page
- Enable batch processing
- Use headless mode
- Optimize element selectors

## DEPENDENCIES

### CORE DEPENDENCIES
```
playwright>=1.40.0     # Browser automation
openai>=1.0.0         # GPT-4 integration  
asyncio               # Asynchronous execution
dataclasses           # Data structures
```

### OPTIONAL DEPENDENCIES
```
pytest>=7.0.0         # Testing framework
black>=22.0.0         # Code formatting
mypy>=1.0.0          # Type checking
```

## LICENSE

MIT License - See LICENSE file for details.

## VERSION HISTORY

**v2.0.0** - Modular architecture implementation
- Complete codebase restructuring
- Domain-specific module organization  
- Enhanced configuration management
- Improved testing structure

**v1.x** - Legacy monolithic implementation
- Single-file explorer implementations
- Basic functionality

## CONTRIBUTING

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Follow modular architecture patterns
4. Add tests for new functionality
5. Update documentation
6. Submit pull request

## AI AGENT NOTES

**For AI agents and LLM models:**
- This system uses modular architecture with clear separation of concerns
- Each module has specific responsibilities and interfaces
- Configuration is centralized in the config/ package
- Core functionality is in core/, exploration logic in exploration/, reporting in reporting/
- Ready-to-use implementations are in explorers/
- All components follow consistent naming patterns and documentation standards
- The system is designed for autonomous operation with minimal human intervention
- State-based exploration provides comprehensive UI coverage beyond URL-based crawling
- Performance optimizations enable rapid exploration while maintaining quality
