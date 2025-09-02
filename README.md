# Vignora Medical Questions Bot

بوت أسئلة طبية متخصص في طب الأسنان، مبني باستخدام Python و Telegram Bot API.

## المميزات

- **أسئلة طبية متخصصة**: حالياً متوفر طب الأسنان، وسيتم إضافة باقي التخصصات قريباً
- **نظام اختبار تفاعلي**: أسئلة متعددة الخيارات مع شرح مبسط
- **تتبع الإحصائيات**: عرض إجمالي الأسئلة والإجابات الصحيحة والدقة
- **منع التكرار**: لا يتم عرض نفس السؤال مرتين للمستخدم
- **إدارة المستخدمين**: جمع بيانات المستخدمين وتتبع التفاعلات
- **ويبهوك مدمج**: أداء سريع بدون تأخير باستخدام الويبهوك المدمج في PTB

## المتطلبات

- Python 3.11+
- حساب Telegram Bot
- قاعدة بيانات Supabase

## التثبيت

1. **استنساخ المشروع**:
   ```bash
   git clone https://github.com/IDrSavage/vignora-telegram-bot.git
   cd vignora-telegram-bot
   ```

2. **إنشاء ملف البيئة**:
   ```bash
   # إنشاء ملف .env
   TELEGRAM_TOKEN=your_bot_token_here
   SUPABASE_URL=your_supabase_url_here
   SUPABASE_KEY=your_supabase_key_here
   TELEGRAM_CHANNEL_ID=@Vignora
   TELEGRAM_CHANNEL_LINK=https://t.me/Vignora
   CHANNEL_SUBSCRIPTION_REQUIRED=true
   ```

3. **تثبيت المكتبات**:
   ```bash
   pip install -r requirements.txt
   ```

## التشغيل المحلي

```bash
python telegram_bot.py
```

## النشر على Google Cloud Run

### 1. إعداد Cloud Build Trigger

في Google Cloud Console → Cloud Build → Triggers:

- **الاسم**: `vignora-bot-trigger`
- **Event**: Push to a branch
- **Source**: GitHub repository + branch (main)
- **Build configuration**: Cloud Build configuration file (yaml)
- **File location**: `cloudbuild.yaml`

### 2. إعداد المتغيرات (Substitutions)

في نفس صفحة إنشاء التريجر، تحت Variables:

```
_TELEGRAM_TOKEN = توكن البوت
_SUPABASE_URL = https://…supabase.co
_SUPABASE_KEY = مفتاح سوبابيس
_TELEGRAM_CHANNEL_ID = @Vignora
_TELEGRAM_CHANNEL_LINK = https://t.me/Vignora
_CHANNEL_SUBSCRIPTION_REQUIRED = true
_CLOUD_RUN_HOSTNAME = vignora-bot-826012995194.us-central1.run.app
```

### 3. النشر التلقائي

بعد إعداد التريجر، كل `git push` سيؤدي إلى نشر تلقائي.

## بنية قاعدة البيانات

### جدول الأسئلة (questions)
```sql
CREATE TABLE public.questions (
    id SERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT NOT NULL,
    option_d TEXT NOT NULL,
    correct_answer CHAR(1) NOT NULL,
    explanation TEXT NOT NULL,
    date_added BIGINT NOT NULL
);
```

### جدول المستخدمين (target_users)
```sql
CREATE TABLE public.target_users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    phone_number VARCHAR(20) NOT NULL,
    language_code VARCHAR(10),
    joined_at TIMESTAMP DEFAULT NOW(),
    last_interaction TIMESTAMP DEFAULT NOW()
);
```

### جدول إجابات المستخدمين (user_answers_bot)
```sql
CREATE TABLE public.user_answers_bot (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES target_users(telegram_id),
    question_id INTEGER REFERENCES questions(id),
    selected_answer CHAR(1) NOT NULL,
    correct_answer CHAR(1) NOT NULL,
    is_correct BOOLEAN NOT NULL,
    answered_at TIMESTAMP DEFAULT NOW()
);
```

## الملفات

- `telegram_bot.py` - الكود الرئيسي للبوت
- `requirements.txt` - مكتبات Python المطلوبة
- `Dockerfile` - ملف Docker للنشر
- `cloudbuild.yaml` - إعدادات Cloud Build
- `.env` - متغيرات البيئة (يجب إنشاؤه محلياً)

## التطوير

### إضافة أسئلة جديدة

1. إضافة السؤال في قاعدة البيانات
2. التأكد من صحة التنسيق
3. اختبار البوت محلياً

### تعديل الواجهة

- تعديل الرسائل في الدوال المناسبة
- إضافة أزرار جديدة في `InlineKeyboardMarkup`
- تعديل التصميم باستخدام Markdown

## الدعم

للمساعدة أو الإبلاغ عن مشاكل، يرجى فتح issue في GitHub.

## الترخيص

هذا المشروع مملوك لشركة Vignora.
