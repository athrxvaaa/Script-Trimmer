#!/bin/bash

# Script to update Modal secrets with OpenAI API key
echo "🔧 Updating Modal secrets with OpenAI API key..."

# Check if OPENAI_API_KEY is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OPENAI_API_KEY environment variable is not set"
    echo "Please set your OpenAI API key:"
    echo "export OPENAI_API_KEY='your-openai-api-key-here'"
    exit 1
fi

# Update Modal secrets with OpenAI API key
echo "📝 Updating Modal secrets..."
modal secret create script-trimmer-secrets \
  --data "{
    \"S3_ACCESS_KEY\": \"$S3_ACCESS_KEY\",
    \"S3_SECRET_KEY\": \"$S3_SECRET_KEY\",
    \"S3_BUCKET_NAME\": \"$S3_BUCKET_NAME\",
    \"S3_REGION\": \"$S3_REGION\",
    \"OPENAI_API_KEY\": \"$OPENAI_API_KEY\"
  }"

echo "✅ Modal secrets updated successfully!"
echo "🔑 OpenAI API key has been added to the secrets"
echo "🚀 You can now deploy your app with: modal deploy modal_app.py" 