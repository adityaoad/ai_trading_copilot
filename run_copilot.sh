#!/bin/zsh
# run_copilot.sh — starts daily scan + monitor
# Adjust these paths for your machine if your folder is elsewhere.

PROJECT_DIR="$HOME/Documents/ai_trading_copilot"
PY="$PROJECT_DIR/.venv/bin/python"

# --- Environment for Telegram (OPTIONAL: you can hardcode or rely on ~/.zshrc exports)
export TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN}"
export TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID}"

# --- go to project
cd "$PROJECT_DIR" || exit 1

# --- build daily watchlist (risk per trade: $10; tweak as you like)
"$PY" daily_watchlist.py --auto --risk 10 >> "$PROJECT_DIR/logs/runner.log" 2>&1

# --- start the monitor for the day; polling every 10 minutes
# NOTE: launchd will keep this process alive as long as the Mac is on and your user is logged in.
"$PY" monitor_entries.py --interval 10 >> "$PROJECT_DIR/logs/monitor.log" 2>&1

