from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import asyncio
import os
import logging
import shutil
from formatter import format_status

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = "Checking status..."
    await update.message.reply_text(user_msg)
    
    try:
        # Run the command exactly as requested
        # 'uvx' needs to be in the PATH. If running on a system where uv is installed, it should be fine.
        logging.info("Running uvx aioairctrl command...")
        
        # Check if uvx is available
        uvx_path = shutil.which("uvx")
        if not uvx_path:
            raise FileNotFoundError("uvx command not found")

        # Use asyncio.create_subprocess_exec for non-blocking execution
        process = await asyncio.create_subprocess_exec(
            "uvx", "aioairctrl", "-H", "10.1.0.137", "status",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_text = stderr.decode().strip()
            error_msg = f"Error executing command.\nExit Code: {process.returncode}\nStderr: {error_text}"
            logging.error(error_msg)
            await update.message.reply_text(error_msg)
            return

        output = stdout.decode().strip()
        logging.info(f"Command output: {output}")
        
        response = format_status(output)
        
        # Send as HTML
        await update.message.reply_text(response, parse_mode=ParseMode.HTML)

    except FileNotFoundError:
        error_msg = "Error: 'uvx' command not found. Please ensure 'uv' is installed and in your PATH."
        logging.error(error_msg)
        await update.message.reply_text(error_msg)
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        logging.error(error_msg)
        await update.message.reply_text(error_msg)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # If the user asks something that looks like they want status, trigger status.
    text = update.message.text.lower()
    if "status" in text or "explain" in text or "report" in text:
        await status(update, context)

if __name__ == '__main__':
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN environment variable not set.")
        print("Please export TELEGRAM_BOT_TOKEN='your_token_here'")
        exit(1)
        
    application = ApplicationBuilder().token(token).build()
    
    start_handler = CommandHandler('status', status)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    
    application.add_handler(start_handler)
    application.add_handler(message_handler)
    
    print("Bot is running...")
    application.run_polling()
