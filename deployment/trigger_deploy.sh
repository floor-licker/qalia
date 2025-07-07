#!/bin/bash

# Script to trigger deployment by creating a random trigger file
set -e

echo "🚀 Triggering deployment..."

# Change to demo-web-app directory
cd demo-web-app

# Remove trigger.txt if it exists
if [ -f "trigger.txt" ]; then
    echo "🗑️  Removing existing trigger.txt"
    rm trigger.txt
fi

# Generate 25 random 0s and 1s
echo "🎲 Generating random trigger content..."
trigger_content=""
for i in {1..25}; do
    random_bit=$((RANDOM % 2))
    trigger_content="${trigger_content}${random_bit}"
done

# Create trigger.txt with random content
echo "$trigger_content" > trigger.txt
echo "📝 Created trigger.txt with content: $trigger_content"

# Git operations
echo "📤 Committing and pushing to Git..."
git add trigger.txt
git commit -m "Trigger"
git push origin singular-page

echo "✅ Deployment trigger completed successfully!" 