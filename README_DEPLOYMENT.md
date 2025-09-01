# 🚀 Vignora Telegram Bot - Google Cloud Run Deployment Guide

## 📋 Prerequisites / المتطلبات المسبقة

### 1. Google Cloud Account
- Create a Google Cloud account: https://cloud.google.com/
- Create a new project or use existing one

### 2. Install Google Cloud CLI
```bash
# Windows (PowerShell)
# Download from: https://cloud.google.com/sdk/docs/install

# macOS
brew install google-cloud-sdk

# Linux
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

### 3. Enable Billing
- Enable billing for your Google Cloud project
- Cloud Run requires billing to be enabled

## 🔧 Setup Steps / خطوات الإعداد

### Step 1: Authenticate with Google Cloud
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### Step 2: Enable Required APIs
```bash
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### Step 3: Set Environment Variables
Create a `.env` file with your credentials:
```env
TELEGRAM_TOKEN=your_telegram_bot_token
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
TELEGRAM_CHANNEL_ID=@Vignora
TELEGRAM_CHANNEL_LINK=https://t.me/Vignora
CHANNEL_SUBSCRIPTION_REQUIRED=true
```

## 🚀 Deployment Methods / طرق النشر

### Method 1: Using deploy.sh Script (Recommended)
```bash
# Make script executable
chmod +x deploy.sh

# Set environment variables
export TELEGRAM_TOKEN="your_token"
export SUPABASE_URL="your_url"
export SUPABASE_KEY="your_key"
export TELEGRAM_CHANNEL_ID="@Vignora"
export TELEGRAM_CHANNEL_LINK="https://t.me/Vignora"
export CHANNEL_SUBSCRIPTION_REQUIRED="true"

# Run deployment
./deploy.sh
```

### Method 2: Manual Deployment
```bash
# Build and deploy
gcloud run deploy vignora-bot \
    --source . \
    --region us-central1 \
    --platform managed \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --max-instances 10 \
    --timeout 300 \
    --set-env-vars TELEGRAM_TOKEN="your_token",SUPABASE_URL="your_url",SUPABASE_KEY="your_key",TELEGRAM_CHANNEL_ID="@Vignora",TELEGRAM_CHANNEL_LINK="https://t.me/Vignora",CHANNEL_SUBSCRIPTION_REQUIRED="true"
```

### Method 3: Using Cloud Build
```bash
# Update cloudbuild.yaml with your values
# Then run:
gcloud builds submit --config cloudbuild.yaml .
```

## 🔗 Post-Deployment Setup / الإعداد بعد النشر

### 1. Get Service URL
```bash
gcloud run services describe vignora-bot --region=us-central1 --format="value(status.url)"
```

### 2. Set Telegram Webhook
Replace `YOUR_SERVICE_URL` with the actual URL:
```bash
curl -X POST "https://api.telegram.org/botYOUR_TOKEN/setWebhook" \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"YOUR_SERVICE_URL/webhook\"}"
```

### 3. Test Health Check
```bash
curl https://YOUR_SERVICE_URL/health
```

## 📊 Monitoring / المراقبة

### View Logs
```bash
gcloud run services logs read vignora-bot --region=us-central1
```

### Monitor Performance
- Go to Google Cloud Console
- Navigate to Cloud Run
- Select your service
- View metrics and logs

## 🔧 Configuration Options / خيارات التكوين

### Memory and CPU
- Default: 512Mi RAM, 1 CPU
- Adjust based on usage:
  ```bash
  --memory 1Gi --cpu 2
  ```

### Scaling
- Default: 0-10 instances
- Adjust max instances:
  ```bash
  --max-instances 20
  ```

### Timeout
- Default: 300 seconds
- Adjust if needed:
  ```bash
  --timeout 600
  ```

## 🛠️ Troubleshooting / استكشاف الأخطاء

### Common Issues

#### 1. Build Failures
```bash
# Check build logs
gcloud builds log BUILD_ID
```

#### 2. Runtime Errors
```bash
# Check service logs
gcloud run services logs read vignora-bot --region=us-central1
```

#### 3. Webhook Issues
```bash
# Test webhook manually
curl -X POST "https://api.telegram.org/botYOUR_TOKEN/getWebhookInfo"
```

#### 4. Environment Variables
```bash
# Verify environment variables
gcloud run services describe vignora-bot --region=us-central1 --format="value(spec.template.spec.containers[0].env[].name,spec.template.spec.containers[0].env[].value)"
```

## 💰 Cost Optimization / تحسين التكلفة

### Free Tier
- Cloud Run offers generous free tier
- 2 million requests per month
- 360,000 vCPU-seconds
- 180,000 GiB-seconds

### Cost Monitoring
```bash
# View cost breakdown
gcloud billing accounts list
```

## 🔒 Security / الأمان

### Best Practices
1. Use environment variables for secrets
2. Enable Cloud Audit Logs
3. Use IAM roles with minimal permissions
4. Enable VPC connector if needed

### IAM Setup
```bash
# Grant Cloud Run Admin role
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="user:YOUR_EMAIL" \
    --role="roles/run.admin"
```

## 📱 Testing / الاختبار

### Local Testing
```bash
# Test locally before deployment
python telegram_bot.py
```

### Production Testing
1. Send `/start` to your bot
2. Test question flow
3. Test channel subscription
4. Test reporting system

## 🔄 Updates / التحديثات

### Deploy Updates
```bash
# Simply run deploy script again
./deploy.sh
```

### Rollback
```bash
# List revisions
gcloud run revisions list --service=vignora-bot --region=us-central1

# Rollback to specific revision
gcloud run services update-traffic vignora-bot \
    --to-revisions=REVISION_NAME=100 \
    --region=us-central1
```

## 📞 Support / الدعم

### Useful Commands
```bash
# Service info
gcloud run services describe vignora-bot --region=us-central1

# List all services
gcloud run services list --region=us-central1

# Delete service
gcloud run services delete vignora-bot --region=us-central1
```

### Documentation
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Supabase Documentation](https://supabase.com/docs)

---

## 🎉 Congratulations!
Your Vignora Medical Questions Bot is now running on Google Cloud Run!

**Service Features:**
- ✅ Auto-scaling
- ✅ High availability
- ✅ SSL encryption
- ✅ Global CDN
- ✅ Pay-per-use pricing
- ✅ Zero maintenance

**Next Steps:**
1. Test the bot thoroughly
2. Monitor performance
3. Set up alerts
4. Configure custom domain (optional)
