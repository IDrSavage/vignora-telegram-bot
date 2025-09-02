import os
import asyncio
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
from supabase import create_client, Client
from dotenv import load_dotenv
import logging
from flask import Flask, request, jsonify
import threading

# إعداد logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# تحميل متغيرات البيئة
load_dotenv()

# تعيين المتغيرات الثابتة - مطلوبة من ملف .env
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "@Vignora")
TELEGRAM_CHANNEL_LINK = os.getenv("TELEGRAM_CHANNEL_LINK", "https://t.me/Vignora")
CHANNEL_SUBSCRIPTION_REQUIRED = os.getenv("CHANNEL_SUBSCRIPTION_REQUIRED", "true").lower() == "true"

# التحقق من وجود المتغيرات المطلوبة
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is required in .env file")
if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL is required in .env file")
if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY is required in .env file")

# إنشاء عميل Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase client created successfully")
except Exception as e:
    print(f"⚠️ Warning: Could not create Supabase client: {e}")
    print("⚠️ Bot will run with limited functionality")
    supabase = None

# متغير للتحكم في إظهار التاريخ (يمكن تغييره لاحقاً)
SHOW_DATE_ADDED = False

# متغير عام للتطبيق (مطلوب للويبهوك)
application = None

def format_timestamp(timestamp):
    """تحويل Unix timestamp إلى تاريخ مفهوم"""
    try:
        if timestamp:
            # تحويل Unix timestamp إلى datetime
            dt = datetime.fromtimestamp(int(timestamp))
            # تنسيق التاريخ باللغة العربية والإنجليزية
            return dt.strftime("%Y-%m-%d %H:%M")
        return "Unknown"
    except (ValueError, TypeError, OSError):
        return "Unknown"

def check_user_exists(telegram_id: int):
    """التحقق من وجود المستخدم في قاعدة البيانات"""
    try:
        response = supabase.table('target_users').select('telegram_id').eq('telegram_id', telegram_id).execute()
        return len(response.data) > 0
    except Exception as e:
        print(f"⚠️ Warning: Could not check user existence: {e}")
        # في حالة فشل الاتصال، نفترض أن المستخدم جديد
        return False

def save_user_data(telegram_id: int, username: str, first_name: str, last_name: str, phone_number: str, language_code: str):
    """حفظ بيانات المستخدم في قاعدة البيانات"""
    try:
        user_data = {
            'telegram_id': telegram_id,
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'phone_number': phone_number,
            'language_code': language_code,
            'joined_at': 'now()',
            'last_interaction': 'now()'
        }
        
        response = supabase.table('target_users').insert(user_data).execute()
        print(f"✅ User saved successfully: {telegram_id}")
        return True
    except Exception as e:
        print(f"⚠️ Warning: Could not save user data: {e}")
        # في حالة فشل الحفظ، نسمح للمستخدم بالمتابعة
        return True

def update_last_interaction(telegram_id: int):
    """تحديث آخر تفاعل للمستخدم"""
    if not supabase:
        return
    
    try:
        supabase.table('target_users').update({'last_interaction': 'now()'}).eq('telegram_id', telegram_id).execute()
    except Exception as e:
        print(f"⚠️ Warning: Could not update last interaction: {e}")
        # لا نوقف البوت بسبب فشل تحديث آخر تفاعل

def save_user_answer(telegram_id: int, question_id: int, selected_answer: str, correct_answer: str, is_correct: bool):
    """حفظ إجابة المستخدم في قاعدة البيانات"""
    try:
        answer_data = {
            'user_id': telegram_id,
            'question_id': question_id,
            'selected_answer': selected_answer,
            'correct_answer': correct_answer,
            'is_correct': is_correct,
            'answered_at': 'now()'
        }
        
        response = supabase.table('user_answers_bot').insert(answer_data).execute()
        print(f"✅ User answer saved: User {telegram_id}, Question {question_id}, Correct: {is_correct}")
        return True
    except Exception as e:
        print(f"⚠️ Warning: Could not save user answer: {e}")
        return False

def get_user_stats(telegram_id: int):
    """جلب إحصائيات المستخدم"""
    try:
        response = supabase.table('user_answers_bot').select('is_correct', count='exact').eq('user_id', telegram_id).execute()
        if response.data:
            total_answers = len(response.data)
            correct_answers = sum(1 for answer in response.data if answer['is_correct'])
            accuracy = (correct_answers / total_answers) * 100 if total_answers > 0 else 0
            print(f"✅ User {telegram_id} stats: {total_answers} total, {correct_answers} correct, {accuracy}% accuracy")
            return {
                'total_answers': total_answers,
                'correct_answers': correct_answers,
                'accuracy': round(accuracy, 1)
            }
        print(f"✅ User {telegram_id} has no stats yet")
        return {'total_answers': 0, 'correct_answers': 0, 'accuracy': 0}
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch user stats: {e}")
        return {'total_answers': 0, 'correct_answers': 0, 'accuracy': 0}

def get_user_answered_questions(telegram_id: int):
    """جلب الأسئلة التي أجاب عليها المستخدم"""
    try:
        # محاولة استخدام count للحصول على جميع الأسئلة
        response = supabase.table('user_answers_bot').select('question_id', count='exact').eq('user_id', telegram_id).execute()
        if response.data:
            count = len(response.data)
            print(f"✅ User {telegram_id} answered {count} questions")
            return [answer['question_id'] for answer in response.data]
        print(f"✅ User {telegram_id} answered 0 questions")
        return []
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch user answers: {e}")
        return []

def get_total_questions_count():
    """جلب عدد الأسئلة الكلي في قاعدة البيانات"""
    try:
        # محاولة استخدام count
        response = supabase.table('questions').select('*', count='exact').execute()
        if hasattr(response, 'count') and response.count is not None:
            print(f"✅ Got exact count: {response.count}")
            return response.count
        
        # إذا فشل count، نجرب طريقة أخرى
        print("⚠️ Count method failed, trying alternative...")
        response = supabase.table('questions').select('id').execute()
        count = len(response.data)
        print(f"✅ Got count from data length: {count}")
        return count
        
    except Exception as e:
        print(f"⚠️ Warning: Could not get total questions count: {e}")
        return 0

def fetch_random_question(telegram_id: int = None):
    """جلب أحدث سؤال من قاعدة البيانات (غير مجاب عليه من قبل المستخدم)"""
    try:
        # إذا كان هناك معرف مستخدم، نستثني الأسئلة المجاب عليها
        if telegram_id:
            answered_questions = get_user_answered_questions(telegram_id)
            print(f"📊 User {telegram_id} has answered {len(answered_questions)} questions")
            
            # استعلام لجلب أحدث سؤال غير مجاب عليه
            if answered_questions:
                # استخدام not in مع limit للحصول على سؤال عشوائي
                response = supabase.table('questions').select(
                    'id, question, option_a, option_b, option_c, option_d, correct_answer, explanation, date_added'
                ).not_.in_('id', answered_questions).order('date_added', desc=True).limit(1).execute()
            else:
                # المستخدم لم يجب على أي سؤال بعد - جلب أحدث سؤال
                response = supabase.table('questions').select(
                    'id, question, option_a, option_b, option_c, option_d, correct_answer, explanation, date_added'
                ).order('date_added', desc=True).limit(1).execute()
        else:
            # بدون معرف مستخدم - جلب أحدث سؤال
            response = supabase.table('questions').select(
                'id, question, option_a, option_b, option_c, option_d, correct_answer, explanation, date_added'
            ).order('date_added', desc=True).limit(1).execute()
        
        if response.data and len(response.data) > 0:
            question = response.data[0]
            print(f"📅 Question {question.get('id')} from date: {question.get('date_added')}")
            return question
        else:
            if telegram_id and answered_questions:
                print(f"⚠️ User {telegram_id} has answered all available questions")
            else:
                print("⚠️ Warning: No questions found in database")
            return None
            
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch question: {e}")
        return None

def get_latest_questions(limit: int = 10):
    """جلب أحدث الأسئلة من قاعدة البيانات"""
    try:
        response = supabase.table('questions').select(
            'id, question, option_a, option_b, option_c, option_d, correct_answer, explanation, date_added'
        ).order('date_added', desc=True).limit(limit).execute()
        
        if response.data:
            print(f"📅 Fetched {len(response.data)} latest questions")
            return response.data
        else:
            print("⚠️ No questions found")
            return []
            
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch latest questions: {e}")
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بداية التفاعل مع البوت"""
    user = update.effective_user
    telegram_id = user.id
    
    # التحقق من وجود المستخدم
    user_exists = check_user_exists(telegram_id)
    if not user_exists:
        # المستخدم جديد - طلب رقم الجوال
        context.user_data["new_user"] = True
        
        # إنشاء لوحة مفاتيح لطلب رقم الجوال
        keyboard = [[KeyboardButton("Share Phone Number / مشاركة رقم الجوال", request_contact=True)]]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        
        welcome_message = (
            "Welcome to Vignora Medical Questions Bot!\n"
            "مرحباً بك في بوت فيجنورا للأسئلة الطبية!\n\n"
            "🦷 **Available Now:** Dentistry Questions\n"
            "🦷 **متوفر الآن:** أسئلة طب الأسنان\n\n"
            "🌟 More medical specialties coming soon!\n"
            "🌟 المزيد من التخصصات الطبية قريباً!\n\n"
            "To get started, please share your phone number.\n"
            "للبدء، يرجى مشاركة رقم جوالك."
        )
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)
    else:
        # المستخدم موجود - عرض قائمة الاختبار
        await show_quiz_menu(update, context)

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة مشاركة رقم الجوال"""
    if not update.message.contact:
        await update.message.reply_text("Please share your phone number to continue.")
        return
    
    user = update.effective_user
    contact = update.message.contact
    
    # حفظ بيانات المستخدم
    success = save_user_data(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        phone_number=contact.phone_number,
        language_code=user.language_code
    )
    
    if success:
        # إزالة لوحة المفاتيح
        await update.message.reply_text(
            "تم حفظ معلوماتك بنجاح.\n"
            "Your information has been saved successfully.",
            reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
        )
        
        # عرض مقدمة البوت مباشرة
        await show_bot_introduction(update, context)
    else:
        await update.message.reply_text("Sorry, there was an error saving your information. Please try again.")

async def show_bot_introduction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض مقدمة البوت للمستخدمين الجدد"""
    user = update.effective_user
    telegram_id = user.id
    
    # تحديث آخر تفاعل
    update_last_interaction(telegram_id)
    
    # جلب عدد الأسئلة المتاحة
    total_questions = get_total_questions_count()
    
    intro_message = (
        "🎯 **مرحباً بك في بوت فيجنورا للأسئلة الطبية!**\n"
        "**Welcome to Vignora Medical Questions Bot!**\n\n"
        
        "📚 **ما هو بوت فيجنورا؟**\n"
        "**What is Vignora Bot?**\n"
        "بوت تفاعلي متطور يساعدك على اختبار معرفتك الطبية من خلال أسئلة متعددة الخيارات.\n"
        "An advanced interactive bot that helps you test your medical knowledge through multiple choice questions.\n\n"
        
        "🦷 **متوفر الآن:**\n"
        "**Available Now:**\n"
        "• أسئلة طب الأسنان\n"
        "• Dentistry Questions\n\n"
        
        f"📊 **Questions Available:** {total_questions}\n\n"
        
        "🚀 **كيف يعمل؟**\n"
        "**How does it work?**\n"
        "• ستحصل على أسئلة طبية عشوائية\n"
        "• اختر الإجابة الصحيحة من 4 خيارات\n"
        "• احصل على شرح فوري لكل سؤال\n"
        "• تتبع تقدمك وإحصائياتك\n\n"
        
        "• You'll get random medical questions\n"
        "• Choose the correct answer from 4 options\n"
        "• Get instant explanations for each question\n"
        "• Track your progress and statistics\n\n"
        
        "💡 **مميزات بوت فيجنورا:**\n"
        "**Vignora Bot Features:**\n"
        "✅ أسئلة متنوعة ومحدثة\n"
        "✅ شرح مفصل لكل إجابة\n"
        "✅ إحصائيات شخصية\n"
        "✅ لا تكرار للأسئلة\n"
        "✅ واجهة ثنائية اللغة\n\n"
        
        "✅ Diverse and updated questions\n"
        "✅ Detailed explanations\n"
        "✅ Personal statistics\n"
        "✅ No question repetition\n"
        "✅ Bilingual interface\n\n"
        
        "🌟 **خطة التطوير:**\n"
        "**Development Plan:**\n"
        "سيتم إضافة باقي التخصصات الطبية قريباً لتغطية جميع احتياجاتكم التعليمية.\n"
        "Other medical specialties will be added soon to cover all your educational needs.\n\n"
        
        "🎉 **هل أنت مستعد للبدء مع فيجنورا؟**\n"
        "**Are you ready to start with Vignora?**"
    )
    
    keyboard = [
        [InlineKeyboardButton("🚀 Start Quiz / بدء الاختبار", callback_data="quiz")],
        [InlineKeyboardButton("📊 My Stats / إحصائياتي", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ About / حول البوت", callback_data="about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(intro_message, reply_markup=reply_markup, parse_mode='Markdown')

async def show_quiz_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة الاختبار"""
    user = update.effective_user
    telegram_id = user.id
    
    # تحديث آخر تفاعل
    update_last_interaction(telegram_id)
    
    # التحقق من الاشتراك في القناة
    if CHANNEL_SUBSCRIPTION_REQUIRED:
        is_subscribed = await check_channel_subscription(telegram_id, context.bot)
        if not is_subscribed:
            await show_subscription_required(update, context, is_new_user=False)
            return
    
    # جلب عدد الأسئلة المتاحة
    total_questions = get_total_questions_count()
    
    keyboard = [
        [InlineKeyboardButton("Start Quiz / بدء الاختبار", callback_data="quiz")],
        [InlineKeyboardButton("My Stats / إحصائياتي", callback_data="stats")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = (
        "🎯 **مرحباً بك مرة أخرى في بوت فيجنورا للأسئلة الطبية!**\n"
        "**Welcome back to Vignora Medical Questions Bot!**\n\n"
        "🦷 **متوفر الآن:** أسئلة طب الأسنان\n"
        "🦷 **Available Now:** Dentistry Questions\n\n"
        f"📊 **Questions Available:** {total_questions}\n\n"
        "🌟 **خطة التطوير:** سيتم إضافة باقي التخصصات الطبية قريباً\n"
        "**Development Plan:** Other medical specialties will be added soon\n\n"
        "🚀 **اختر ما تريد القيام به:**\n"
        "**Choose what you want to do:**"
    )
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات المستخدم"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    update_last_interaction(user.id)
    
    # التحقق من الاشتراك في القناة
    if CHANNEL_SUBSCRIPTION_REQUIRED:
        is_subscribed = await check_channel_subscription(user.id, context.bot)
        if not is_subscribed:
            await show_subscription_required(update, context, is_new_user=False)
            return
    
    stats = get_user_stats(user.id)
    
    # جلب عدد الأسئلة الكلي والمتبقية
    total_questions = get_total_questions_count()
    answered_questions = get_user_answered_questions(user.id)
    remaining_questions = total_questions - len(answered_questions)
    
    stats_message = (
        f"📊 **Your Statistics / إحصائياتك**\n\n"
        f"**Answered:** {stats['total_answers']}\n"
        f"**Correct:** {stats['correct_answers']}\n"
        f"**Accuracy:** {stats['accuracy']}%\n\n"
        f"📚 **Progress:** {stats['total_answers']} / {total_questions}\n"
        f"📚 **Remaining:** {remaining_questions} / {total_questions}\n\n"
        f"Keep going! 🚀\n"
        f"استمر! 🚀"
    )
    
        # أزرار العودة
    keyboard = [[InlineKeyboardButton("Back to Menu / العودة للقائمة", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(stats_message, reply_markup=reply_markup, parse_mode='Markdown')

async def end_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنهاء جلسة الاختبار والعودة للقائمة الرئيسية"""
    query = update.callback_query
    await query.answer()
    
    # مسح بيانات السؤال الحالي
    if "current_question" in context.user_data:
        del context.user_data["current_question"]
    
    # عرض رسالة إنهاء الجلسة
    end_message = (
        "🔚 **تم إنهاء الجلسة**\n"
        "**Session Ended**\n\n"
        "شكراً لك على المشاركة في الاختبار!\n"
        "Thank you for participating in the quiz!\n\n"
        "يمكنك العودة للقائمة الرئيسية أو بدء جلسة جديدة.\n"
        "You can return to the main menu or start a new session."
    )
    
    keyboard = [
        [InlineKeyboardButton("🚀 Start New Quiz / بدء اختبار جديد", callback_data="quiz")],
        [InlineKeyboardButton("📊 My Stats / إحصائياتي", callback_data="stats")],
        [InlineKeyboardButton("🏠 Main Menu / القائمة الرئيسية", callback_data="menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(end_message, reply_markup=reply_markup, parse_mode='Markdown')

async def show_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معلومات حول البوت"""
    query = update.callback_query
    await query.answer()
    
    about_message = (
        "ℹ️ **حول بوت فيجنورا / About Vignora Bot**\n\n"
        
        "🏥 **الغرض:**\n"
        "**Purpose:**\n"
        "بوت تعليمي متطور يهدف إلى مساعدة الطلاب والمهنيين الطبيين على اختبار معرفتهم الطبية.\n"
        "An advanced educational bot designed to help medical students and professionals test their medical knowledge.\n\n"
        
        "🎓 **الفئة المستهدفة:**\n"
        "**Target Audience:**\n"
        "• طلاب طب الأسنان\n"
        "• المهنيون الطبيون\n"
        "• أي شخص مهتم بالمعرفة الطبية\n\n"
        
        "• Dental students\n"
        "• Medical professionals\n"
        "• Anyone interested in medical knowledge\n\n"
        
        "🦷 **المحتوى المتوفر الآن:**\n"
        "**Currently Available:**\n"
        "أسئلة طب الأسنان متنوعة تغطي مختلف المستويات.\n"
        "Diverse dentistry questions covering various levels.\n\n"
        
        "🚀 **خطة التطوير:**\n"
        "**Development Plan:**\n"
        "سيتم إضافة باقي التخصصات الطبية قريباً لتغطية جميع احتياجاتك التعليمية.\n"
        "Other medical specialties will be added soon to cover all your educational needs.\n\n"
        
        "📱 **كيفية الاستخدام:**\n"
        "**How to Use:**\n"
        "1. اضغط على 'بدء الاختبار'\n"
        "2. اقرأ السؤال بعناية\n"
        "3. اختر الإجابة الصحيحة\n"
        "4. اقرأ الشرح\n"
        "5. انتقل للسؤال التالي\n\n"
        
        "1. Click 'Start Quiz'\n"
        "2. Read the question carefully\n"
        "3. Choose the correct answer\n"
        "4. Read the explanation\n"
        "5. Move to next question\n\n"
        
        "🌟 **مميزات بوت فيجنورا:**\n"
        "**Vignora Bot Features:**\n"
        "• لا تكرار للأسئلة\n"
        "• إحصائيات شخصية\n"
        "• تتبع التقدم\n"
        "• واجهة ثنائية اللغة\n"
        "• تطوير مستمر ومحتوى محدث\n\n"
        
        "• No question repetition\n"
        "• Personal statistics\n"
        "• Progress tracking\n"
        "• Bilingual interface\n"
        "• Continuous development and updated content"
    )
    
    # أزرار العودة
    keyboard = [[InlineKeyboardButton("Back to Menu / العودة للقائمة", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(about_message, reply_markup=reply_markup, parse_mode='Markdown')

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال سؤال للمستخدم"""
    query = update.callback_query
    await query.answer()
    
    # تحديث آخر تفاعل
    user = query.from_user
    update_last_interaction(user.id)
    
    # التحقق من الاشتراك في القناة
    if CHANNEL_SUBSCRIPTION_REQUIRED:
        is_subscribed = await check_channel_subscription(user.id, context.bot)
        if not is_subscribed:
            await show_subscription_required(update, context, is_new_user=False)
            return
    
    # جلب عدد الأسئلة المتاحة
    total_questions = get_total_questions_count()
    answered_questions = get_user_answered_questions(user.id)
    remaining_questions = total_questions - len(answered_questions)
    
    # التحقق من حد 10 أسئلة للمستخدمين الجدد
    if len(answered_questions) >= 10:
        # التحقق من الاشتراك مرة أخرى
        is_subscribed = await check_channel_subscription(user.id, context.bot)
        if not is_subscribed:
            await show_subscription_required(update, context, is_new_user=True)
            return
    
    question_data = fetch_random_question(user.id)
    if not question_data:
        # التحقق من سبب عدم وجود أسئلة
        if answered_questions and len(answered_questions) > 0:
            await query.edit_message_text(
                "🎉 مبروك! لقد أجبت على جميع الأسئلة المتاحة!\n"
                "Congratulations! You've answered all available questions!\n\n"
                "سيتم إضافة المزيد من الأسئلة قريباً.\n"
                "More questions will be added soon."
            )
        else:
            await query.edit_message_text(
                "عذراً، لا يمكن جلب الأسئلة حالياً.\n"
                "Sorry, questions are not available at the moment.\n\n"
                "يرجى المحاولة لاحقاً.\n"
                "Please try again later."
            )
        return
    
    # تنسيق السؤال مع عدد الأسئلة المتبقية
    question_text = (
        f"📚 **Question / السؤال:**\n"
        f"{question_data.get('question', 'No question')}\n\n"
        f"📊 **Remaining:** {remaining_questions} / {total_questions}\n\n"
        f"{'📅 **Added:** ' + format_timestamp(question_data.get('date_added')) + '\\n\\n' if SHOW_DATE_ADDED else ''}"
        "**Options / الخيارات:**"
    )
    
    # إنشاء أزرار الخيارات - بدون ترجمة
    keyboard = [
        [InlineKeyboardButton(f"A: {question_data.get('option_a', '')}", callback_data="answer_A")],
        [InlineKeyboardButton(f"B: {question_data.get('option_b', '')}", callback_data="answer_B")],
        [InlineKeyboardButton(f"C: {question_data.get('option_c', '')}", callback_data="answer_C")],
        [InlineKeyboardButton(f"D: {question_data.get('option_d', '')}", callback_data="answer_D")],
        [InlineKeyboardButton("🔚 End Session / إنهاء الجلسة", callback_data="end_session")]
    ]
    
    # حفظ بيانات السؤال في سياق المستخدم
    context.user_data["current_question"] = {
        "question_id": question_data.get('id', ''),
        "correct_answer": question_data.get('correct_answer', ''),
        "explanation": question_data.get('explanation', '')
    }
    
    # حفظ بيانات السؤال الكاملة لعرض الإجابة الصحيحة
    context.user_data["current_question_data"] = {
        "option_a": question_data.get('option_a', ''),
        "option_b": question_data.get('option_b', ''),
        "option_c": question_data.get('option_c', ''),
        "option_d": question_data.get('option_d', '')
    }
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(question_text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة إجابة المستخدم"""
    query = update.callback_query
    await query.answer()
    
    # تحديث آخر تفاعل
    user = query.from_user
    update_last_interaction(user.id)
    
    # التحقق من وجود بيانات السؤال
    if "current_question" not in context.user_data:
        await query.edit_message_text("عذراً، حدث خطأ. يرجى البدء من جديد.")
        return
    
    selected_answer = query.data.split("_")[1]
    correct_answer = context.user_data["current_question"]["correct_answer"]
    explanation = context.user_data["current_question"]["explanation"]
    question_id = context.user_data["current_question"]["question_id"]
    
    # حفظ الإجابة المختارة للعودة إليها
    context.user_data["last_selected_answer"] = selected_answer
    
    # تحديد ما إذا كانت الإجابة صحيحة
    is_correct = selected_answer == correct_answer
    
    # حفظ إجابة المستخدم
    save_user_answer(user.id, question_id, selected_answer, correct_answer, is_correct)
    
    # إنشاء رسالة النتيجة
    if is_correct:
        result_message = "✅ إجابة صحيحة!\nCorrect answer!\n\n"
    else:
        # عرض الإجابة الصحيحة كاملة
        correct_answer_text = ""
        question_data = context.user_data.get("current_question_data", {})
        if question_data:
            if correct_answer == "A":
                correct_answer_text = f"A: {question_data.get('option_a', '')}"
            elif correct_answer == "B":
                correct_answer_text = f"B: {question_data.get('option_b', '')}"
            elif correct_answer == "C":
                correct_answer_text = f"C: {question_data.get('option_c', '')}"
            elif correct_answer == "D":
                correct_answer_text = f"D: {question_data.get('option_d', '')}"
        
        result_message = (
            f"❌ إجابة خاطئة\n"
            f"Wrong answer\n\n"
            f"**Correct Answer / الإجابة الصحيحة:**\n"
            f"{correct_answer_text}\n\n"
        )
    
    # إضافة الشرح المبسط فقط
    if explanation:
        result_message += f"**Explanation / الشرح:**\n{explanation}"
    else:
        result_message += "**No explanation available / لا يوجد شرح متاح**"
    
    # أزرار التحكم - زر التالي وزر إنهاء الجلسة وزر الإبلاغ
    keyboard = [
        [InlineKeyboardButton("Next Question / السؤال التالي", callback_data="quiz")],
        [InlineKeyboardButton("🚨 Report Question / الإبلاغ عن السؤال", callback_data="report")],
        [InlineKeyboardButton("🔚 End Session / إنهاء الجلسة", callback_data="end_session")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(result_message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الإبلاغ عن السؤال"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    update_last_interaction(user.id)
    
    # التحقق من وجود بيانات السؤال
    if "current_question" not in context.user_data:
        await query.edit_message_text("عذراً، حدث خطأ. يرجى البدء من جديد.")
        return
    
    question_id = context.user_data["current_question"]["question_id"]
    
    # عرض خيارات الإبلاغ
    report_keyboard = [
        [InlineKeyboardButton("❌ Incorrect Answer / إجابة خاطئة", callback_data=f"report_incorrect_{question_id}")],
        [InlineKeyboardButton("📝 Typo or Grammar / خطأ إملائي أو نحوي", callback_data=f"report_typo_{question_id}")],
        [InlineKeyboardButton("🔍 Unclear Question / سؤال غير واضح", callback_data=f"report_unclear_{question_id}")],
        [InlineKeyboardButton("📚 Wrong Topic / موضوع خاطئ", callback_data=f"report_topic_{question_id}")],
        [InlineKeyboardButton("🔙 Back / العودة", callback_data="back_to_answer")]
    ]
    
    report_markup = InlineKeyboardMarkup(report_keyboard)
    
    report_message = (
        "🚨 **Report Question / الإبلاغ عن السؤال**\n\n"
        "Please select the reason for reporting:\n"
        "يرجى اختيار سبب الإبلاغ:\n\n"
        "Choose the most appropriate reason to help us improve the question quality.\n"
        "اختر السبب الأكثر ملاءمة لمساعدتنا في تحسين جودة السؤال."
    )
    
    await query.edit_message_text(report_message, reply_markup=report_markup, parse_mode='Markdown')

async def handle_report_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة سبب الإبلاغ المحدد"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    update_last_interaction(user.id)
    
    # استخراج نوع البلاغ ومعرف السؤال
    callback_data = query.data
    parts = callback_data.split('_')
    
    if len(parts) < 3:
        await query.edit_message_text("عذراً، حدث خطأ في معالجة البلاغ.")
        return
    
    report_type = parts[1]
    question_id = int(parts[2])
    
    # تحديد سبب البلاغ
    report_reasons = {
        'incorrect': 'Incorrect Answer / إجابة خاطئة',
        'typo': 'Typo or Grammar / خطأ إملائي أو نحوي',
        'unclear': 'Unclear Question / سؤال غير واضح',
        'topic': 'Wrong Topic / موضوع خاطئ'
    }
    
    report_reason = report_reasons.get(report_type, 'Other / أخرى')
    
    # حفظ البلاغ
    success = report_question(user.id, question_id, report_reason)
    
    if success:
        success_message = (
            "✅ **Report Submitted / تم إرسال البلاغ**\n\n"
            f"**Question ID:** {question_id}\n"
            f"**Report Reason:** {report_reason}\n\n"
            "Thank you for helping us improve the question quality!\n"
            "شكراً لك لمساعدتنا في تحسين جودة السؤال!\n\n"
            "We will review your report and take appropriate action.\n"
            "سنراجع بلاغك ونتخذ الإجراء المناسب."
        )
        
        keyboard = [
            [InlineKeyboardButton("Next Question / السؤال التالي", callback_data="quiz")],
            [InlineKeyboardButton("🔚 End Session / إنهاء الجلسة", callback_data="end_session")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(success_message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        error_message = (
            "❌ **Report Failed / فشل في إرسال البلاغ**\n\n"
            "Sorry, there was an error submitting your report.\n"
            "عذراً، حدث خطأ في إرسال البلاغ.\n\n"
            "Please try again later.\n"
            "يرجى المحاولة لاحقاً."
        )
        
        keyboard = [
            [InlineKeyboardButton("🔙 Back / العودة", callback_data="back_to_answer")],
            [InlineKeyboardButton("🔚 End Session / إنهاء الجلسة", callback_data="end_session")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(error_message, reply_markup=reply_markup, parse_mode='Markdown')

async def back_to_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """العودة إلى عرض الإجابة"""
    query = update.callback_query
    await query.answer()
    
    # إعادة عرض الإجابة مع الأزرار
    if "current_question" in context.user_data:
        # إعادة إنشاء رسالة النتيجة
        selected_answer = context.user_data.get("last_selected_answer", "")
        correct_answer = context.user_data["current_question"]["correct_answer"]
        explanation = context.user_data["current_question"]["explanation"]
        
        # إنشاء رسالة النتيجة
        if selected_answer == correct_answer:
            result_message = "✅ إجابة صحيحة!\nCorrect answer!\n\n"
        else:
            # عرض الإجابة الصحيحة كاملة
            correct_answer_text = ""
            question_data = context.user_data.get("current_question_data", {})
            if question_data:
                if correct_answer == "A":
                    correct_answer_text = f"A: {question_data.get('option_a', '')}"
                elif correct_answer == "B":
                    correct_answer_text = f"B: {question_data.get('option_b', '')}"
                elif correct_answer == "C":
                    correct_answer_text = f"C: {question_data.get('option_c', '')}"
                elif correct_answer == "D":
                    correct_answer_text = f"D: {question_data.get('option_d', '')}"
            
            result_message = (
                f"❌ إجابة خاطئة\n"
                f"Wrong answer\n\n"
                f"**Correct Answer / الإجابة الصحيحة:**\n"
                f"{correct_answer_text}\n\n"
            )
        
        # إضافة الشرح
        if explanation:
            result_message += f"**Explanation / الشرح:**\n{explanation}"
        else:
            result_message += "**No explanation available / لا يوجد شرح متاح**"
        
        # أزرار التحكم
        keyboard = [
            [InlineKeyboardButton("Next Question / السؤال التالي", callback_data="quiz")],
            [InlineKeyboardButton("🚨 Report Question / الإبلاغ عن السؤال", callback_data="report")],
            [InlineKeyboardButton("🔚 End Session / إنهاء الجلسة", callback_data="end_session")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(result_message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await query.edit_message_text("عذراً، لا يمكن العودة إلى الإجابة.")

async def test_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اختبار عدد الأسئلة الحقيقي"""
    try:
        # طريقة 1: استخدام count
        count_response = supabase.table('questions').select('*', count='exact').execute()
        count_method = count_response.count if hasattr(count_response, 'count') else 'Not available'
        
        # طريقة 2: جلب جميع الأسئلة
        all_response = supabase.table('questions').select('id').execute()
        all_method = len(all_response.data)
        
        # طريقة 3: جلب آخر 1000 سؤال
        limit_response = supabase.table('questions').select('id').order('id', desc=True).limit(1000).execute()
        limit_method = len(limit_response.data)
        
        test_message = (
            "🧪 **Test Count Results / نتائج اختبار العدد:**\n\n"
            f"📊 Count Method: {count_method}\n"
            f"📊 All Method: {all_method}\n"
            f"📊 Limit Method: {limit_method}\n\n"
            "This helps debug the question count issue.\n"
            "هذا يساعد في تشخيص مشكلة عدد الأسئلة."
        )
        
        await update.message.reply_text(test_message, parse_mode='Markdown')
        
    except Exception as e:
        error_message = f"❌ Error testing count: {e}"
        await update.message.reply_text(error_message)

async def db_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض معلومات قاعدة البيانات"""
    try:
        # معلومات الأسئلة
        questions_count = get_total_questions_count()
        
        # معلومات المستخدمين
        users_response = supabase.table('target_users').select('telegram_id', count='exact').execute()
        users_count = users_response.count if hasattr(users_response, 'count') else len(users_response.data)
        
        # معلومات الإجابات
        answers_response = supabase.table('user_answers_bot').select('id', count='exact').execute()
        answers_count = answers_response.count if hasattr(answers_response, 'count') else len(answers_response.data)
        
        info_message = (
            "🗄️ **Database Information / معلومات قاعدة البيانات:**\n\n"
            f"📚 **Questions / الأسئلة:**\n"
            f"Total Questions: {questions_count}\n"
            f"إجمالي الأسئلة: {questions_count}\n\n"
            f"👥 **Users / المستخدمين:**\n"
            f"Total Users: {users_count}\n"
            f"إجمالي المستخدمين: {users_count}\n\n"
            f"✅ **Answers / الإجابات:**\n"
            f"Total Answers: {answers_count}\n"
            f"إجمالي الإجابات: {answers_count}\n\n"
            "This shows the real numbers from your database.\n"
            "هذا يعرض الأرقام الحقيقية من قاعدة البيانات."
        )
        
        await update.message.reply_text(info_message, parse_mode='Markdown')
        
    except Exception as e:
        error_message = f"❌ Error getting database info: {e}"
        await update.message.reply_text(error_message)

async def test_bot_permissions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اختبار صلاحيات البوت في القناة"""
    try:
        channel_id = TELEGRAM_CHANNEL_ID.lstrip('@')
        
        # محاولة الحصول على معلومات القناة
        chat_info = await context.bot.get_chat(f"@{channel_id}")
        
        # محاولة الحصول على معلومات البوت في القناة
        bot_member = await context.bot.get_chat_member(f"@{channel_id}", context.bot.id)
        
        # محاولة الحصول على قائمة الأعضاء (اختبار الصلاحيات)
        try:
            # محاولة جلب عضو واحد للاختبار
            test_member = await context.bot.get_chat_member(f"@{channel_id}", context.bot.id)
            members_accessible = True
        except Exception as e:
            members_accessible = False
            members_error = str(e)
        
        # إنشاء رسالة التقرير
        report_message = (
            "🔧 **Bot Permissions Test / اختبار صلاحيات البوت**\n\n"
            f"📢 **Channel Info:**\n"
            f"**Name:** {chat_info.title}\n"
            f"**Username:** @{chat_info.username}\n"
            f"**Type:** {chat_info.type}\n\n"
            f"🤖 **Bot Status:**\n"
            f"**Role:** {bot_member.status}\n"
            f"**Can Access Members:** {'✅ Yes' if members_accessible else '❌ No'}\n\n"
        )
        
        if not members_accessible:
            report_message += (
                f"❌ **Members Access Error:**\n"
                f"{members_error}\n\n"
                "🔧 **Required Actions:**\n"
                "1. Make bot admin in channel\n"
                "2. Enable 'Add Members' permission\n"
                "3. Ensure bot has 'Invite Users' right\n\n"
                "🔧 **الإجراءات المطلوبة:**\n"
                "1. اجعل البوت مدير في القناة\n"
                "2. فعّل صلاحية 'إضافة أعضاء'\n"
                "3. تأكد من أن البوت لديه حق 'دعوة مستخدمين'"
            )
        else:
            report_message += (
                "✅ **All Permissions OK!**\n"
                "The bot can check channel subscriptions.\n\n"
                "✅ **جميع الصلاحيات جيدة!**\n"
                "البوت يمكنه التحقق من اشتراكات القناة."
            )
        
        await update.message.reply_text(report_message, parse_mode='Markdown')
        
    except Exception as e:
        error_message = (
            "❌ **Permission Test Failed / فشل اختبار الصلاحيات**\n\n"
            f"**Error:** {str(e)}\n\n"
            "🔧 **Check:**\n"
            "1. Channel username is correct\n"
            "2. Bot is added to channel\n"
            "3. Bot has admin rights\n\n"
            "🔧 **تحقق من:**\n"
            "1. اسم المستخدم للقناة صحيح\n"
            "2. البوت مضاف للقناة\n"
            "3. البوت لديه صلاحيات مدير"
        )
        await update.message.reply_text(error_message, parse_mode='Markdown')

def report_question(user_id: int, question_id: int, report_reason: str):
    """الإبلاغ عن سؤال"""
    try:
        # تحديث السجل الموجود أو إنشاء سجل جديد
        response = supabase.table('user_answers_bot').update({
            'is_reported': True,
            'report_reason': report_reason
        }).eq('user_id', user_id).eq('question_id', question_id).execute()
        
        print(f"✅ Question {question_id} reported by user {user_id}: {report_reason}")
        return True
    except Exception as e:
        print(f"⚠️ Warning: Could not report question: {e}")
        return False

async def check_channel_subscription(user_id: int, bot):
    """التحقق من اشتراك المستخدم في القناة"""
    if not CHANNEL_SUBSCRIPTION_REQUIRED:
        return True
    
    try:
        # إزالة @ من معرف القناة إذا كان موجوداً
        channel_id = TELEGRAM_CHANNEL_ID.lstrip('@')
        
        # التحقق من حالة العضو في القناة
        member = await bot.get_chat_member(f"@{channel_id}", user_id)
        
        # الحالات المقبولة: member, administrator, creator
        if member.status in ['member', 'administrator', 'creator']:
            print(f"✅ User {user_id} is subscribed to channel @{channel_id}")
            return True
        else:
            print(f"❌ User {user_id} is not subscribed to channel @{channel_id} (status: {member.status})")
            return False
            
    except Exception as e:
        print(f"⚠️ Warning: Could not check channel subscription for user {user_id}: {e}")
        # في حالة الخطأ، نفترض أن المستخدم مشترك (لعدم إيقاف البوت)
        return True

async def show_subscription_required(update: Update, context: ContextTypes.DEFAULT_TYPE, is_new_user: bool = False):
    """عرض رسالة طلب الاشتراك في القناة"""
    
    if is_new_user:
        # للمستخدمين الجدد - بعد 10 أسئلة
        message = (
            "🎉 **Congratulations! / مبروك!**\n\n"
            "You've completed your first 10 questions!\n"
            "لقد أكملت أول 10 أسئلة!\n\n"
            "🌟 **To continue learning, please subscribe to our channel:**\n"
            "🌟 **لمتابعة التعلم، يرجى الاشتراك في قناتنا:**\n\n"
            f"📢 **Channel:** {TELEGRAM_CHANNEL_ID}\n"
            f"🔗 **Link:** {TELEGRAM_CHANNEL_LINK}\n\n"
            "After subscribing, you can continue with more questions!\n"
            "بعد الاشتراك، يمكنك متابعة المزيد من الأسئلة!"
        )
    else:
        # للمستخدمين القدامى - عند إلغاء الاشتراك
        message = (
            "⚠️ **Subscription Required / الاشتراك مطلوب**\n\n"
            "Your access has been paused.\n"
            "تم إيقاف وصولك مؤقتاً.\n\n"
            "🌟 **Please subscribe to our channel to continue:**\n"
            "🌟 **يرجى الاشتراك في قناتنا للمتابعة:**\n\n"
            f"📢 **Channel:** {TELEGRAM_CHANNEL_ID}\n"
            f"🔗 **Link:** {TELEGRAM_CHANNEL_LINK}\n\n"
            "After subscribing, click 'Check Subscription' below.\n"
            "بعد الاشتراك، اضغط على 'التحقق من الاشتراك' أدناه."
        )
    
    # إنشاء الأزرار
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel / انضم للقناة", url=TELEGRAM_CHANNEL_LINK)],
        [InlineKeyboardButton("✅ Check Subscription / التحقق من الاشتراك", callback_data="check_subscription")],
        [InlineKeyboardButton("🏠 Main Menu / القائمة الرئيسية", callback_data="menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التحقق من الاشتراك في القناة"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    update_last_interaction(user.id)
    
    # التحقق من الاشتراك
    is_subscribed = await check_channel_subscription(user.id, context.bot)
    
    if is_subscribed:
        # المستخدم مشترك - يمكنه المتابعة
        success_message = (
            "✅ **Subscription Verified! / تم التحقق من الاشتراك!**\n\n"
            "Welcome back! You can now continue learning.\n"
            "مرحباً بعودتك! يمكنك الآن متابعة التعلم.\n\n"
            "Choose what you want to do:\n"
            "اختر ما تريد القيام به:"
        )
        
        keyboard = [
            [InlineKeyboardButton("🚀 Start Quiz / بدء الاختبار", callback_data="quiz")],
            [InlineKeyboardButton("📊 My Stats / إحصائياتي", callback_data="stats")],
            [InlineKeyboardButton("🏠 Main Menu / القائمة الرئيسية", callback_data="menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(success_message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        # المستخدم غير مشترك
        await show_subscription_required(update, context, is_new_user=False)

# Flask app for Cloud Run
app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Cloud Run"""
    logger.info("Health check endpoint called")
    return jsonify({
        'status': 'healthy',
        'bot': 'Vignora Medical Questions Bot',
        'timestamp': datetime.now().isoformat()
    }), 200

@app.route('/', methods=['GET'])
def home():
    """Home endpoint"""
    logger.info("Home endpoint called")
    return jsonify({
        'message': 'Vignora Medical Questions Bot is running!',
        'status': 'active',
        'endpoints': {
            'health': '/health',
            'webhook': '/webhook'
        }
    }), 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint for Telegram updates"""
    try:
        logger.info("Webhook endpoint called")
        # Get the update from Telegram
        update_data = request.get_json()
        
        # Process the update asynchronously
        asyncio.run(process_update(update_data))
        
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'error': str(e)}), 500

async def process_update(update_data):
    """Process Telegram update asynchronously"""
    try:
        logger.info("Processing Telegram update")
        if application is None:
            logger.error("Application is not initialized yet.")
            return
        
        # Create update object
        update = Update.de_json(update_data, application.bot)
        
        # Process the update
        await application.process_update(update)
        logger.info("Telegram update processed successfully")
    except Exception as e:
        logger.error(f"Error processing update: {e}")

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    global application
    
    print("🚀 Starting Medical Questions Bot...")
    logger.info("Starting Medical Questions Bot...")
    print(f"📡 Supabase URL: {SUPABASE_URL}")
    print(f"🤖 Telegram Token: {TELEGRAM_TOKEN[:20]}...")
    
    # معلومات القناة
    if CHANNEL_SUBSCRIPTION_REQUIRED:
        print(f"📢 Channel Subscription Required: YES")
        print(f"📢 Channel ID: {TELEGRAM_CHANNEL_ID}")
        print(f"🔗 Channel Link: {TELEGRAM_CHANNEL_LINK}")
    else:
        print(f"📢 Channel Subscription Required: NO")
    
    # إنشاء التطبيق
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    logger.info("Telegram application created successfully")
    
    # إضافة معالجات الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(CallbackQueryHandler(send_question, pattern="^quiz$"))
    application.add_handler(CallbackQueryHandler(handle_answer, pattern="^answer_"))
    application.add_handler(CallbackQueryHandler(show_stats, pattern="^stats$"))
    application.add_handler(CallbackQueryHandler(show_quiz_menu, pattern="^menu$"))
    application.add_handler(CallbackQueryHandler(end_session, pattern="^end_session$"))
    application.add_handler(CallbackQueryHandler(handle_report, pattern="^report$"))
    application.add_handler(CallbackQueryHandler(handle_report_reason, pattern="^report_incorrect_|^report_typo_|^report_unclear_|^report_topic_"))
    application.add_handler(CallbackQueryHandler(back_to_answer, pattern="^back_to_answer$"))
    application.add_handler(CommandHandler("test_count", test_count))
    application.add_handler(CommandHandler("db_info", db_info))
    application.add_handler(CallbackQueryHandler(test_bot_permissions, pattern="^test_bot_permissions$"))
    application.add_handler(CallbackQueryHandler(check_subscription, pattern="^check_subscription$"))
    logger.info("All handlers added successfully")
    
    # تشغيل البوت
    print("✅ Bot is running and ready to receive messages!")
    print("📱 Users can now start the bot with /start")
    logger.info("Bot is running and ready to receive messages!")
    
    # Check if running on Cloud Run
    if os.environ.get('PORT'):
        print("🌐 Running on Cloud Run with Gunicorn...")
        logger.info("Running on Cloud Run with Gunicorn...")
        print("📝 Note: Flask will be started by Gunicorn")
        # Don't start Flask here - Gunicorn will handle it
        # Just keep the main thread alive for the bot
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            print("🛑 Bot stopped by user")
            logger.info("Bot stopped by user")
    else:
        print("🔄 Running locally - Using polling mode...")
        logger.info("Running locally - Using polling mode...")
        application.run_polling()

if __name__ == "__main__":
    main()