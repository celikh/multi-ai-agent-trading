#!/bin/bash
# Install systemd services for Multi-Agent Trading System
# This ensures all services auto-start after power outages

set -e

echo "=== Installing Trading System Services ==="

# macOS uses launchd, not systemd
# Create launchd plist files instead

LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$LAUNCH_AGENTS_DIR"

# Create API service
cat > "$LAUNCH_AGENTS_DIR/com.trading.api.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.trading.api</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/hasancelik/projects/multi-ai-agent-trading/venv/bin/uvicorn</string>
        <string>api.main:app</string>
        <string>--host</string>
        <string>0.0.0.0</string>
        <string>--port</string>
        <string>8000</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/hasancelik/projects/multi-ai-agent-trading</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/hasancelik/projects/multi-ai-agent-trading/logs/api.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/hasancelik/projects/multi-ai-agent-trading/logs/api.log</string>
</dict>
</plist>
EOF

# Create Dashboard service
cat > "$LAUNCH_AGENTS_DIR/com.trading.dashboard.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.trading.dashboard</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/bin/npm</string>
        <string>run</string>
        <string>start</string>
        <string>--</string>
        <string>-p</string>
        <string>3001</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/hasancelik/projects/multi-ai-agent-trading/trading-dashboard</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>NODE_ENV</key>
        <string>production</string>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/hasancelik/projects/multi-ai-agent-trading/logs/dashboard.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/hasancelik/projects/multi-ai-agent-trading/logs/dashboard.log</string>
</dict>
</plist>
EOF

# Create Agents service
cat > "$LAUNCH_AGENTS_DIR/com.trading.agents.plist" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.trading.agents</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/hasancelik/projects/multi-ai-agent-trading/start_all_agents.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/hasancelik/projects/multi-ai-agent-trading</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/hasancelik/projects/multi-ai-agent-trading/logs/agents-service.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/hasancelik/projects/multi-ai-agent-trading/logs/agents-service.log</string>
</dict>
</plist>
EOF

echo "✓ Created launchd service files"

# Load services
launchctl unload "$LAUNCH_AGENTS_DIR/com.trading.api.plist" 2>/dev/null || true
launchctl unload "$LAUNCH_AGENTS_DIR/com.trading.dashboard.plist" 2>/dev/null || true
launchctl unload "$LAUNCH_AGENTS_DIR/com.trading.agents.plist" 2>/dev/null || true

launchctl load "$LAUNCH_AGENTS_DIR/com.trading.api.plist"
launchctl load "$LAUNCH_AGENTS_DIR/com.trading.dashboard.plist"
launchctl load "$LAUNCH_AGENTS_DIR/com.trading.agents.plist"

echo "✓ Loaded all services"

echo ""
echo "=== Services Installed Successfully ==="
echo ""
echo "Services will now auto-start on boot and restart if they crash."
echo ""
echo "Manage services with:"
echo "  launchctl list | grep trading       # View status"
echo "  launchctl start com.trading.api     # Start service"
echo "  launchctl stop com.trading.api      # Stop service"
echo ""
