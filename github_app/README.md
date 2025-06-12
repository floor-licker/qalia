# QALIA GitHub App

This is the GitHub App version of QALIA, which provides automated QA analysis for your repositories.

## Setup

1. Create a new GitHub App in your GitHub account:
   - Go to Settings > Developer Settings > GitHub Apps
   - Click "New GitHub App"
   - Set the following permissions:
     - Repository permissions:
       - Contents: Read
       - Pull requests: Read & Write
       - Checks: Read & Write
     - Subscribe to events:
       - Pull requests
       - Push

2. After creating the app, you'll need:
   - App ID
   - Private key (download and save it)
   - Webhook secret (generate one)

3. Create a `.env` file with the following variables:
   ```
   GITHUB_APP_ID=your_app_id
   GITHUB_APP_PRIVATE_KEY="""-----BEGIN RSA PRIVATE KEY-----
   your_private_key_here
   -----END RSA PRIVATE KEY-----"""
   GITHUB_WEBHOOK_SECRET=your_webhook_secret
   OPENAI_API_KEY=your_openai_api_key
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Run the server:
   ```bash
   python app/server.py
   ```

## Development

The app uses FastAPI for the webhook server. Key components:

- `server.py`: Main FastAPI application
- Webhook handlers for different GitHub events
- Integration with QALIA core functionality

## Deployment

For production deployment:

1. Set up a reverse proxy (e.g., Nginx) to handle HTTPS
2. Use a process manager (e.g., Supervisor) to keep the app running
3. Set up proper environment variables
4. Configure GitHub App webhook URL to point to your server

## Security

- All webhook requests are verified using the webhook secret
- GitHub App authentication uses JWT and installation tokens
- Private keys and secrets are stored in environment variables 