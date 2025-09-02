# Medical Questions Telegram Bot

A Telegram bot for medical quiz questions built with Python and Supabase.

## Features

- Interactive medical quiz questions
- Multiple choice answers (A, B, C, D)
- Immediate feedback with explanations
- Supabase database integration
- Bilingual interface (English/Arabic)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. **IMPORTANT: Create a `.env` file with your credentials:**
   - Copy the example below
   - Replace with your actual values
   - **NEVER commit the .env file to Git**

```bash
# Create .env file with these variables:
TELEGRAM_TOKEN=your_actual_bot_token_here
SUPABASE_URL=your_actual_supabase_url_here
SUPABASE_KEY=your_actual_supabase_key_here
```pyح

3. Run the bot:
```bash
python telegram_bot.py
```

## Security Notes

- ⚠️ **NEVER commit your .env file to Git**
- ⚠️ **Keep your bot tokens private**
- ⚠️ **The .env file is already in .gitignore**

## Environment Variables

The bot requires these environment variables:
- `TELEGRAM_TOKEN` - Your Telegram Bot Token from @BotFather
- `SUPABASE_URL` - Your Supabase project URL
- `SUPABASE_KEY` - Your Supabase anon/public key

## Database Schema

The bot expects a `questions` table with the following columns:
- `id` - Question ID
- `question` - Question text
- `option_a`, `option_b`, `option_c`, `option_d` - Answer options
- `correct_answer` - Correct answer (A, B, C, or D)
- `explanation` - Simple explanation

## Usage

1. Start the bot with `/start`
2. Click "Start Quiz" to begin
3. Answer questions by selecting A, B, C, or D
4. View explanations and continue to next question

## Contributing

Feel free to submit issues and enhancement requests!
