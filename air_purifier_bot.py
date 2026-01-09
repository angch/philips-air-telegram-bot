from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import asyncio
import os
import logging
import shutil
import ast
import json
import io
import traceback
from diagram_renderer import render_status_image

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def get_air_purifier_status():
    """Gets the status from the air purifier."""
    logging.info("Running uvx aioairctrl command...")
    
    uvx_path = shutil.which("uvx")
    if not uvx_path:
        logging.error("uvx command not found")
        return None

    try:
        process = await asyncio.create_subprocess_exec(
            "uvx", "aioairctrl", "-H", "10.1.0.137", "status",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_text = stderr.decode().strip()
            logging.error(f"Error executing command. Exit Code: {process.returncode}. Stderr: {error_text}")
            return None

        output = stdout.decode().strip()
        logging.info(f"Command output: {output}")
        
        # Helper to try parsing string as dict/json
        def try_parse(s):
            # Try JSON first
            try:
                return json.loads(s)
            except json.JSONDecodeError:
                pass
            # Try ast.literal_eval
            try:
                return ast.literal_eval(s)
            except (ValueError, SyntaxError):
                return None

        # 1. Try whole string
        data = try_parse(output)
        if data: return data

        # 2. Try finding dict-like substring
        start = output.find('{')
        end = output.rfind('}')
        if start != -1 and end != -1 and end > start:
            potential_dict = output[start:end+1]
            data = try_parse(potential_dict)
            if data: return data

        logging.error(f"Failed to parse output as dict/json: {output}")
        return None

    except Exception as e:
        logging.error(f"Unexpected error getting status: {e}")
        return None

async def generate_status_diagram(data):
    """
    Generates a status diagram using HTML/Playwright.
    """
    try:
        image_data = await render_status_image(data)
        return image_data

    except Exception as e:
        logging.error(f"Error generating diagram: {traceback.format_exc()}")
        return None

async def send_status_image(bot, chat_id, image_data, caption=None):
    """Helper to send the image."""
    try:
        image_file = io.BytesIO(image_data)
        image_file.name = "status_diagram.png"
        await bot.send_photo(chat_id=chat_id, photo=image_file, caption=caption)
    except Exception as e:
        logging.error(f"Failed to send photo: {e}")

async def mock_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates a status diagram using mock data."""
    user_msg = "Generating mock status diagram..."
    await update.message.reply_text(user_msg)

    mock_data = {
        'name': 'Mock Device',
        'type': 'AC1234',
        'pm25': 45,
        'iaql': 6,
        'fltsts1': 1000,
        'flttotal1': 4000,
        'fltsts0': 200,
        'flttotal0': 720,
        'err': 0
    }

    diagram_data = await generate_status_diagram(mock_data)

    if diagram_data:
         await send_status_image(context.bot, update.message.chat_id, diagram_data, caption="Mock Status Diagram")
    else:
        await update.message.reply_text("Failed to generate mock diagram.")

async def check_air_quality(context: ContextTypes.DEFAULT_TYPE):
    """Periodic job to check air quality and notify on change."""
    logging.info("Periodic check for air quality...")

    current_state = await get_air_purifier_status()

    if current_state is None:
        logging.warning("Could not get status.")
        return

    # Access last_known_state from bot_data
    last_known_state = context.bot_data.get('last_known_state')

    should_notify = False

    if last_known_state is None:
        logging.info("Initial state recorded.")
        context.bot_data['last_known_state'] = current_state
        return

    # Check for changes
    pm25_old = last_known_state.get('pm25', 0)
    pm25_new = current_state.get('pm25', 0)

    if abs(pm25_new - pm25_old) > 5:
        should_notify = True
        logging.info(f"PM2.5 changed significantly: {pm25_old} -> {pm25_new}")

    if last_known_state.get('iaql') != current_state.get('iaql'):
        should_notify = True
        logging.info(f"IAI changed: {last_known_state.get('iaql')} -> {current_state.get('iaql')}")

    if last_known_state.get('err') != current_state.get('err'):
        should_notify = True
        logging.info("Error state changed.")

    if should_notify:
        logging.info("State changed, generating diagram...")
        context.bot_data['last_known_state'] = current_state

        diagram_data = await generate_status_diagram(current_state)

        if diagram_data:
            chat_id = os.getenv("TELEGRAM_CHAT_ID")
            if chat_id:
                await send_status_image(context.bot, chat_id, diagram_data, caption="Air Quality Changed")
            else:
                logging.error("TELEGRAM_CHAT_ID not set, cannot send notification.")
        else:
            logging.error("Failed to generate diagram for notification.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual status command."""
    user_msg = "Checking status and generating diagram..."
    await update.message.reply_text(user_msg)

    data = await get_air_purifier_status()
    if data:
        diagram_data = await generate_status_diagram(data)
        if diagram_data:
             await send_status_image(context.bot, update.message.chat_id, diagram_data)
        else:
            await update.message.reply_text("Failed to generate diagram. Sending text report instead.")
            # Fallback to text
            from formatter import format_status
            response = format_status(str(data))
            await update.message.reply_text(response, parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text("Failed to get status.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if "status" in text or "explain" in text or "report" in text:
        await status(update, context)

if __name__ == '__main__':
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
        exit(1)
        
    application = ApplicationBuilder().token(token).build()
    
    application.bot_data['last_known_state'] = None

    if application.job_queue:
        application.job_queue.run_repeating(check_air_quality, interval=300, first=10)
        logging.info("JobQueue configured.")
    else:
        logging.error("JobQueue not available! Please install 'python-telegram-bot[job-queue]'.")

    start_handler = CommandHandler('status', status)
    mock_handler = CommandHandler('mockstatus', mock_status)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    
    application.add_handler(start_handler)
    application.add_handler(mock_handler)
    application.add_handler(message_handler)
    
    print("Bot is running...")
    application.run_polling()
