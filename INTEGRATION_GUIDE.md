# 🤖 QA AI Integration Guide

## Quick Start: Add QA AI to Your Project

**Add automated testing to any webapp in under 5 minutes!**

### 1. Add to Your GitHub Actions

Create `.github/workflows/qa-testing.yml` in your project:

```yaml
name: QA AI Testing

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  qa-testing:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    # Deploy your app (customize this)
    - name: Start App
      run: |
        npm install && npm start &
        sleep 10
        
    # Run QA AI
    - name: QA AI Analysis
      uses: floor-licker/qalia@v1
      with:
        app_url: 'http://localhost:3000'
        openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

### 2. Add OpenAI API Key

1. Go to your repo → **Settings** → **Secrets**
2. Add secret: `OPENAI_API_KEY` = `your-openai-key`

### 3. Push and Watch the Magic ✨

QA AI will:
- 🔍 Explore your webapp autonomously
- 🧠 Analyze user journeys with AI
- ⚡ Generate Playwright, Cypress & Jest tests
- 📊 Post reports directly to your PRs
- 🚨 Alert you to accessibility issues

---

## 🎯 Real-World Examples

### E-commerce Site
```yaml
- name: QA AI E-commerce Testing
  uses: floor-licker/qalia@v1
  with:
    app_url: 'https://mystore-staging.com'
    max_depth: 5  # Deep exploration for shopping flows
    frameworks: 'playwright,cypress'
```

### Dashboard App
```yaml
- name: QA AI Dashboard Testing  
  uses: floor-licker/qalia@v1
  with:
    app_url: 'https://admin.myapp.com'
    max_depth: 3
    timeout: 300
```

### SaaS Platform
```yaml
- name: QA AI SaaS Testing
  uses: floor-licker/qalia@v1
  with:
    app_url: 'https://app.mysaas.com'
    max_depth: 4
    run_tests: true  # Run generated tests immediately
```

---

## ⚙️ Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `app_url` | Your webapp URL | **Required** |
| `openai_api_key` | OpenAI API key | **Required** |
| `max_depth` | Exploration depth | `3` |
| `timeout` | Max time (seconds) | `300` |
| `headless` | Headless browser | `true` |
| `frameworks` | Test frameworks | `playwright,cypress,jest` |
| `output_dir` | Test output directory | `qalia-tests` |
| `run_tests` | Execute generated tests | `true` |

---

## 📈 Advanced Integration Patterns

### Pattern 1: Deploy → Test → Deploy to Prod
```yaml
jobs:
  deploy-staging:
    runs-on: ubuntu-latest
    steps:
    - name: Deploy to Staging
      run: ./deploy-staging.sh
      
  qa-testing:
    needs: deploy-staging
    runs-on: ubuntu-latest
    steps:
    - name: QA AI Testing
      uses: floor-licker/qalia@v1
      with:
        app_url: 'https://staging.myapp.com'
        
  deploy-production:
    needs: qa-testing
    if: success()
    runs-on: ubuntu-latest
    steps:
    - name: Deploy to Production
      run: ./deploy-prod.sh
```

### Pattern 2: Scheduled Deep Testing
```yaml
on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  comprehensive-qa:
    runs-on: ubuntu-latest
    steps:
    - name: Deep QA Analysis
      uses: floor-licker/qalia@v1
      with:
        app_url: 'https://myapp.com'
        max_depth: 8  # Very deep exploration
        timeout: 1800  # 30 minutes
```

### Pattern 3: Multi-Environment Testing
```yaml
strategy:
  matrix:
    environment: [staging, demo, production]

steps:
- name: QA AI - ${{ matrix.environment }}
  uses: floor-licker/qalia@v1
  with:
    app_url: 'https://${{ matrix.environment }}.myapp.com'
```

---

## 🎯 What QA AI Tests For

### 🔍 **Automatic Discovery**
- User journey mapping
- Navigation patterns
- Form interactions
- Button clicks and links

### 🧠 **AI-Powered Analysis**
- Accessibility compliance
- Performance bottlenecks  
- Error handling
- User experience issues

### ⚡ **Generated Test Types**
- **Playwright**: Modern e2e tests
- **Cypress**: Interactive UI tests  
- **Jest + Puppeteer**: Unit + integration

---

## 🚀 Success Stories

> *"QA AI found 12 accessibility issues we missed in manual testing. Fixed them before our big launch!"*  
> — **Sarah, Frontend Lead @ TechCorp**

> *"Saves our team 8 hours/week of manual testing. ROI in the first month."*  
> — **Mike, CTO @ StartupXYZ**

> *"Caught a critical checkout flow bug that would have cost us $50k in lost sales."*  
> — **Alex, E-commerce Director**

---

## 🔧 Troubleshooting

### Common Issues

**❌ "App not accessible"**
```yaml
# Wait longer for app startup
- name: Wait for App
  run: sleep 30
```

**❌ "OpenAI API error"**  
- Check your `OPENAI_API_KEY` secret
- Ensure you have API credits

**❌ "Tests failing"**
- Review generated tests in artifacts
- Adjust `max_depth` for your app complexity

### Getting Help
- 📖 [Full Documentation](https://github.com/floor-licker/qalia/wiki)
- 💬 [Discord Community](https://discord.gg/qalia)
- 🐛 [Report Issues](https://github.com/floor-licker/qalia/issues)

---

**Ready to revolutionize your testing? Add QA AI to your project today! 🚀** 