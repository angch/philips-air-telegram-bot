# Philips Air Purifier Telegram Bot

This repository (`angch/philips-air-telegram-bot`) contains a Telegram bot that monitors the status of a Philips Air Purifier (specifically tested with AC2936) using `aioairctrl`.

## Features
- **Real-time Status**: Fetches live data from the device using `aioairctrl`.
- **Human-Readable Reports**: Parses technical metrics into a clean, HTML-formatted explanation.
- **Maintenance Alerts**: Clearly indicates when filters need cleaning or replacement.

## Prerequisites

1.  **Python 3.7+**
2.  **uv**: This project uses `uvx` to execute the air control command.
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
3.  **Telegram Bot Token**: Obtain one from @BotFather on Telegram.

## Quick Start

1.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the Bot**
    ```bash
    export TELEGRAM_BOT_TOKEN='your_token_here'
    python air_purifier_bot.py
    ```

## Usage

Send `/status` or ask "status" in your Telegram chat.
The bot will execute:
```bash
uvx aioairctrl -H 10.1.0.137 status
```
And reply with a detailed health report.

## Configuration

*   **IP Address**: The device IP is currently hardcoded to `10.1.0.137`. Edit `air_purifier_bot.py` to change this.

## Pushing to GitHub

To push this code to the new repository:

```bash
git remote add origin https://github.com/angch/philips-air-telegram-bot.git
git branch -M main
git push -u origin main
```
