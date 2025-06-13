# 🤖 QALIA - Autonomous UI Testing, starts with QA et ça finit avec l'IA.

**Stop doing QA manually. Let AI explore your entire application and generate a comprehensive fingerprint state-map of user flows with corresponding test suites automatically, fully equipped to support automatic testcase generation with puppetteer, jest, and cypress.**

Qalia is a GitHub App that autonomously explores your web application using AI, discovers user journeys, identifies bugs, and generates production-ready test suites in Playwright, Cypress, and Jest—all integrated seamlessly into your development workflow through PR comments and check runs.

## 🎯 **The Problem We Solve**

**Manual testing is expensive and incomplete:**
- ❌ Manual exploratory testing misses edge cases and state combinations  
- ❌ Test maintenance becomes a bottleneck as applications grow
- ❌ Certain user journeys go untested until production failures occur

**Qalia's AI-powered solution:**
- ✅ **EXhaustive UI Exploration in Minutes**, dramatically faster and more reliable than manual testing with state-based navigation
- ✅ **Autonomous bug detection** catches UI bugs before they reach users 
- ✅ **Production-ready test generation** in multiple frameworks simultaneously
- ✅ **Zero maintenance overhead** - tests evolve with your application

## 💰 **Quantified Improvement**

| Traditional Approach | With Qalia | **Savings** |
|---------------------|------------|-------------|
| 40 hours manual test writing | 5 minutes setup | **~99% time reduction** |
| $4,000/month QA engineer | $0 ongoing cost | **$48,000+ annual savings** |
| 3-5 days exploratory testing | 10 minutes automated exploration | **~95% faster coverage** |
| Manual bug reproduction | Automatic screenshots + reproduction steps | **~90% faster debugging** |

## 🚀 **Quick Setup**

### **Step 1: Install the GitHub App**

1. **Visit the GitHub App page**: [Install Qalia](https://github.com/apps/qalia)
2. **Choose repositories** to install on (or select all repositories)
3. **Grant permissions** for the app to access your repositories

### **Step 2: Configure Your Application**

Create a `qalia.yml` file in your repository root to tell Qalia how to deploy and test your application:

```yaml
# qalia.yml - Application configuration for Qalia
deployment:
  type: "npm"  # Options: static, npm, python, docker, custom
  build:
    - "npm install"
    - "npm run build"
  start:
    command: "npm start"
    port: 3000
    wait_for_ready: 30
    health_check: "http://localhost:3000"

testing:
  entry_points:
    - url: "/"
      name: "Homepage"
    - url: "/login"
      name: "Login Page"
  exploration:
    max_depth: 3
    timeout: 300
  generation:
    frameworks: ["playwright", "cypress", "jest"]
```

**Alternative: Environment Variables** (for existing deployments)

```bash
# For specific repositories
DEPLOY_URL_MYORG_MYAPP=https://myapp.herokuapp.com

# Or use a generic pattern
DEFAULT_DEPLOY_URL=https://{repo}.herokuapp.com
```

### **Step 3: Automatic Analysis**

Once installed, Qalia will automatically:
- 🔍 **Analyze PRs** when opened or updated
- 🧠 **Explore** your deployed application with AI
- ⚡ **Generate** comprehensive test suites
- 📊 **Create check runs** with detailed results
- 🚨 **Comment on PRs** with actionable insights

## 🎯 **Advanced Configuration**

### **Enterprise Setup**
```yaml
- name: Qalia Enterprise Testing
  uses: floor-licker/qalia@v1
  with:
    app_url: 'https://staging.yourapp.com'
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    # Performance optimization
    max_depth: 5
    max_actions_per_page: 100
    # Test generation
    frameworks: 'playwright,cypress,jest'
    run_tests: true
    # Security & compliance
    headless: true
    viewport: '1920x1080'
    # Custom configuration
    config_file: 'qalia-config.yml'
```

### **Multi-Environment Testing**
```yaml
strategy:
  matrix:
    environment: 
      - staging
      - demo
      - feature-branch
steps:
  - name: Test ${{ matrix.environment }}
    uses: floor-licker/qalia@v1
    with:
      app_url: 'https://${{ matrix.environment }}.yourapp.com'
      openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

## 🧠 **AI-Powered Intelligence**

### **Smart Exploration Strategy**
- **State-based navigation** goes beyond simple URL crawling
- **Modal detection and interaction** handles complex UI patterns  
- **Form validation testing** with intelligent data generation
- **Adaptive timeouts** optimize exploration speed without missing content

### **Intelligent Bug Detection**
- **Automatic error categorization** (Critical, High, Medium, Low)
- **Screenshot capture** with context-aware naming
- **Console error analysis** with root cause identification
- **Performance monitoring** with actionable optimization suggestions

### **Production-Ready Test Generation**
- **Multi-framework output** (Playwright, Cypress, Jest)
- **User journey mapping** creates realistic test scenarios
- **Accessibility testing** built-in (WCAG compliance)
- **Performance assertions** for Core Web Vitals

## 📊 **What You Get**

Every run produces:

```
qalia-tests/
├── playwright/           # Parallel execution, multiple browsers
│   ├── user-auth.spec.ts
│   ├── checkout-flow.spec.ts
│   └── navigation.spec.ts
├── cypress/             # E2E testing with visual validation  
│   ├── user-auth.cy.js
│   └── checkout-flow.cy.js
├── jest/                # Unit/integration tests
│   └── api-validation.test.js
├── reports/
│   ├── bug-analysis.html     # Categorized issues with screenshots
│   ├── coverage-report.html  # Exploration coverage metrics
│   └── performance.json      # Core Web Vitals analysis
└── github-summary.md         # PR comment with actionable insights
```

## 🔧 **Framework Integration**

### **Local Development**
```bash
# Run exploration locally
docker run -e OPENAI_API_KEY=your-key \
  ghcr.io/floor-licker/qalia:latest \
  --app-url https://localhost:3000 \
  --output-dir ./tests
```

### **Existing Test Integration**
```yaml
# Add to existing test workflow
- name: Generate AI Tests
  uses: floor-licker/qalia@v1
  with:
    app_url: ${{ env.STAGING_URL }}
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}

- name: Run Generated Tests
  run: |
    npm install @playwright/test
    npx playwright test qalia-tests/playwright/
```

## 💡 **ROI Calculator**

**For a typical SaaS application:**

| Metric | Manual Approach | With Qalia | **Impact** |
|--------|----------------|------------|------------|
| **Test Creation** | 2-3 sprints | 1 workflow run | **6-8x faster delivery** |
| **Bug Detection** | 60% coverage | 95%+ coverage | **58% more bugs caught** |
| **Maintenance** | 20% of dev time | Near zero | **20% dev capacity freed** |
| **Production Issues** | 5-10 per month | 1-2 per month | **75% reduction in incidents** |

## 🚀 **Get Started in 60 Seconds**

1. **Copy the workflow** above to `.github/workflows/qalia-testing.yml`
2. **Add your OpenAI API key** to GitHub Secrets  
3. **Create a pull request** and watch Qalia work
4. **Review generated tests** and bug reports in artifacts

**Ready to eliminate manual testing bottlenecks?** [See Full Integration Guide →](INTEGRATION_GUIDE.md)

---

## 🔍 **Technical Architecture** 

<details>
<summary><strong>Advanced Implementation Details</strong></summary>

### **Core Components**
- **Browser Automation**: Playwright-based with intelligent element discovery
- **AI Analysis**: GPT-4 powered exploration strategy and bug analysis  
- **State Management**: Beyond URL-based crawling with UI state fingerprinting
- **Test Generation**: Multi-framework output with configurable templates

### **Performance Optimizations**
- **Adaptive timeouts**: 5s default, 2s for modals, 8s for navigation
- **Batch processing**: 5 elements per batch with smart prioritization
- **Element priority weighting**: Buttons (10), Links (8), Forms (6)
- **Parallel execution**: Concurrent action processing where safe

### **Supported Frameworks**
```bash
# Test generation support
playwright    # Cross-browser, parallel execution
cypress       # E2E with visual testing
jest          # Unit/integration with Puppeteer
selenium      # Legacy system compatibility
webdriver.io  # Advanced automation scenarios
```

</details>

**Questions?** Open an issue or check our [Documentation](INTEGRATION_GUIDE.md)

## 📁 **Repository Structure**

```
qalia/                          # Main QA AI tool repository
├── 🔧 Source Code              # QA AI tool implementation
├── 🐳 Docker Publishing        # Automated image builds
├── ✅ Tool Validation          # Tests that QA AI works correctly
└── 📚 Documentation           # How to use QA AI

demo-web-app/                   # Demonstration website
├── 🌐 Sample Web App           # TechStore e-commerce demo
├── 🧪 QA AI Workflows          # Examples of using QA AI
└── 📊 Live Results             # See QA AI in action
```

### **Important: Repository Roles**

- **🔧 Main QA AI Repo**: Contains the **tool source code** - NOT tested by QA AI
- **🌐 Demo Web App**: Sample **website** that **demonstrates** QA AI capabilities
- **👥 User Repositories**: Real applications where QA AI provides value

> **Note**: QA AI doesn't test itself! The `qalia` repository contains the tool's source code, while `demo-web-app` showcases how to use QA AI on actual web applications.

## 🎯 **Quick Start**
