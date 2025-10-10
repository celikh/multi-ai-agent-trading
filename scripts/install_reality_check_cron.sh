#!/bin/bash
# Install Reality Check Cron Job
# Runs automated reality checks every 30 minutes

SCRIPT_DIR="/Users/hasancelik/Development/Projects/Multi AI Agent Trading/scripts"
LOG_DIR="/Users/hasancelik/Development/Projects/Multi AI Agent Trading/logs"

# Create cron job entry
CRON_ENTRY="*/30 * * * * /usr/bin/python3 '$SCRIPT_DIR/reality_check.py' >> '$LOG_DIR/reality_check_cron.log' 2>&1"

# Check if cron entry already exists
if crontab -l 2>/dev/null | grep -q "reality_check.py"; then
    echo "✅ Reality check cron job already exists"
    crontab -l | grep "reality_check.py"
else
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    echo "✅ Reality check cron job installed"
    echo "📅 Schedule: Every 30 minutes"
    echo "📝 Logs: $LOG_DIR/reality_check_cron.log"
fi

echo ""
echo "Current crontab:"
crontab -l | grep "reality_check.py"
