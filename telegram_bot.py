import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters
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
        response = supabase.table('user_answers_bot').select('is_correct').eq('user_id', telegram_id).execute()
        if response.data:
            total_answers = len(response.data)
            correct_answers = sum(1 for answer in response.data if answer['is_correct'])
            accuracy = (correct_answers / total_answers) * 100 if total_answers > 0 else 0
            return {
                'total_answers': total_answers,
                'correct_answers': correct_answers,
                'accuracy': round(accuracy, 1)
            }
        return {'total_answers': 0, 'correct_answers': 0, 'accuracy': 0}
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch user stats: {e}")
        return {'total_answers': 0, 'correct_answers': 0, 'accuracy': 0}

def get_user_answered_questions(telegram_id: int):
    """جلب الأسئلة التي أجاب عليها المستخدم"""
    try:
        response = supabase.table('user_answers_bot').select('question_id').eq('user_id', telegram_id).execute()
        if response.data:
            return [answer['question_id'] for answer in response.data]
        return []
    except Exception as e:
        print(f"⚠️ Warning: Could not fetch user answers: {e}")
        return []

def fetch_random_question(telegram_id: int = None):
    """جلب سؤال عشوائي من قاعدة البيانات (غير مجاب عليه من قبل المستخدم)"""
    try:
        # إذا كان هناك معرف مستخدم، نستثني الأسئلة المجاب عليها
        if telegram_id:
            answered_questions = get_user_answered_questions(telegram_id)
            
            # استعلام لجلب سؤال عشوائي غير مجاب عليه
            if answered_questions:
                response = supabase.table('questions').select(
                    'id, question, option_a, option_b, option_c, option_d, correct_answer, explanation'
                ).not_.in_('id', answered_questions).limit(1).execute()
            else:
                # المستخدم لم يجب على أي سؤال بعد
                response = supabase.table('questions').select(
                    'id, question, option_a, option_b, option_c, option_d, correct_answer, explanation'
                ).limit(1).execute()
        else:
            # بدون معرف مستخدم - جلب أي سؤال
            response = supabase.table('questions').select(
                'id, question, option_a, option_b, option_c, option_d, correct_answer, explanation'
            ).limit(1).execute()
        
        if response.data and len(response.data) > 0:
            question = response.data[0]
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
            "Welcome to the Medical Questions Bot!\n"
            "مرحباً بك في بوت الأسئلة الطبية!\n\n"
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
            "Thank you! Your information has been saved.\n"
            "شكراً لك! تم حفظ معلوماتك.",
            reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
        )
        
        # عرض قائمة الاختبار
        await show_quiz_menu(update, context)
    else:
        await update.message.reply_text("Sorry, there was an error saving your information. Please try again.")

async def show_quiz_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة الاختبار"""
    user = update.effective_user
    telegram_id = user.id
    
    # تحديث آخر تفاعل
    update_last_interaction(telegram_id)
    
    keyboard = [
        [InlineKeyboardButton("Start Quiz / بدء الاختبار", callback_data="quiz")],
        [InlineKeyboardButton("My Stats / إحصائياتي", callback_data="stats")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_message = (
        "Welcome back to the Medical Questions Bot!\n"
        "مرحباً بك مرة أخرى في بوت الأسئلة الطبية!\n\n"
        "Press the button below to start answering questions.\n"
        "اضغط على الزر أدناه لبدء الإجابة على الأسئلة."
    )
    
    if hasattr(update, 'callback_query'):
        await update.callback_query.edit_message_text(welcome_message, reply_markup=reply_markup)
    else:
        await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات المستخدم"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    stats = get_user_stats(user.id)
    
    stats_message = (
        f"📊 Your Statistics / إحصائياتك\n\n"
        f"Total Questions: {stats['total_answers']}\n"
        f"إجمالي الأسئلة: {stats['total_answers']}\n\n"
        f"Correct Answers: {stats['correct_answers']}\n"
        f"الإجابات الصحيحة: {stats['correct_answers']}\n\n"
        f"Accuracy: {stats['accuracy']}%\n"
        f"الدقة: {stats['accuracy']}%\n\n"
        f"Keep going! 🚀\n"
        f"استمر! 🚀"
    )
    
    # أزرار العودة
    keyboard = [[InlineKeyboardButton("Back to Menu / العودة للقائمة", callback_data="menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(stats_message, reply_markup=reply_markup)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال سؤال للمستخدم"""
    query = update.callback_query
    await query.answer()
    
    # تحديث آخر تفاعل
    user = query.from_user
    update_last_interaction(user.id)
    
    question_data = fetch_random_question(user.id)
    if not question_data:
        # التحقق من سبب عدم وجود أسئلة
        answered_questions = get_user_answered_questions(user.id)
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
        "question_id": question_data.get('id', ''),
        "correct_answer": question_data.get('correct_answer', ''),
        "explanation": question_data.get('explanation', '')
    }
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(question_text, reply_markup=reply_markup)

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
    
    # تحديد ما إذا كانت الإجابة صحيحة
    is_correct = selected_answer == correct_answer
    
    # حفظ إجابة المستخدم
    save_user_answer(user.id, question_id, selected_answer, correct_answer, is_correct)
    
    # إنشاء رسالة النتيجة
    if is_correct:
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
    print("🚀 Starting Medical Questions Bot...")
    print(f"📡 Supabase URL: {SUPABASE_URL}")
    print(f"🤖 Telegram Token: {TELEGRAM_TOKEN[:20]}...")
    
    # إنشاء التطبيق
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # إضافة معالجات الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    application.add_handler(CallbackQueryHandler(send_question, pattern="^quiz$"))
    application.add_handler(CallbackQueryHandler(handle_answer, pattern="^answer_"))
    application.add_handler(CallbackQueryHandler(show_stats, pattern="^stats$"))
    application.add_handler(CallbackQueryHandler(show_quiz_menu, pattern="^menu$"))
    
    # تشغيل البوت
    print("✅ Bot is running and ready to receive messages!")
    print("📱 Users can now start the bot with /start")
    application.run_polling()

if __name__ == "__main__":
    main()