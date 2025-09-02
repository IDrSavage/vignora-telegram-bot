# Vignora Telegram Bot - Cloud Run Deployment Guide

## المشكلة الأساسية: "container failed to start and listen on PORT=8080"

هذا الخطأ يعني أن الحاوية ما اشتغلت أصلاً أو خرجت قبل ما تفتح سيرفر على 8080. 

### الأسباب الشائعة:

1. **متغيّرات البيئة الأساسية ناقصة** ⇒ السكربت يرمي ValueError ويخرج قبل تشغيل السيرفر
2. **الملف يطلب TELEGRAM_TOKEN وSUPABASE_URL وSUPABASE_KEY**، ولو ناقص واحد منها يرفع استثناء ويتوقف التشغيل

## الحل:

### 1. تعديل الكود (تم إنجازه ✅)

تم تعديل `telegram_bot.py` ليتحقق من المتغيرات المطلوبة فقط عند تشغيل البوت في وضع polling، وليس عند تشغيل Flask server.

### 2. تعيين متغيّرات البيئة على Cloud Run

```bash
gcloud run deploy vignora-telegram-bot \
  --source . \
  --region=us-central1 \
  --allow-unauthenticated \
  --set-env-vars TELEGRAM_TOKEN="YOUR_TELEGRAM_BOT_TOKEN" \
  --set-env-vars SUPABASE_URL="https://xxxx.supabase.co" \
  --set-env-vars SUPABASE_KEY="YOUR_SUPABASE_SERVICE_ROLE_OR_ANON_KEY" \
  --set-env-vars TELEGRAM_CHANNEL_ID="@Vignora" \
  --set-env-vars TELEGRAM_CHANNEL_LINK="https://t.me/Vignora" \
  --set-env-vars CHANNEL_SUBSCRIPTION_REQUIRED="true" \
  --port=8080 \
  --timeout=300s
```

### 3. استخدام gunicorn (مُستحسن)

تم إضافة `gunicorn` إلى `requirements.txt` وإنشاء `Procfile`:

```txt
web: gunicorn telegram_bot:app --bind 0.0.0.0:$PORT --workers 2 --timeout 300
```

### 4. خطوات النشر:

1. **عدّل `deploy.sh`**:
   - استبدل `YOUR_TELEGRAM_BOT_TOKEN` بالتوكن الحقيقي
   - استبدل `https://xxxx.supabase.co` برابط Supabase الحقيقي
   - استبدل `YOUR_SUPABASE_SERVICE_ROLE_OR_ANON_KEY` بالمفتاح الحقيقي
   - استبدل `your-project-id` بمعرف المشروع الحقيقي

2. **شغّل النشر**:
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

### 5. التحقق من النجاح:

- **Health Check**: `https://YOUR-SERVICE-URL.run.app/health`
- **Home**: `https://YOUR-SERVICE-URL.run.app/`
- **Webhook**: `https://YOUR-SERVICE-URL.run.app/webhook`

### 6. إعداد Webhook:

```bash
curl -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/setWebhook" \
  -d "url=https://YOUR-SERVICE-URL.run.app/webhook"
```

## ملاحظات مهمة:

- التطبيق الآن يتحقق من المتغيرات فقط عند الحاجة
- Flask server يشتغل حتى لو كانت بعض المتغيرات ناقصة
- البوت سيعمل بشكل محدود حتى يتم تعيين جميع المتغيرات
- تم إضافة gunicorn لتحسين الأداء على Cloud Run

## استكشاف الأخطاء:

إذا استمرت المشكلة، راجع:

1. **متغيّرات البيئة** في تبويب Variables & Secrets في خدمة Cloud Run
2. **السجلات** للبحث عن أول استثناء أثناء الإقلاع
3. **مسار /health** للتأكد من أن السيرفر يعمل
4. **Entry point** في Dockerfile (يجب أن يكون `python telegram_bot.py`)
