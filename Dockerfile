FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright dependencies
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /qa-ai

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium --with-deps

# Copy the entire QA AI codebase
COPY . .

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Parse inputs from GitHub Actions\n\
APP_URL="${INPUT_APP_URL}"\n\
MAX_DEPTH="${INPUT_MAX_DEPTH:-3}"\n\
TIMEOUT="${INPUT_TIMEOUT:-300}"\n\
HEADLESS="${INPUT_HEADLESS:-true}"\n\
FRAMEWORKS="${INPUT_FRAMEWORKS:-playwright,cypress,jest}"\n\
OUTPUT_DIR="${INPUT_OUTPUT_DIR:-qa-ai-tests}"\n\
RUN_TESTS="${INPUT_RUN_TESTS:-true}"\n\
\n\
echo "🤖 QA AI Docker Container Starting..."\n\
echo "🔗 Target URL: $APP_URL"\n\
echo "🔍 Max Depth: $MAX_DEPTH"\n\
echo "⏱️  Timeout: $TIMEOUT seconds"\n\
echo "📁 Output Directory: $OUTPUT_DIR"\n\
\n\
# Validate inputs\n\
if [ -z "$APP_URL" ]; then\n\
  echo "❌ Error: app_url is required"\n\
  exit 1\n\
fi\n\
\n\
if [ -z "$OPENAI_API_KEY" ]; then\n\
  echo "❌ Error: OPENAI_API_KEY environment variable is required"\n\
  exit 1\n\
fi\n\
\n\
# Build command arguments\n\
CMD_ARGS="$APP_URL --max-depth $MAX_DEPTH --timeout $TIMEOUT"\n\
\n\
if [ "$HEADLESS" = "true" ]; then\n\
  CMD_ARGS="$CMD_ARGS --headless"\n\
fi\n\
\n\
# Parse frameworks (comma-separated to individual args)\n\
IFS="," read -ra FRAMEWORK_ARRAY <<< "$FRAMEWORKS"\n\
FRAMEWORK_ARGS=""\n\
for framework in "${FRAMEWORK_ARRAY[@]}"; do\n\
  FRAMEWORK_ARGS="$FRAMEWORK_ARGS --frameworks $framework"\n\
done\n\
\n\
CMD_ARGS="$CMD_ARGS $FRAMEWORK_ARGS --output-dir /github/workspace/$OUTPUT_DIR"\n\
\n\
# Run QA AI\n\
echo "🚀 Executing: python main.py $CMD_ARGS"\n\
python main.py $CMD_ARGS\n\
\n\
# Set outputs for GitHub Actions\n\
if [ -d "/github/workspace/$OUTPUT_DIR" ]; then\n\
  TEST_COUNT=$(find "/github/workspace/$OUTPUT_DIR" -name "*.spec.ts" -o -name "*.cy.js" -o -name "*.test.js" | wc -l)\n\
  echo "tests_generated=$TEST_COUNT" >> $GITHUB_OUTPUT\n\
  echo "report_path=/github/workspace/$OUTPUT_DIR/qa-ai-summary.md" >> $GITHUB_OUTPUT\n\
  echo "test_results=/github/workspace/$OUTPUT_DIR/test-results.json" >> $GITHUB_OUTPUT\n\
  \n\
  echo "✅ Generated $TEST_COUNT test files"\n\
  echo "📁 Output saved to $OUTPUT_DIR/"\n\
else\n\
  echo "⚠️  No tests were generated"\n\
fi\n\
\n\
echo "🎉 QA AI analysis completed successfully!"\n\
' > /entrypoint.sh

# Make entrypoint executable
RUN chmod +x /entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"] 