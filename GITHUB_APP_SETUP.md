# 🤖 Qalia GitHub App Setup Guide

This guide will help you set up Qalia as a GitHub App for automatic QA testing on your repositories.

## 📋 Prerequisites

- GitHub repository with a deployed web application
- OpenAI API key
- Render account (for hosting the GitHub App)

## 🚀 Step 1: Deploy the GitHub App

### Option A: Deploy to Render (Recommended)

1. **Fork this repository** to your GitHub account
2. **Go to [Render](https://render.com)** and create a new Web Service
3. **Connect your forked repository**
4. **Configure the service**:
   - **Build Command**: `pip install -r requirements.txt && playwright install chromium --with-deps`
   - **Start Command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Environment**: Python 3

### Option B: Deploy with Docker

```bash
# Build the image
docker build -t qalia-github-app .

# Run the container
docker run -p 8000:8000 \
  -e GITHUB_APP_ID=your_app_id \
  -e GITHUB_WEBHOOK_SECRET=your_webhook_secret \
  -e OPENAI_API_KEY=your_openai_key \
  qalia-github-app
```

## 🔧 Step 2: Create GitHub App

1. **Go to GitHub Settings** → Developer settings → GitHub Apps
2. **Click "New GitHub App"**
3. **Fill in the details**:
   - **App name**: `Qalia QA AI` (or your preferred name)
   - **Homepage URL**: Your Render app URL (e.g., `https://your-app.onrender.com`)
   - **Webhook URL**: Your Render app URL + `/webhook` (e.g., `https://your-app.onrender.com/webhook`)
   - **Webhook secret**: Generate a secure random string

4. **Set Permissions**:
   - **Repository permissions**:
     - Contents: Read
     - Issues: Write
     - Pull requests: Write
     - Checks: Write
   - **Subscribe to events**:
     - Pull request
     - Push

5. **Create the app** and note down the **App ID**

6. **Generate a private key** and download the `.pem` file

## 🔐 Step 3: Configure Environment Variables

In your Render dashboard (or deployment platform), set these environment variables:

```bash
# GitHub App Configuration
GITHUB_APP_ID=123456  # Your GitHub App ID
GITHUB_WEBHOOK_SECRET=your_webhook_secret
OPENAI_API_KEY=sk-your-openai-api-key

# Deployment URL Configuration
DEFAULT_DEPLOY_URL=https://{repo}.herokuapp.com
# Or set specific URLs:
# DEPLOY_URL_MYORG_MYAPP=https://myapp.herokuapp.com

# QA AI Configuration (optional)
MAX_ANALYSIS_TIMEOUT=600
MAX_EXPLORATION_DEPTH=3
DEFAULT_FRAMEWORKS=playwright,cypress,jest
ENABLE_PR_COMMENTS=true
ENABLE_CHECK_RUNS=true
```

## 📁 Step 4: Upload Private Key

1. **In Render**, go to your service settings
2. **Upload the private key file** as `private-key.pem` in the root directory
3. **Or use the shell** to upload:
   ```bash
   # In Render shell
   cat > private-key.pem << 'EOF'
   -----BEGIN RSA PRIVATE KEY-----
   [paste your private key content here]
   -----END RSA PRIVATE KEY-----
   EOF
   ```

## 🎯 Step 5: Install on Repositories

1. **Go to your GitHub App settings**
2. **Click "Install App"**
3. **Choose repositories** to install on
4. **Grant permissions**

## ✅ Step 6: Test the Installation

1. **Create a pull request** in one of your repositories
2. **Check that Qalia**:
   - Creates a check run
   - Comments on the PR with analysis results
   - Analyzes your deployed application

## 🔧 Configuration Options

### Deployment URL Patterns

Qalia needs to know where your applications are deployed. Configure using:

```bash
# Generic pattern (recommended)
DEFAULT_DEPLOY_URL=https://{repo}.herokuapp.com

# Specific repository URLs
DEPLOY_URL_MYORG_WEBAPP=https://webapp.mycompany.com
DEPLOY_URL_MYORG_API=https://api.mycompany.com
```

### Framework Selection

Choose which test frameworks to generate:

```bash
DEFAULT_FRAMEWORKS=playwright,cypress,jest  # All frameworks
DEFAULT_FRAMEWORKS=playwright              # Playwright only
DEFAULT_FRAMEWORKS=cypress,jest            # Cypress and Jest
```

### Feature Toggles

Control app behavior:

```bash
ENABLE_PR_COMMENTS=true   # Comment on pull requests
ENABLE_CHECK_RUNS=true    # Create GitHub check runs
MAX_EXPLORATION_DEPTH=3   # How deep to explore (1-5)
MAX_ANALYSIS_TIMEOUT=600  # Timeout in seconds
```

## 🐛 Troubleshooting

### Common Issues

1. **"Private key not found"**
   - Ensure `private-key.pem` is in the root directory
   - Check file permissions and content

2. **"Invalid webhook signature"**
   - Verify `GITHUB_WEBHOOK_SECRET` matches your GitHub App settings
   - Check for extra spaces or characters

3. **"QA AI modules not available"**
   - Ensure all dependencies are installed
   - Check that Playwright browsers are installed

4. **"Unable to determine deployment URL"**
   - Set `DEFAULT_DEPLOY_URL` or specific repository URLs
   - Ensure your application is accessible

### Logs and Debugging

Check your Render logs for detailed error messages:

```bash
# In Render shell
tail -f /var/log/render.log
```

## 📞 Support

If you encounter issues:

1. Check the [GitHub repository](https://github.com/floor-licker/qalia) for documentation
2. Review Render logs for error messages
3. Ensure all environment variables are set correctly
4. Verify your GitHub App permissions and webhook configuration

## 🎉 Success!

Once configured, Qalia will automatically:
- Analyze every pull request
- Generate comprehensive test suites
- Report bugs and issues
- Provide actionable insights

Your development workflow just got a lot smarter! 🚀 