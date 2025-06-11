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
WORKDIR /qalia

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
OUTPUT_DIR="${INPUT_OUTPUT_DIR:-qalia-tests}"\n\
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
START_TIME=$(date +%s)\n\
python main.py $CMD_ARGS\n\
END_TIME=$(date +%s)\n\
DURATION=$((END_TIME - START_TIME))\n\
\n\
# Generate GitHub Actions Summary\n\
WORKSPACE_DIR="/github/workspace/$OUTPUT_DIR"\n\
SUMMARY_FILE="$WORKSPACE_DIR/github-summary.md"\n\
\n\
if [ -d "$WORKSPACE_DIR" ]; then\n\
  # Count generated files\n\
  TEST_COUNT=$(find "$WORKSPACE_DIR" -name "*.spec.ts" -o -name "*.cy.js" -o -name "*.test.js" | wc -l)\n\
  SUITE_COUNT=$(find "$WORKSPACE_DIR" -name "*.test.js" -o -name "*.spec.ts" -o -name "*.cy.js" | xargs dirname | sort -u | wc -l)\n\
  \n\
  # Create summary markdown\n\
  cat > "$SUMMARY_FILE" << EOF\n\
# 🤖 QA AI Test Generation Report\n\
\n\
## 📊 Summary\n\
\n\
| Metric | Value |\n\
|--------|-------|\n\
| **Target Application** | \`$APP_URL\` |\n\
| **Test Cases Generated** | **$TEST_COUNT** |\n\
| **Test Suites Created** | **$SUITE_COUNT** |\n\
| **Analysis Duration** | ${DURATION}s |\n\
| **Max Exploration Depth** | $MAX_DEPTH |\n\
| **Frameworks** | \`$FRAMEWORKS\` |\n\
\n\
## 🎯 Generated Test Files\n\
\n\
EOF\n\
\n\
  # List generated test files\n\
  find "$WORKSPACE_DIR" -name "*.test.js" -o -name "*.spec.ts" -o -name "*.cy.js" | while read file; do\n\
    filename=$(basename "$file")\n\
    echo "- 📝 \`$filename\`" >> "$SUMMARY_FILE"\n\
  done\n\
\n\
  # Add generation summary if available\n\
  if [ -f "$WORKSPACE_DIR/generation_summary.json" ]; then\n\
    echo "" >> "$SUMMARY_FILE"\n\
    echo "## 📈 Detailed Analysis" >> "$SUMMARY_FILE"\n\
    echo "" >> "$SUMMARY_FILE"\n\
    \n\
    # Extract key metrics from JSON (basic parsing)\n\
    if command -v python3 >/dev/null 2>&1; then\n\
      python3 -c "\n\
import json\n\
import sys\n\
try:\n\
    with open(\"$WORKSPACE_DIR/generation_summary.json\") as f:\n\
        data = json.load(f)\n\
    \n\
    summary = data.get(\"generation_summary\", {})\n\
    breakdown = data.get(\"test_breakdown\", {})\n\
    suites = data.get(\"test_suites\", [])\n\
    \n\
    print(\"### Test Case Breakdown\")\n\
    print(\"\")\n\
    \n\
    if \"by_priority\" in breakdown:\n\
        priorities = breakdown[\"by_priority\"]\n\
        print(\"**By Priority:**\")\n\
        for priority, count in priorities.items():\n\
            if count > 0:\n\
                emoji = \"🔴\" if priority == \"critical\" else \"🟡\" if priority == \"high\" else \"🟢\"\n\
                print(f\"- {emoji} {priority.title()}: {count} test(s)\")\n\
        print(\"\")\n\
    \n\
    if suites:\n\
        print(\"### Test Suites\")\n\
        print(\"\")\n\
        for suite in suites:\n\
            name = suite.get(\"name\", \"Unknown\")\n\
            desc = suite.get(\"description\", \"No description\")\n\
            count = suite.get(\"test_count\", 0)\n\
            duration = suite.get(\"estimated_duration\", 0)\n\
            print(f\"**{name}** - {desc}\")\n\
            print(f\"- Tests: {count}\")\n\
            print(f\"- Estimated Duration: {duration}s\")\n\
            print(\"\")\n\
            \n\
except Exception as e:\n\
    print(f\"Unable to parse generation summary: {e}\")\n\
" >> "$SUMMARY_FILE"\n\
    fi\n\
  fi\n\
\n\
  # Add download instructions\n\
  echo "" >> "$SUMMARY_FILE"\n\
  echo "## 📁 Artifacts" >> "$SUMMARY_FILE"\n\
  echo "" >> "$SUMMARY_FILE"\n\
  echo "Generated test files and reports are available as workflow artifacts:" >> "$SUMMARY_FILE"\n\
  echo "1. Click on the **Summary** tab above" >> "$SUMMARY_FILE"\n\
  echo "2. Scroll down to **Artifacts** section" >> "$SUMMARY_FILE"\n\
  echo "3. Download the **qalia-test-results** archive" >> "$SUMMARY_FILE"\n\
  echo "" >> "$SUMMARY_FILE"\n\
  echo "### Artifact Contents" >> "$SUMMARY_FILE"\n\
  echo "- **Test Files**: Ready-to-run test cases for your CI/CD pipeline" >> "$SUMMARY_FILE"\n\
  echo "- **Reports**: Detailed analysis and exploration session data" >> "$SUMMARY_FILE"\n\
  echo "- **Configuration**: QA AI configuration used for generation" >> "$SUMMARY_FILE"\n\
\n\
  # Output to GitHub Actions job summary if available\n\
  if [ ! -z "$GITHUB_STEP_SUMMARY" ]; then\n\
    cat "$SUMMARY_FILE" >> "$GITHUB_STEP_SUMMARY"\n\
    echo "📋 GitHub Actions summary updated"\n\
  fi\n\
  \n\
  # Add GitHub annotations for key metrics\n\
  if [ ! -z "$GITHUB_OUTPUT" ]; then\n\
    echo "tests_generated=$TEST_COUNT" >> "$GITHUB_OUTPUT"\n\
    echo "test_suites=$SUITE_COUNT" >> "$GITHUB_OUTPUT"\n\
    echo "analysis_duration=${DURATION}s" >> "$GITHUB_OUTPUT"\n\
    echo "report_path=$WORKSPACE_DIR/github-summary.md" >> "$GITHUB_OUTPUT"\n\
  fi\n\
  \n\
  # Add annotations visible in workflow\n\
  echo "::notice title=Tests Generated::Successfully generated $TEST_COUNT test cases across $SUITE_COUNT test suites"\n\
  echo "::notice title=Analysis Complete::QA AI analysis completed in ${DURATION}s"\n\
  \n\
  if [ $TEST_COUNT -eq 0 ]; then\n\
    echo "::warning title=No Tests Generated::QA AI was unable to generate any test cases. Check the target URL and configuration."\n\
  fi\n\
  \n\
  echo "✅ Generated $TEST_COUNT test files in $SUITE_COUNT suites"\n\
  echo "📁 Output saved to $OUTPUT_DIR/"\n\
  echo "📋 GitHub summary available in workflow details"\n\
else\n\
  echo "::error title=Generation Failed::No output directory was created"\n\
  echo "⚠️  No tests were generated"\n\
  exit 1\n\
fi\n\
\n\
echo "🎉 QA AI analysis completed successfully!"\n\
' > /entrypoint.sh

# Make entrypoint executable
RUN chmod +x /entrypoint.sh

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"] 