import os
import jdatetime
import openpyxl
import pytz
from io import BytesIO
from dotenv import load_dotenv
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext
import psycopg2

# Load environment variables from .env file
load_dotenv()

# Fetch environment variables
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
TOKEN = os.getenv('TELEGRAM_TOKEN')

# Define Iran time zone
IRAN_TZ = pytz.timezone('Asia/Tehran')

def get_iran_time():
    return datetime.now(IRAN_TZ)

def gregorian_to_jalali(date):
    jdate = jdatetime.date.fromgregorian(date=date)
    return f'{jdate.year}/{jdate.month:02}/{jdate.day:02}'

def get_custom_keyboard():
    keyboard = [
        ['ﻭﺭﻭﺩ', 'ﺥﺭﻮﺟ'],
        ['ﮒﺯﺍﺮﺷ', 'ﺭﺎﻬﻨﻣﺍ']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        'ﺐﻫ ﺮﺑﺎﺗ ﺢﺿﻭﺭ ﻭ ﻎﯾﺎﺑ ﺥﻮﺷ ﺂﻣﺪﯾﺩ.\n'
        'ﺏﺭﺎﯾ ﺩﺮﯾﺎﻔﺗ ﺭﺎﻬﻨﻣﺍ ﺍﺯ /help ﺎﺴﺘﻓﺍﺪﻫ ﮏﻨﯾﺩ.',
        reply_markup=get_custom_keyboard()
    )

async def checkin(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    now = get_iran_time()
    date = now.date()
    jalali_date = gregorian_to_jalali(date)
    day = now.day
    check_in_time = now.strftime('%H:%M')  # Format time without seconds

    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST)
        c = conn.cursor()
        c.execute('''
        INSERT INTO attendance (user_id, username, date, jalali_date, day, check_in)
        VALUES (%s, %s, %s, %s, %s, %s)
        ''', (user_id, username, date, jalali_date, day, check_in_time))
        conn.commit()
        c.execute('SELECT * FROM attendance ORDER BY id DESC LIMIT 1')
        last_row = c.fetchone()
        print(f"Inserted data: {last_row}")
        conn.close()
        await update.message.reply_text(f'ﺶﻣﺍ ﺩﺭ ﺕﺍﺮﯿﺧ {jalali_date} ﻭ ﺱﺎﻌﺗ {check_in_time} ﻭﺍﺭﺩ ﺵﺪﯾﺩ.')
    except psycopg2.Error as e:
        await update.message.reply_text(f"ﺦﻃﺍ ﺩﺭ ﭖﺎﯿﮔﺎﻫ ﺩﺍﺪﻫ: {e}")

async def checkout(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    now = get_iran_time()
    date = now.date()
    jalali_date = gregorian_to_jalali(date)
    day = now.day
    check_out_time = now.strftime('%H:%M')  # Format time without seconds

    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST)
        c = conn.cursor()
        c.execute('''
        UPDATE attendance
        SET check_out = %s
        WHERE user_id = %s AND date = %s AND day = %s AND check_out IS NULL
        ''', (check_out_time, user_id, date, day))
        conn.commit()
        conn.close()
        await update.message.reply_text(f'ﺶﻣﺍ ﺩﺭ ﺕﺍﺮﯿﺧ {jalali_date} ﻭ ﺱﺎﻌﺗ {check_out_time} ﺥﺍﺮﺟ ﺵﺪﯾﺩ.')
    except psycopg2.Error as e:
        await update.message.reply_text(f"ﺦﻃﺍ ﺩﺭ ﭖﺎﯿﮔﺎﻫ ﺩﺍﺪﻫ: {e}")

async def report(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    now = get_iran_time()
    month = now.month
    year = now.year
    jalali_month = gregorian_to_jalali(now).split('/')[1]

    try:
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST)
        c = conn.cursor()
        c.execute('''
        SELECT date, day, check_in, check_out
        FROM attendance
        WHERE user_id = %s AND EXTRACT(MONTH FROM date) = %s AND EXTRACT(YEAR FROM date) = %s
        ''', (user_id, month, year))

        records = c.fetchall()
        conn.close()

        if not records:
            await update.message.reply_text('ﺩﺭ ﺎﯿﻧ ﻡﺎﻫ ﺮﮐﻭﺭﺪﯾ ﺚﺒﺗ ﻦﺷﺪﻫ ﺎﺴﺗ.')
            return

        # Create an Excel file
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = 'ﮒﺯﺍﺮﺷ ﺢﺿﻭﺭ'

        # Add headers
        headers = ['ﺕﺍﺮﯿﺧ', 'ﺭﻭﺯ', 'ﻭﺭﻭﺩ', 'ﺥﺭﻮﺟ', 'ﻡﺪﺗ ﺰﻣﺎﻧ ﮎﺍﺭ']
        sheet.append(headers)

        total_hours = 0

        for record in records:
            date, day, check_in, check_out = record

            # Format times without seconds
            check_in_str = check_in.strftime('%H:%M') if check_in else 'ﻭﺭﻭﺩ ﺚﺒﺗ ﻦﺷﺪﻫ'
            check_out_str = check_out.strftime('%H:%M') if check_out else 'ﺥﺭﻮﺟ ﺚﺒﺗ ﻦﺷﺪﻫ'

            # Calculate work duration
            if check_in and check_out:
                check_in_time = datetime.combine(date, check_in)
                check_out_time = datetime.combine(date, check_out)
                work_duration = check_out_time - check_in_time
                work_duration_hours = work_duration.total_seconds() / 3600
                total_hours += work_duration_hours
                work_duration_str = f'{work_duration_hours:.2f} ﺱﺎﻌﺗ'
            else:
                work_duration_str = 'ﻥﺩﺍﺭﺩ'

            row = [
                gregorian_to_jalali(date),
                day,
                check_in_str,
                check_out_str,
                work_duration_str
            ]
            sheet.append(row)

        # Add total hours to the end of the file
        sheet.append([])
        sheet.append(['ﺞﻤﻋ ﺱﺎﻋﺎﺗ ﮎﺍﺭ', f'{total_hours:.2f} ﺱﺎﻌﺗ'])

        # Save the workbook to a BytesIO object
        file_stream = BytesIO()
        workbook.save(file_stream)
        file_stream.seek(0)

        # Send the file to the user
        await update.message.reply_document(document=file_stream, filename=f'attendance_report_{jalali_month}_{year}.xlsx')

    except psycopg2.Error as e:
        await update.message.reply_text(f"ﺦﻃﺍ ﺩﺭ ﭖﺎﯿﮔﺎﻫ ﺩﺍﺪﻫ: {e}")
    except Exception as e:
        await update.message.reply_text(f"ﺦﻃﺍ: {e}")

async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        'ﺪﺴﺗﻭﺭﺎﺗ:\n'
        '/checkin - ﻭﺭﻭﺩ\n'
        '/checkout - ﺥﺭﻮﺟ\n'
        '/report - ﮒﺯﺍﺮﺷ\n'
        '/help - ﺭﺎﻬﻨﻣﺍ'
    )

def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("checkin", checkin))
    application.add_handler(CommandHandler("checkout", checkout))
    application.add_handler(CommandHandler("report", report))
    application.add_handler(CommandHandler("help", help_command))

    application.run_polling()

if __name__ == '__main__':
    main()

