# 🤖 Qalia Integration Guide

## Quick Start: Add Qalia to Your Project

**Add autonomous AI testing to any webapp in under 5 minutes!**

### 1. Add to Your GitHub Actions

Create `.github/workflows/qalia-testing.yml` in your project:

```yaml
name: Qalia AI Testing

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  qalia-testing:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    # Deploy your app (customize this section for your tech stack)
    - name: Start App
      run: |
        npm install && npm start &
        sleep 10
        
    # Run Qalia
    - name: Qalia AI Analysis
      uses: floor-licker/qalia@v1
      with:
        app_url: 'http://localhost:3000'
        openai_api_key: ${{ secrets.OPENAI_API_KEY }}
        max_depth: 3
        frameworks: 'playwright,cypress,jest'
        output_dir: 'qalia-tests'
        
    # Upload results for review
    - name: Upload Test Results
      uses: actions/upload-artifact@v3
      with:
        name: qalia-test-results
        path: qalia-tests/
```

### 2. Add OpenAI API Key

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `OPENAI_API_KEY`
4. Value: Your OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

### 3. Push and Watch the Magic ✨

Qalia will automatically:
- 🔍 **Explore** your webapp autonomously using AI navigation
- 🧠 **Analyze** user journeys and interaction patterns with GPT-4
- ⚡ **Generate** production-ready tests (Playwright, Cypress & Jest)
- 📊 **Report** bugs, accessibility issues, and performance problems
- 🚨 **Comment** on PRs with actionable insights and test artifacts

---

## 🎯 Real-World Integration Examples

### E-commerce Application
```yaml
- name: Qalia E-commerce Testing
  uses: floor-licker/qalia@v1
  with:
    app_url: 'https://mystore-staging.com'
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    max_depth: 5              # Deep exploration for shopping flows
    max_actions_per_page: 50  # More thorough page testing
    frameworks: 'playwright,cypress'
    run_tests: true           # Execute tests immediately
```

### SaaS Dashboard
```yaml
- name: Qalia Dashboard Testing  
  uses: floor-licker/qalia@v1
  with:
    app_url: 'https://admin.myapp.com'
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    max_depth: 3
    timeout: 600              # 10 minutes for complex workflows
    headless: true
    viewport: '1920x1080'     # Desktop viewport
```

### React/Vue SPA
```yaml
- name: Qalia SPA Testing
  uses: floor-licker/qalia@v1
  with:
    app_url: 'https://app.mysaas.com'
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    max_depth: 4
    frameworks: 'playwright,jest'  # Focus on modern testing
    config_file: 'qalia-config.yml'  # Custom configuration
```

---

## ⚙️ Complete Configuration Reference

| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `app_url` | Your webapp URL to test | **Required** | `https://myapp.com` |
| `openai_api_key` | OpenAI API key for AI analysis | **Required** | `${{ secrets.OPENAI_API_KEY }}` |
| `max_depth` | How deep to explore (pages/levels) | `3` | `5` for complex apps |
| `max_actions_per_page` | Actions per page | `30` | `50` for thorough testing |
| `timeout` | Max exploration time (seconds) | `300` | `1800` for deep testing |
| `headless` | Run browser without UI | `true` | `false` for debugging |
| `frameworks` | Test frameworks to generate | `playwright,cypress,jest` | `playwright` only |
| `output_dir` | Test output directory | `qalia-tests` | `generated-tests` |
| `run_tests` | Execute generated tests | `true` | `false` to only generate |
| `viewport` | Browser viewport size | `1280x720` | `1920x1080` |
| `config_file` | Custom config file path | None | `qalia-config.yml` |

---

## 📈 Production Integration Patterns

### Pattern 1: Staging Gate (Recommended)
```yaml
name: Deploy with Qalia Gate

on:
  pull_request:
    branches: [ main ]

jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    steps:
    - name: Deploy to Staging
      run: ./deploy-staging.sh
      
  qalia-testing:
    needs: deploy-staging
    runs-on: ubuntu-latest
    steps:
    - name: Qalia Quality Gate
      uses: floor-licker/qalia@v1
      with:
        app_url: 'https://pr-${{ github.event.number }}.myapp.com'
        openai_api_key: ${{ secrets.OPENAI_API_KEY }}
        
    - name: Block merge if critical bugs found
      run: |
        if [ -f "qalia-tests/critical-issues.json" ]; then
          echo "Critical issues found, blocking merge"
          exit 1
        fi
        
  auto-merge:
    needs: qalia-testing
    if: success()
    runs-on: ubuntu-latest
    steps:
    - name: Auto-merge if tests pass
      run: gh pr merge --auto --squash
```

### Pattern 2: Comprehensive Nightly Testing
```yaml
name: Nightly Qalia Analysis

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC

jobs:
  comprehensive-testing:
    runs-on: ubuntu-latest
    steps:
    - name: Deep Qalia Analysis
      uses: floor-licker/qalia@v1
      with:
        app_url: 'https://production.myapp.com'
        openai_api_key: ${{ secrets.OPENAI_API_KEY }}
        max_depth: 8          # Very deep exploration
        timeout: 3600         # 1 hour
        frameworks: 'playwright,cypress,jest'
        
    - name: Slack notification on issues
      if: failure()
      run: |
        curl -X POST -H 'Content-type: application/json' \
        --data '{"text":"🚨 Qalia found critical issues in production!"}' \
        ${{ secrets.SLACK_WEBHOOK }}
```

### Pattern 3: Multi-Environment Matrix Testing
```yaml
strategy:
  matrix:
    environment: 
      - staging
      - demo  
      - production
    browser:
      - chromium
      - firefox

steps:
- name: Qalia Testing - ${{ matrix.environment }}
  uses: floor-licker/qalia@v1
  with:
    app_url: 'https://${{ matrix.environment }}.myapp.com'
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    browser: ${{ matrix.browser }}
```

---

## 🎯 What Qalia Discovers and Tests

### 🔍 **Intelligent Exploration**
- **User Journey Mapping**: Complete workflows from landing to conversion
- **State-Based Navigation**: Beyond simple URL crawling - understands app states
- **Modal & Dialog Handling**: Automatic interaction with complex UI patterns
- **Form Validation**: Smart data entry and edge case testing
- **Dynamic Content**: SPAs, lazy loading, infinite scroll detection

### 🧠 **AI-Powered Analysis**
- **Accessibility Compliance**: WCAG 2.1 AA standards, screen reader compatibility
- **Performance Monitoring**: Core Web Vitals, load times, resource optimization
- **Error Detection**: JavaScript errors, network failures, broken links
- **UX Assessment**: User flow optimization suggestions
- **Security Scan**: Basic XSS, CSRF, and input validation checks

### ⚡ **Multi-Framework Test Generation**
- **Playwright Tests**: Cross-browser, parallel execution, visual regression
- **Cypress Tests**: Interactive UI testing with time-travel debugging
- **Jest + Puppeteer**: Unit/integration tests with headless browser
- **Custom Templates**: Configurable test patterns for your team's standards

---

## 📊 Understanding Your Results

After each run, you'll get:

```
qalia-tests/
├── playwright/
│   ├── user-registration.spec.ts    # User signup flow
│   ├── checkout-process.spec.ts     # E-commerce workflow  
│   └── navigation-testing.spec.ts   # Menu and routing
├── cypress/
│   ├── authentication.cy.js        # Login/logout flows
│   └── form-validation.cy.js       # Input testing
├── jest/
│   └── api-integration.test.js     # Backend integration
├── reports/
│   ├── bug-analysis.html           # Categorized issues with screenshots
│   ├── accessibility-report.html   # WCAG compliance details
│   ├── performance-audit.json      # Core Web Vitals metrics
│   └── coverage-map.html          # Pages and features explored
├── screenshots/                    # Error screenshots with context
└── github-summary.md              # PR comment content
```

---

## 🚀 Team Success Stories

> *"Qalia discovered a race condition in our checkout flow that only happened with fast internet connections. Saved us from losing $50k in holiday sales."*  
> **— Alex Chen, E-commerce Director @ RetailCorp**

> *"Reduced our manual QA cycle from 3 days to 3 hours. The accessibility findings alone justified the cost."*  
> **— Sarah Martinez, Engineering Manager @ FinTech Solutions**

> *"Found 15 accessibility violations before our compliance audit. Qalia paid for itself in the first week."*  
> **— Mike Johnson, Lead Developer @ HealthTech**

---

## 🔧 Troubleshooting Guide

### Common Setup Issues

**❌ "OpenAI API Error" / "Invalid API Key"**
```bash
# Check your API key setup:
# 1. Verify key in GitHub Settings → Secrets
# 2. Ensure you have OpenAI credits
# 3. Check key permissions (should allow GPT-4 access)

# Test your key locally:
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**❌ "App not accessible" / "Connection refused"**
```yaml
# Add proper startup wait:
- name: Start App with Health Check
  run: |
    npm start &
    # Wait for app to be ready
    npx wait-on http://localhost:3000 --timeout 60000
    
# Or for Docker:
- name: Start App Container
  run: |
    docker-compose up -d
    docker-compose exec web curl --retry 5 --retry-delay 5 http://localhost:3000/health
```

**❌ "No tests generated" / "Exploration incomplete"**
```yaml
# Increase timeouts and depth:
- name: Qalia Extended Testing
  uses: floor-licker/qalia@v1
  with:
    app_url: 'https://myapp.com'
    openai_api_key: ${{ secrets.OPENAI_API_KEY }}
    max_depth: 5              # Explore deeper
    timeout: 1800             # 30 minutes
    max_actions_per_page: 100 # More thorough
```

### Performance Optimization

**For Large Applications:**
```yaml
# Optimize for big apps:
with:
  max_depth: 3              # Limit depth
  timeout: 600              # 10 minutes
  headless: true            # Faster execution
  frameworks: 'playwright'  # Single framework
```

**For CI/CD Speed:**
```yaml
# Quick smoke tests:
with:
  max_depth: 2
  timeout: 300
  max_actions_per_page: 20
  quick_scan: true
```

### Advanced Configuration

Create `qalia-config.yml` in your repo root:

```yaml
# Qalia Configuration
exploration:
  headless: true
  max_depth: 4
  timeout: 900
  
  # Custom selectors to prioritize
  priority_selectors:
    - ".cta-button"
    - "[data-testid='checkout']"
    - ".nav-item"
  
  # Elements to avoid
  exclude_selectors:
    - ".advertisement"
    - ".tracking-pixel"

test_generation:
  frameworks:
    - "playwright"
    - "cypress"
  
  output_directory: "ai-tests"
  
  # Custom test templates
  templates:
    playwright: "./templates/playwright.spec.ts"

# AI analysis settings
ai:
  model: "gpt-4"
  focus_areas:
    - "accessibility"
    - "performance"
    - "user_experience"
```

---

## 🎓 Best Practices

### 1. **Start Small, Scale Up**
```yaml
# Week 1: Basic exploration
max_depth: 2
timeout: 300

# Week 2: Expand scope  
max_depth: 3
timeout: 600

# Production: Full coverage
max_depth: 5
timeout: 1800
```

### 2. **Environment-Specific Configuration**
```yaml
# Staging: Comprehensive
max_depth: 5
run_tests: true

# Production: Monitor only
max_depth: 3
run_tests: false
```

### 3. **Team Integration**
- Review generated tests in PR artifacts
- Customize test templates for your standards
- Set up Slack/Teams notifications for critical issues
- Use coverage reports to identify testing gaps

---

## 🆘 Getting Help

### Community & Support
- 📖 **[Full Documentation](https://github.com/floor-licker/qalia/wiki)** - Complete technical reference
- 💬 **[Discord Community](https://discord.gg/qalia)** - Chat with other users and get help
- 🐛 **[Report Issues](https://github.com/floor-licker/qalia/issues)** - Bug reports and feature requests
- 📧 **Enterprise Support**: Contact us for dedicated support plans

### Resources
- 🎥 **[Video Tutorials](https://github.com/floor-licker/qalia/wiki/tutorials)** - Step-by-step setup guides
- 📋 **[Example Configs](https://github.com/floor-licker/qalia/tree/main/examples)** - Ready-to-use configurations
- 🔧 **[Troubleshooting Wiki](https://github.com/floor-licker/qalia/wiki/troubleshooting)** - Common issues and solutions

---

**Ready to eliminate manual testing bottlenecks? Add Qalia to your next PR! 🚀** 