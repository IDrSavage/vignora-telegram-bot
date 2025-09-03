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
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "telegram_bot:app"]