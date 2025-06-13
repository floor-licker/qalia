# QA AI GitHub App - Installation Guide

This guide will walk you through deploying the QA AI GitHub App so it can automatically test repositories when installed.

## 🚀 Quick Start (5 minutes)

### Step 1: Deploy to Render

1. **Go to [Render](https://render.com)** and sign up/login
2. **Click "New +"** → **"Web Service"**
3. **Choose "Public Git Repository"**
4. **Repository URL**: `https://github.com/webisoftSoftware/qalia`
5. **Root Directory**: `qalia-github-app`
6. **Click "Connect"**

### Step 2: Configure Environment Variables

In Render, add these environment variables:

```bash
# Required
GITHUB_APP_ID=          # (You'll get this in Step 3)
GITHUB_WEBHOOK_SECRET=  # (You'll create this in Step 3)
OPENAI_API_KEY=         # Your OpenAI API key

# Deployment URL Pattern (customize for your apps)
DEFAULT_DEPLOY_URL=https://{repo}.herokuapp.com
```

### Step 3: Create GitHub App

1. **Go to GitHub** → Settings → Developer settings → GitHub Apps
2. **Click "New GitHub App"**
3. **Fill in details**:
   - **App name**: "QA AI - YourCompany"
   - **Homepage URL**: Your Render URL (e.g., `https://your-app.onrender.com`)
   - **Webhook URL**: Your Render URL + `/webhook`
   - **Webhook secret**: Generate a random string (save this!)

4. **Set Permissions**:
   - Repository permissions:
     - **Contents**: Read
     - **Pull requests**: Read & Write  
     - **Checks**: Read & Write
   - Subscribe to events:
     - **Pull requests**
     - **Push**

5. **After creation**:
   - Copy the **App ID** 
   - Generate and download the **Private Key** (.pem file)

### Step 4: Upload Private Key

1. **In your Render dashboard**, go to your service
2. **Go to "Shell"** tab
3. **Upload the private key**:
   ```bash
   # Create the app directory if it doesn't exist
   mkdir -p app
   
   # Upload your private key file as app/private-key.pem
   # You can use the file upload feature in Render's shell
   ```

### Step 5: Update Environment Variables

Back in Render, update your environment variables with the real values:

```bash
GITHUB_APP_ID=123456                    # Your actual App ID
GITHUB_WEBHOOK_SECRET=your_secret_here  # The secret you generated
```

### Step 6: Install the App

1. **Go to your GitHub App settings**
2. **Click "Install App"**
3. **Choose repositories** to install it on
4. **Click "Install"**

## ✅ Test It

1. **Create a pull request** in a repository where you installed the app
2. **Check the PR** - you should see:
   - A "QA AI Analysis" check run
   - A comment from the app with analysis results

## 🔧 Customization

### Deployment URL Patterns

The app needs to know where your applications are deployed. Configure this with:

**Generic Pattern** (recommended):
```bash
DEFAULT_DEPLOY_URL=https://{repo}.yourdomain.com
```

**Specific Overrides**:
```bash
DEPLOY_URL_MYCOMPANY_WEBAPP=https://app.mycompany.com
DEPLOY_URL_MYCOMPANY_API=https://api.mycompany.com
```

### Analysis Settings

```bash
MAX_ANALYSIS_TIMEOUT=600                # Max time per analysis (seconds)
MAX_EXPLORATION_DEPTH=3                 # How deep to explore your app
DEFAULT_FRAMEWORKS=playwright,cypress,jest  # Test frameworks to generate
```

### Feature Toggles

```bash
ENABLE_PR_COMMENTS=true                 # Post comments on PRs
ENABLE_CHECK_RUNS=true                  # Create GitHub check runs
```

## 🐛 Troubleshooting

### App not responding to webhooks
- Check webhook URL is correct (should end with `/webhook`)
- Verify webhook secret matches
- Check Render logs for errors

### "Private key file not found"
- Ensure private key is uploaded as `app/private-key.pem`
- Check file permissions

### Analysis fails
- Verify `DEFAULT_DEPLOY_URL` is configured correctly
- Ensure your app is deployed and accessible
- Check OpenAI API key is valid

### No test files generated
- Check application logs for errors
- Verify OpenAI API key has sufficient credits
- Ensure target application is fully loaded

## 📞 Support

- Check the [main README](README.md) for detailed documentation
- Review Render logs for error messages
- Verify GitHub App webhook deliveries in GitHub settings

## 🎉 Success!

Once set up, the QA AI GitHub App will:
- ✅ Automatically analyze every pull request
- ✅ Generate comprehensive test suites
- ✅ Post results directly to GitHub
- ✅ Help improve your application quality

Your team can now focus on building features while QA AI handles the testing! 