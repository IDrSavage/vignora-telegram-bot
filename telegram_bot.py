import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes
from supabase import create_client, Client
from dotenv import load_dotenv

# تحميل متغيرات البيئة
load_dotenv()

# تعيين المتغيرات الثابتة - مطلوبة من ملف .env
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# التحقق من وجود المتغيرات المطلوبة
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is required in .env file")
if not SUPABASE_URL:
    raise ValueError("SUPABASE_URL is required in .env file")
if not SUPABASE_KEY:
    raise ValueError("SUPABASE_KEY is required in .env file")

# إنشاء عميل Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_random_question():
    """جلب سؤال عشوائي من قاعدة البيانات"""
    try:
        # استعلام Supabase لجلب سؤال عشوائي مع البيانات الأساسية فقط
        response = supabase.table('questions').select(
            'id, question, option_a, option_b, option_c, option_d, correct_answer, explanation'
        ).limit(1).execute()
        
        if response.data and len(response.data) > 0:
            question = response.data[0]
            return question
        else:
            print("No questions found in database")
            return None
            
    except Exception as e:
        print(f"Error fetching question: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بداية التفاعل مع البوت"""
    keyboard = [
        [InlineKeyboardButton("Start Quiz / بدء الاختبار", callback_data="quiz")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = (
        "Welcome to the Medical Questions Bot!\n"
        "مرحباً بك في بوت الأسئلة الطبية!\n\n"
        "Press the button below to start answering questions.\n"
        "اضغط على الزر أدناه لبدء الإجابة على الأسئلة."
    )
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال سؤال للمستخدم"""
    query = update.callback_query
    await query.answer()
    
    question_data = fetch_random_question()
    if not question_data:
        await query.edit_message_text("عذراً، حدث خطأ في جلب السؤال. حاول مرة أخرى.")
        return
    
    # تنسيق السؤال - استخدام البيانات الأساسية فقط
    question_text = (
        f"Q: {question_data.get('question', 'No question')}\n\n"
        "Options / الخيارات:"
    )
    
    # إنشاء أزرار الخيارات - بدون ترجمة
    keyboard = [
        [InlineKeyboardButton(f"A: {question_data.get('option_a', '')}", callback_data="answer_A")],
        [InlineKeyboardButton(f"B: {question_data.get('option_b', '')}", callback_data="answer_B")],
        [InlineKeyboardButton(f"C: {question_data.get('option_c', '')}", callback_data="answer_C")],
        [InlineKeyboardButton(f"D: {question_data.get('option_d', '')}", callback_data="answer_D")]
    ]
    
    # حفظ بيانات السؤال في سياق المستخدم
    context.user_data["current_question"] = {
        "correct_answer": question_data.get('correct_answer', ''),
        "explanation": question_data.get('explanation', '')
    }
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(question_text, reply_markup=reply_markup)

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة إجابة المستخدم"""
    query = update.callback_query
    await query.answer()
    
    # التحقق من وجود بيانات السؤال
    if "current_question" not in context.user_data:
        await query.edit_message_text("عذراً، حدث خطأ. يرجى البدء من جديد.")
        return
    
    selected_answer = query.data.split("_")[1]
    correct_answer = context.user_data["current_question"]["correct_answer"]
    explanation = context.user_data["current_question"]["explanation"]
    
    # إنشاء رسالة النتيجة
    if selected_answer == correct_answer:
        result_message = "✅ إجابة صحيحة!\nCorrect answer!\n\n"
    else:
        result_message = f"❌ إجابة خاطئة\nWrong answer\nالإجابة الصحيحة / Correct answer: {correct_answer}\n\n"
    
    # إضافة الشرح المبسط فقط
    if explanation:
        result_message += f"Explanation / الشرح:\n{explanation}"
    else:
        result_message += "No explanation available / لا يوجد شرح متاح"
    
    # أزرار التحكم - زر التالي فقط
    keyboard = [[InlineKeyboardButton("Next Question / السؤال التالي", callback_data="quiz")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(result_message, reply_markup=reply_markup)

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    try:
        # اختبار الاتصال بـ Supabase
        test_response = supabase.table('questions').select('count').limit(1).execute()
        print("✅ Successfully connected to Supabase!")
        print(f"Supabase URL: {SUPABASE_URL}")
        
    except Exception as e:
        print(f"❌ Error connecting to Supabase: {e}")
        return
        
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # إضافة معالجات الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(send_question, pattern="^quiz$"))
    application.add_handler(CallbackQueryHandler(handle_answer, pattern="^answer_"))
    
    # تشغيل البوت
    print("Bot is running...")
    print(f"Telegram Token: {TELEGRAM_TOKEN[:20]}...")
    application.run_polling()

if __name__ == "__main__":
    main()