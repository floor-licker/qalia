# QALIA GitHub App

This is the GitHub App version of QALIA, which provides automated QA analysis for your repositories. When installed on a repository, it automatically runs QA AI analysis on pull requests and pushes, generating comprehensive test suites and posting results directly to GitHub.

## Features

- 🤖 **Automatic Analysis**: Runs QA AI on every PR and push to main
- 📝 **Test Generation**: Creates Playwright, Cypress, and Jest test files
- ✅ **GitHub Integration**: Posts results as check runs and PR comments
- 🔍 **Comprehensive Coverage**: Analyzes UI interactions, navigation, forms, and error handling
- 🚀 **Ready-to-Deploy**: Configured for Render, Heroku, and other platforms

## Quick Deploy to Render

1. **Fork this repository** or use it as a template
2. **Deploy to Render**:
   - Choose "Public Git Repository" in Render
   - Repository URL: `https://github.com/webisoftSoftware/qalia`
   - Root Directory: `qalia-github-app`
3. **Set environment variables** (see Configuration section below)
4. **Create your GitHub App** (see GitHub App Setup section)
5. **Install the app** on your repositories

## GitHub App Setup

1. **Create a new GitHub App**:
   - Go to Settings > Developer Settings > GitHub Apps
   - Click "New GitHub App"
   - **App Name**: "QA AI - Your Company"
   - **Homepage URL**: Your Render app URL (e.g., `https://your-app.onrender.com`)
   - **Webhook URL**: Your Render app URL + `/webhook` (e.g., `https://your-app.onrender.com/webhook`)
   - **Webhook Secret**: Generate a random string (save this)

2. **Set Permissions**:
   - Repository permissions:
     - **Contents**: Read
     - **Pull requests**: Read & Write
     - **Checks**: Read & Write
   - Subscribe to events:
     - **Pull requests**
     - **Push**

3. **After creating the app**:
   - Note the **App ID**
   - Generate and download the **Private Key** (.pem file)
   - Save the **Webhook Secret** you created

## Configuration

Set these environment variables in your deployment platform:

### Required Variables
```bash
GITHUB_APP_ID=123456                    # Your GitHub App ID
GITHUB_WEBHOOK_SECRET=your_webhook_secret # Webhook secret you generated
OPENAI_API_KEY=sk-...                   # Your OpenAI API key
```

### Optional Variables
```bash
# Deployment URL patterns (customize for your hosting)
DEFAULT_DEPLOY_URL=https://{repo}.herokuapp.com  # Default pattern
DEPLOY_URL_MYCOMPANY_MYAPP=https://myapp.mycompany.com  # Specific override

# Analysis settings
MAX_ANALYSIS_TIMEOUT=600                # Max analysis time (seconds)
MAX_EXPLORATION_DEPTH=3                 # How deep to explore
DEFAULT_FRAMEWORKS=playwright,cypress,jest  # Test frameworks to generate

# Feature toggles
ENABLE_PR_COMMENTS=true                 # Post PR comments
ENABLE_CHECK_RUNS=true                  # Create check runs
```

### Deployment URL Configuration

The app needs to know where your applications are deployed. Configure this using:

1. **Generic Pattern** (recommended):
   ```bash
   DEFAULT_DEPLOY_URL=https://{repo}.yourdomain.com
   ```
   - `{repo}` = repository name
   - `{org}` = organization name
   - `{branch}` = git branch

2. **Specific Overrides**:
   ```bash
   DEPLOY_URL_MYCOMPANY_WEBAPP=https://app.mycompany.com
   DEPLOY_URL_MYCOMPANY_API=https://api.mycompany.com
   ```

3. **Common Patterns**:
   - Heroku: `https://{repo}.herokuapp.com`
   - Vercel: `https://{repo}.vercel.app`
   - Netlify: `https://{repo}.netlify.app`
   - Render: `https://{repo}.onrender.com`

## How It Works

1. **Installation**: Install the GitHub App on repositories you want to analyze
2. **Trigger**: App automatically runs when:
   - Pull requests are opened or updated
   - Code is pushed to the main branch
3. **Analysis**: QA AI explores the deployed application and generates tests
4. **Results**: Results are posted as:
   - GitHub check runs (✅/❌ status)
   - Pull request comments with detailed analysis
   - Downloadable test files (when available)

## Local Development

1. **Clone and setup**:
   ```bash
   git clone https://github.com/webisoftSoftware/qalia.git
   cd qalia/qalia-github-app
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Create `.env` file**:
   ```bash
   GITHUB_APP_ID=your_app_id
   GITHUB_WEBHOOK_SECRET=your_webhook_secret
   OPENAI_API_KEY=your_openai_api_key
   DEFAULT_DEPLOY_URL=http://localhost:3000  # For testing
   ```

3. **Add private key**:
   - Save your GitHub App private key as `app/private-key.pem`

4. **Run the server**:
   ```bash
   uvicorn app.server:app --reload --port 8000
   ```

5. **Test webhook** (use ngrok for local testing):
   ```bash
   ngrok http 8000
   # Use the ngrok URL as your webhook URL in GitHub App settings
   ```

## Deployment Platforms

### Render (Recommended)
- Uses the included `render.yaml` configuration
- Automatically installs dependencies and Playwright
- Easy environment variable management

### Heroku
```bash
# Add buildpacks
heroku buildpacks:add heroku/python
heroku buildpacks:add https://github.com/mxschmitt/heroku-playwright-buildpack

# Set environment variables
heroku config:set GITHUB_APP_ID=123456
heroku config:set GITHUB_WEBHOOK_SECRET=your_secret
heroku config:set OPENAI_API_KEY=sk-...
```

### Docker
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN playwright install chromium --with-deps
COPY . .
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Troubleshooting

### Common Issues

1. **"QA AI modules not available"**
   - Ensure the parent QA AI code is accessible
   - Check Python path configuration

2. **"Private key file not found"**
   - Ensure `private-key.pem` is in the `app/` directory
   - Check file permissions

3. **"OpenAI API key not configured"**
   - Set the `OPENAI_API_KEY` environment variable
   - Verify the API key is valid

4. **Analysis fails with deployment URL errors**
   - Configure `DEFAULT_DEPLOY_URL` or specific overrides
   - Ensure your application is deployed and accessible

### Logs and Monitoring

- Check application logs for detailed error messages
- Monitor webhook delivery in GitHub App settings
- Use health check endpoint: `GET /` returns app status

## Security

- ✅ Webhook signature verification
- ✅ GitHub App JWT authentication
- ✅ Environment variable configuration
- ✅ No secrets in code or logs
- ✅ Temporary file cleanup 