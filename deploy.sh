#!/bin/bash

# Vignora Telegram Bot - Google Cloud Run Deployment Script
# سكريبت نشر بوت فيجنورا على Google Cloud Run

set -e

echo "🚀 Starting Vignora Bot deployment to Google Cloud Run..."

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "📥 Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "🔐 Please authenticate with Google Cloud:"
    gcloud auth login
fi

# Set project ID (replace with your project ID)
PROJECT_ID="your-project-id"
echo "📋 Using project: $PROJECT_ID"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Build and deploy
echo "🏗️ Building and deploying..."
gcloud run deploy vignora-bot \
    --source . \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --max-instances 10 \
    --timeout 300 \
    --set-env-vars TELEGRAM_TOKEN="$TELEGRAM_TOKEN",SUPABASE_URL="$SUPABASE_URL",SUPABASE_KEY="$SUPABASE_KEY",TELEGRAM_CHANNEL_ID="$TELEGRAM_CHANNEL_ID",TELEGRAM_CHANNEL_LINK="$TELEGRAM_CHANNEL_LINK",CHANNEL_SUBSCRIPTION_REQUIRED="$CHANNEL_SUBSCRIPTION_REQUIRED"

# Get the service URL
SERVICE_URL=$(gcloud run services describe vignora-bot --region=us-central1 --format="value(status.url)")

echo "✅ Deployment completed successfully!"
echo "🌐 Service URL: $SERVICE_URL"
echo "📊 Health check: $SERVICE_URL/health"
echo "🤖 Bot webhook: $SERVICE_URL/webhook"

# Set webhook for Telegram bot
echo "🔗 Setting Telegram webhook..."
curl -X POST "https://api.telegram.org/bot$TELEGRAM_TOKEN/setWebhook" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"$SERVICE_URL/webhook\"}"

echo "🎉 Bot is now live on Google Cloud Run!"
echo "📱 Users can start the bot with /start"
