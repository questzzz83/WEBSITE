@echo off
:: start_bot.bat
:: Starts the Ink Telegram bot in the background
:: Place a shortcut to this file in:
:: C:\Users\Luis Paiva\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup

cd /d D:\Website
echo Starting Ink bot...
python telegram_bot.py >> D:\Website\logs\bot.log 2>&1
