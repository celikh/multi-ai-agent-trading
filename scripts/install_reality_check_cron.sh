#!/bin/bash
# Install reality check cron job
# Runs every 30 minutes and saves results

PROJECT_DIR="$HOME/projects/multi-ai-agent-trading"
LOG_DIR="$PROJECT_DIR/logs"

# Create cron job entry
CRON_JOB="*/30 * * * * cd $PROJECT_DIR && venv/bin/python3 scripts/reality_check.py >> $LOG_DIR/reality_check_cron.log 2>&1"

# Check if cron job already exists
(crontab -l 2>/dev/null | grep -F "reality_check.py") && {
    echo "⚠️  Reality check cron job already exists"
    echo "Current crontab:"
    crontab -l | grep reality_check
    exit 0
}

# Add cron job
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "✅ Reality check cron job installed"
echo "📋 Schedule: Every 30 minutes"
echo "📝 Logs: $LOG_DIR/reality_check_cron.log"
echo "📊 Reports: $LOG_DIR/reality_check_latest.txt"
echo ""
echo "Current crontab:"
crontab -l | grep reality_check
