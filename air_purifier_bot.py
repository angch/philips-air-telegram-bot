from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import asyncio
import os
import logging
import shutil
import ast
import json
import google.generativeai as genai
import io
import matplotlib.pyplot as plt
import matplotlib
import traceback

# Use non-interactive backend for matplotlib
matplotlib.use('Agg')

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

def render_chart_thread_safe(data, chart_spec):
    """
    Renders the chart using Matplotlib OO interface based on a spec.
    Running this in a separate thread avoids blocking the event loop.
    `chart_spec` is a dictionary returned by Gemini describing visual elements.
    """
    try:
        # Create a new figure and axes object (thread-safe local state)
        fig, ax = plt.subplots(figsize=(8, 6))

        # Example Spec Handling:
        # {
        #   "title": "Air Quality Status",
        #   "pm25": {"value": 10, "color": "green", "label": "Excellent"},
        #   "iai": {"value": 1, "color": "blue"},
        #   "filters": [{"name": "Main", "pct": 100}, {"name": "Pre", "pct": 90}]
        # }

        # If Gemini returned a structure, use it. Otherwise, plot raw data.
        # Ideally, we should just plot the data ourselves if we know the schema,
        # but the task requires using "Nano Banana Pro" (Gemini) to generate the diagram.
        # So we trust Gemini's visual guidance (colors, labels).

        title = chart_spec.get('title', 'Air Quality Status')
        ax.set_title(title, fontsize=16)

        # Plotting logic based on spec
        # Let's assume a Bar Chart for simplicity and clarity as an infographic
        labels = []
        values = []
        colors = []

        # PM2.5
        if 'pm25' in chart_spec:
            item = chart_spec['pm25']
            labels.append(f"PM2.5: {item.get('value')} ({item.get('label', '')})")
            values.append(item.get('value', 0))
            colors.append(item.get('color', 'gray'))

        # IAI
        if 'iai' in chart_spec:
            item = chart_spec['iai']
            labels.append(f"IAI: {item.get('value')}")
            # Scale IAI to be visible? IAI is 1-12. PM2.5 is 0-500.
            # Maybe use two subplots? Or just normalize?
            # For simplicity, let's just plot bars.
            values.append(item.get('value', 0))
            colors.append(item.get('color', 'blue'))

        # Filters
        if 'filters' in chart_spec:
            for f in chart_spec['filters']:
                labels.append(f"{f.get('name')}: {f.get('pct')}%")
                values.append(f.get('pct', 0))
                colors.append('green' if f.get('pct', 0) > 20 else 'red')

        if labels:
            bars = ax.barh(labels, values, color=colors)
            ax.set_xlabel('Value / Percentage')

            # Add text labels on bars
            for bar in bars:
                width = bar.get_width()
                label_x_pos = width + 1
                ax.text(label_x_pos, bar.get_y() + bar.get_height()/2, f'{width}', va='center')

        plt.tight_layout()

        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        buf.seek(0)
        plt.close(fig) # Close the specific figure
        return buf.getvalue()

    except Exception as e:
        logging.error(f"Error rendering chart: {e}")
        plt.close('all') # Cleanup just in case
        return None

async def generate_status_diagram(data):
    """
    Generates a status diagram using Gemini to determine the visualization content,
    then renders it safely using Matplotlib in a thread.
    """
    try:
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            logging.error("GEMINI_API_KEY not set.")
            return None

        # Use simple configuration, assuming it handles single calls well.
        genai.configure(api_key=gemini_api_key)

        # Using gemini-1.5-flash
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt = f"""
        You are "Nano Banana Pro", an expert visual designer.
        Analyze this air purifier data: {data}
        
        Return a JSON object specifying how to visualize this status.
        Format:
        {{
            "title": "...",
            "pm25": {{"value": <number>, "color": "<hex/name>", "label": "<Good/Fair/Poor>"}},
            "iai": {{"value": <number>, "color": "<hex/name>"}},
            "filters": [
                {{"name": "Main Filter", "pct": <number>}},
                {{"name": "Pre-Filter", "pct": <number>}}
            ]
        }}

        Logic:
        - PM2.5 Color: Green (<12), Yellow (<35), Orange (<55), Red (>55)
        - Filter Pct: Calculate from fltsts1/flttotal1 (Main) and fltsts0/flttotal0 (Pre).

        Return ONLY valid JSON.
        """

        response = await model.generate_content_async(prompt)
        text = response.text

        # Clean markdown
        text = text.replace("```json", "").replace("```", "").strip()

        try:
            chart_spec = json.loads(text)
        except json.JSONDecodeError:
            logging.error(f"Failed to parse Gemini JSON: {text}")
            return None

        # Render in thread
        loop = asyncio.get_running_loop()
        image_data = await loop.run_in_executor(None, render_chart_thread_safe, data, chart_spec)

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
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    
    application.add_handler(start_handler)
    application.add_handler(message_handler)
    
    print("Bot is running...")
    application.run_polling()
