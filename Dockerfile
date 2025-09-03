# استخدم نسخة بايثون رسمية كنقطة بداية
FROM python:3.11-slim

# تعيين مجلد العمل داخل الحاوية
WORKDIR /app

# انسخ ملف المكتبات أولاً للاستفادة من التخزين المؤقت (caching)
COPY requirements.txt .

# تثبيت المكتبات المطلوبة
RUN pip install --no-cache-dir -r requirements.txt

# انسخ باقي ملفات المشروع إلى الحاوية
COPY . .

# اجعل المنفذ 8080 متاحاً للعالم الخارجي
EXPOSE 8080

# الأمر الذي سيتم تشغيله عند بدء تشغيل الحاوية
# نستخدم gunicorn لأنه الخيار الأفضل للبيئات الإنتاجية مثل Cloud Run
# --workers 1: Cloud Run is single-threaded per instance, so 1 worker is optimal.
# --threads 8: Use threads within the worker to handle concurrent I/O efficiently.
# --timeout 120: Increase timeout to 120 seconds to handle potentially slow API responses.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "120", "telegram_bot:app"]