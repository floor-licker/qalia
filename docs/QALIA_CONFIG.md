# 📋 Qalia Configuration Guide

This guide explains how to configure Qalia using the `qalia.yml` configuration file to automatically deploy and test your applications.

## 🚀 Quick Start

Create a `qalia.yml` file in your repository root:

```yaml
# Minimal configuration
deployment:
  type: "static"
  start:
    command: "python -m http.server 8080"
    port: 8080

testing:
  entry_points:
    - url: "/"
      name: "Homepage"
```

## 📖 Complete Configuration Reference

### 🏗️ Deployment Configuration

The `deployment` section tells Qalia how to build and run your application for testing.

#### Static Sites

```yaml
deployment:
  type: "static"
  build:
    - "npm run build"  # Optional build commands
  start:
    command: "python -m http.server 8080"
    port: 8080
    build_dir: "dist"  # Directory to serve (default: current directory)
```

#### Node.js Applications

```yaml
deployment:
  type: "npm"
  build:
    - "npm install"
    - "npm run build"
  start:
    command: "npm start"
    port: 3000
    wait_for_ready: 30
    health_check: "http://localhost:3000/health"
  
environment:
  variables:
    NODE_ENV: "test"
    API_URL: "http://localhost:3001"
```

#### Python Applications

```yaml
deployment:
  type: "python"
  build:
    - "pip install -r requirements.txt"
  start:
    command: "python app.py"
    port: 5000
    wait_for_ready: 20
```

#### Docker Applications

```yaml
deployment:
  type: "docker"
  docker:
    image: "my-app"
    port: 3000
    build_args:
      - "NODE_ENV=test"
```

#### Custom Deployment

```yaml
deployment:
  type: "custom"
  custom:
    setup:
      - "make install"
      - "make build"
    start_command: "./start-server.sh"
    url: "http://localhost:8080"
```

#### Existing Deployment

```yaml
deployment:
  url: "https://my-app.herokuapp.com"  # Skip local deployment
```

### 🧪 Testing Configuration

#### Entry Points

Define the main pages/routes for Qalia to explore:

```yaml
testing:
  entry_points:
    - url: "/"
      name: "Homepage"
      description: "Main landing page"
    - url: "/login"
      name: "Login Page"
      description: "User authentication"
    - url: "/dashboard"
      name: "User Dashboard"
      description: "Main user interface"
```

#### Exploration Settings

```yaml
testing:
  exploration:
    max_depth: 3          # How deep to explore (default: 3)
    timeout: 300          # Total timeout in seconds (default: 300)
    headless: true        # Run browser in headless mode (default: true)
    viewport:
      width: 1920         # Browser width (default: 1920)
      height: 1080        # Browser height (default: 1080)
```

#### Test Generation

```yaml
testing:
  generation:
    frameworks: ["playwright", "cypress", "jest"]  # Which frameworks to generate
    output_dir: "qalia-tests"                      # Output directory
    include_accessibility: true                    # Generate accessibility tests
    include_performance: true                      # Generate performance tests
```

### 🔐 Authentication

For applications that require login:

```yaml
authentication:
  enabled: true
  type: "form"  # Options: form, oauth, api_key, custom
  credentials:
    username: "test@example.com"
    password: "testpassword"
  login_url: "/login"
  success_indicator: ".user-menu"  # CSS selector that appears when logged in
```

### 🎯 Custom Scenarios

Define specific user journeys to test:

```yaml
scenarios:
  - name: "User Registration"
    description: "Test user signup process"
    steps:
      - action: "navigate"
        url: "/register"
      - action: "fill_form"
        selector: "#registration-form"
        data:
          email: "newuser@example.com"
          password: "password123"
      - action: "click"
        selector: "#submit-btn"
      - action: "wait_for"
        selector: ".success-message"

  - name: "Product Purchase"
    description: "Test e-commerce checkout"
    steps:
      - action: "navigate"
        url: "/products"
      - action: "click"
        selector: ".product:first-child .buy-btn"
      - action: "fill_form"
        selector: "#checkout-form"
        data:
          name: "Test User"
          email: "test@example.com"
```

### 🚫 Exclusions

Specify areas to avoid during exploration:

```yaml
exclusions:
  urls:
    - "/admin/*"      # Skip admin pages
    - "/api/*"        # Skip API endpoints
    - "*/logout"      # Avoid logout links
  
  selectors:
    - ".delete-btn"                    # Avoid destructive actions
    - ".logout-link"                   # Don't click logout
    - "[data-destructive='true']"      # Skip dangerous elements
```

### 🌍 Environment Setup

For applications requiring additional services:

```yaml
environment:
  variables:
    NODE_ENV: "test"
    DATABASE_URL: "sqlite:///test.db"
    API_KEY: "test-key-123"
  
  services:
    - name: "database"
      command: "docker run -d -p 5432:5432 postgres:13"
      health_check: "pg_isready -h localhost -p 5432"
    
    - name: "redis"
      command: "redis-server --port 6380"
      port: 6380
      health_check: "redis-cli -p 6380 ping"
```

### 📢 Notifications

Configure how Qalia reports results:

```yaml
notifications:
  github:
    enabled: true
    create_check_run: true
    comment_on_pr: true
  
  slack:
    enabled: false
    webhook_url: "${SLACK_WEBHOOK_URL}"
  
  email:
    enabled: false
    recipients: ["team@example.com"]
```

## 📝 Configuration Examples

### React Application

```yaml
deployment:
  type: "npm"
  build:
    - "npm install"
    - "npm run build"
  start:
    command: "npm start"
    port: 3000

testing:
  entry_points:
    - url: "/"
      name: "Homepage"
    - url: "/about"
      name: "About Page"
  exploration:
    max_depth: 2
    timeout: 180
  generation:
    frameworks: ["playwright", "cypress"]
```

### Django Application

```yaml
deployment:
  type: "python"
  build:
    - "pip install -r requirements.txt"
    - "python manage.py migrate"
    - "python manage.py collectstatic --noinput"
  start:
    command: "python manage.py runserver 8000"
    port: 8000

environment:
  variables:
    DJANGO_SETTINGS_MODULE: "myapp.settings.test"
    DEBUG: "True"

authentication:
  enabled: true
  type: "form"
  credentials:
    username: "admin"
    password: "testpass123"
  login_url: "/admin/login/"
  success_indicator: "#user-tools"
```

### Next.js Application

```yaml
deployment:
  type: "npm"
  build:
    - "npm install"
    - "npm run build"
  start:
    command: "npm start"
    port: 3000
    wait_for_ready: 45

testing:
  entry_points:
    - url: "/"
      name: "Homepage"
    - url: "/products"
      name: "Products"
    - url: "/contact"
      name: "Contact"
  
  generation:
    frameworks: ["playwright", "jest"]
    include_accessibility: true
    include_performance: true

scenarios:
  - name: "Product Search"
    steps:
      - action: "navigate"
        url: "/products"
      - action: "fill_form"
        selector: "#search-form"
        data:
          query: "laptop"
      - action: "click"
        selector: "#search-btn"
      - action: "wait_for"
        selector: ".product-results"
```

### Static Site (Hugo/Jekyll)

```yaml
deployment:
  type: "static"
  build:
    - "hugo"  # or "bundle exec jekyll build"
  start:
    command: "python -m http.server 8080"
    port: 8080
    build_dir: "public"  # or "_site" for Jekyll

testing:
  entry_points:
    - url: "/"
      name: "Homepage"
    - url: "/blog/"
      name: "Blog"
    - url: "/about/"
      name: "About"
  
  exploration:
    max_depth: 2
    timeout: 120
```

## 🔧 Advanced Configuration

### Multi-Service Applications

```yaml
deployment:
  type: "custom"
  custom:
    setup:
      - "docker-compose up -d database redis"
      - "npm install"
      - "npm run build"
    start_command: "npm start"
    url: "http://localhost:3000"

environment:
  services:
    - name: "database"
      command: "docker-compose up -d postgres"
      health_check: "pg_isready -h localhost -p 5432"
    - name: "redis"
      command: "docker-compose up -d redis"
      health_check: "redis-cli ping"
```

### Conditional Configuration

```yaml
deployment:
  type: "npm"
  build:
    - "npm install"
    - "npm run build:${NODE_ENV:-test}"
  start:
    command: "npm run start:test"
    port: 3000

environment:
  variables:
    NODE_ENV: "test"
    DATABASE_URL: "${TEST_DATABASE_URL:-sqlite:///test.db}"
```

## 🚨 Common Issues & Solutions

### Application Won't Start

```yaml
# Increase wait time and add health check
deployment:
  start:
    command: "npm start"
    port: 3000
    wait_for_ready: 60  # Increase from default 30
    health_check: "http://localhost:3000/health"
```

### Authentication Issues

```yaml
# Use more specific success indicator
authentication:
  enabled: true
  success_indicator: "[data-testid='user-menu']"  # More specific than ".user-menu"
```

### Exploration Timeout

```yaml
# Reduce scope or increase timeout
testing:
  exploration:
    max_depth: 2      # Reduce from 3
    timeout: 600      # Increase from 300
```

## 📚 Best Practices

1. **Start Simple**: Begin with minimal configuration and add complexity as needed
2. **Use Health Checks**: Always specify health check URLs for reliable deployment detection
3. **Specific Selectors**: Use data attributes or specific CSS selectors for authentication indicators
4. **Environment Isolation**: Use test-specific environment variables and databases
5. **Reasonable Timeouts**: Balance thoroughness with execution time
6. **Exclude Destructive Actions**: Always exclude logout, delete, and other destructive elements

## 🆘 Getting Help

- **Configuration Issues**: Check the logs in your GitHub Actions or Render dashboard
- **Deployment Problems**: Verify your build and start commands work locally
- **Authentication Failures**: Test your login credentials and success indicators manually
- **Missing Tests**: Ensure your entry points are accessible and your application is fully loaded

For more help, open an issue in the [Qalia repository](https://github.com/floor-licker/qalia/issues). 