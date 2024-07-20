import os
import jdatetime
import openpyxl
import pytz
from io import BytesIO
from dotenv import load_dotenv
from datetime import datetime, timedelta
from telegram import Update
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

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        'به ربات حضور و غیاب خوش آمدید.\n'
        'برای دریافت راهنما از /help استفاده کنید.'
    )

async def checkin(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    now = get_iran_time()
    date = now.date()
    jalali_date = gregorian_to_jalali(date)
    day = now.day
    check_in_time = now.time().isoformat()

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
        await update.message.reply_text(f'شما در تاریخ {jalali_date} و ساعت {check_in_time} برای ثبت ورود به شرکت وارد شدید.')
    except psycopg2.Error as e:
        await update.message.reply_text(f"خطا در پایگاه داده: {e}")

async def checkout(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    now = get_iran_time()
    date = now.date()
    jalali_date = gregorian_to_jalali(date)
    day = now.day
    check_out_time = now.time().isoformat()

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
        await update.message.reply_text(f'شما در تاریخ {jalali_date} و ساعت {check_out_time} برای ثبت خروج از شرکت خارج شدید.')
    except psycopg2.Error as e:
        await update.message.reply_text(f"خطا در پایگاه داده: {e}")

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
            await update.message.reply_text('در این ماه رکوردی ثبت نشده است.')
            return

        # Create an Excel file
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = 'گزارش حضور'

        # Add headers
        headers = ['تاریخ', 'روز', 'ورود', 'خروج', 'مدت زمان کار']
        sheet.append(headers)

        total_hours = 0

        for record in records:
            date, day, check_in, check_out = record

            # Convert datetime and time to string, handling None values
            check_in_str = check_in.isoformat() if check_in else 'ورود ثبت نشده'
            check_out_str = check_out.isoformat() if check_out else 'خروج ثبت نشده'

            # Convert strings to datetime objects if not 'ثبت نشده'
            try:
                check_in_time = datetime.fromisoformat(check_in_str) if check_in_str != 'ورود ثبت نشده' else None
            except ValueError:
                check_in_time = None

            try:
                check_out_time = datetime.fromisoformat(check_out_str) if check_out_str != 'خروج ثبت نشده' else get_iran_time()
            except ValueError:
                check_out_time = get_iran_time()

            work_duration = (check_out_time - check_in_time) if check_in_time else None
            total_hours += work_duration.total_seconds() / 3600 if work_duration else 0

            row = [
                gregorian_to_jalali(date),
                day,
                check_in_str,
                check_out_str,
                str(work_duration) if work_duration else 'ندارد'
            ]
            sheet.append(row)

        # Add total hours to the end of the file
        sheet.append([])
        sheet.append(['جمع ساعات کار', f'{total_hours:.2f}'])

        # Save the workbook to a BytesIO object
        file_stream = BytesIO()
        workbook.save(file_stream)
        file_stream.seek(0)

        # Send the file to the user
        await update.message.reply_document(document=file_stream, filename=f'attendance_report_{jalali_month}_{year}.xlsx')

    except psycopg2.Error as e:
        await update.message.reply_text(f"خطا در پایگاه داده: {e}")
    except Exception as e:
        await update.message.reply_text(f"خطا: {e}")

async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        'دستورات موجود در ربات:\n'
        '/checkin - برای ثبت ورود به شرکت.\n'
        '/checkout - برای ثبت خروج از شرکت.\n'
        '/report - برای دریافت گزارش ماهانه.\n'
        '/help - برای دریافت راهنمای دستورات.'
    )

def main():
    application = Application.builder().token(TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('checkin', checkin))
    application.add_handler(CommandHandler('checkout', checkout))
    application.add_handler(CommandHandler('report', report))
    application.add_handler(CommandHandler('help', help_command))

    # Run the bot
    application.run_polling()

if __name__ == "__main__":
    main()

