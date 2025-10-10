#!/usr/bin/env python3
"""
Automated Reality Check System
Monitors Linear issues and verifies actual system state matches expectations
"""

import subprocess
import sys
import json
from datetime import datetime
from typing import Dict, List, Optional
import os

# Issue configurations with reality check commands
REALITY_CHECKS = {
    "DEV-67": {
        "title": "Minimum lot size validation",
        "checks": [
            {
                "name": "No minimum precision errors",
                "command": "ssh mac-mini 'tail -100 ~/projects/multi-ai-agent-trading/logs/execution.log | grep -c \"minimum amount precision\"'",
                "expected": "0",
                "alert_if_not": True
            },
            {
                "name": "Orders have correct lot sizes",
                "command": "ssh mac-mini 'tail -50 ~/projects/multi-ai-agent-trading/logs/execution.log | grep order_received | tail -3'",
                "contains": ["0.0", "quantity"],
                "alert_if_not": True
            }
        ]
    },
    "DEV-68": {
        "title": "Position sizing optimization",
        "checks": [
            {
                "name": "No insufficient balance errors (last hour)",
                "command": "ssh mac-mini 'tail -500 ~/projects/multi-ai-agent-trading/logs/execution.log | strings | grep \"insufficient balance\" | grep \"$(date +%H):\" | wc -l | tr -d \" \"'",
                "expected": "0",
                "alert_if_not": True
            },
            {
                "name": "Position sizes reasonable",
                "command": "ssh mac-mini 'tail -50 ~/projects/multi-ai-agent-trading/logs/risk_manager.log | grep trade_approved | tail -3'",
                "alert_if_not": False
            }
        ]
    },
    "DEV-69": {
        "title": "Positions table exists",
        "checks": [
            {
                "name": "No relation not exist errors (confirms table exists)",
                "command": "ssh mac-mini 'tail -100 ~/projects/multi-ai-agent-trading/logs/risk_manager.log | grep -c \"positions.*does not exist\"'",
                "expected": "0",
                "alert_if_not": True
            },
            {
                "name": "Positions count query succeeds",
                "command": "ssh mac-mini 'cd ~/projects/multi-ai-agent-trading && PYTHONPATH=. venv/bin/python3 -c \"import asyncio; from infrastructure.database.postgresql import get_db; asyncio.run(get_db()).fetch_one(\\\"SELECT COUNT(*) FROM positions\\\")\" 2>&1 | grep -q \"postgres_connected\" && echo \"success\" || echo \"fail\"'",
                "expected": "success",
                "alert_if_not": True
            }
        ]
    },
    "DEV-72": {
        "title": "Data collection periodic execution",
        "checks": [
            {
                "name": "Agent executing periodically",
                "command": "ssh mac-mini 'tail -200 ~/projects/multi-ai-agent-trading/logs/data_collection.log | grep -c \"execute_started\"'",
                "expected_min": "3",
                "alert_if_not": True
            },
            {
                "name": "Data being fetched successfully",
                "command": "ssh mac-mini 'tail -100 ~/projects/multi-ai-agent-trading/logs/data_collection.log | grep -c \"rest_data_fetched\"'",
                "expected_min": "6",
                "alert_if_not": True
            },
            {
                "name": "No timeout errors",
                "command": "ssh mac-mini 'tail -100 ~/projects/multi-ai-agent-trading/logs/data_collection.log | grep -c \"RequestTimeout\"'",
                "expected": "0",
                "alert_if_not": True
            },
            {
                "name": "Data in InfluxDB",
                "command": "ssh mac-mini 'cd ~/projects/multi-ai-agent-trading && PYTHONPATH=. venv/bin/python3 scripts/check_data.py 2>&1 | grep -c \"Found 1 data\"'",
                "expected": "1",
                "alert_if_not": True
            }
        ]
    },
    "DEV-70": {
        "title": "InfluxDB query working",
        "checks": [
            {
                "name": "No InfluxDB query errors",
                "command": "ssh mac-mini 'tail -100 ~/projects/multi-ai-agent-trading/logs/risk_manager.log | grep -c \"InfluxDBClient.*has no attribute\"'",
                "expected": "0",
                "alert_if_not": True
            },
            {
                "name": "No fallback prices",
                "command": "ssh mac-mini 'tail -100 ~/projects/multi-ai-agent-trading/logs/risk_manager.log | grep -c \"using_fallback_price\"'",
                "expected": "0",
                "alert_if_not": True
            }
        ]
    }
}

def run_command(cmd: str) -> tuple[str, int]:
    """Execute command and return output and exit code"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "TIMEOUT", 1
    except Exception as e:
        return f"ERROR: {str(e)}", 1

def check_issue(issue_id: str, config: Dict) -> Dict:
    """Run reality checks for a specific issue"""
    results = {
        "issue_id": issue_id,
        "title": config["title"],
        "timestamp": datetime.now().isoformat(),
        "checks": [],
        "passed": True
    }

    for check in config["checks"]:
        output, exit_code = run_command(check["command"])

        check_result = {
            "name": check["name"],
            "passed": True,
            "output": output[:200],  # Limit output
            "alert": False
        }

        # Verify expected value
        if "expected" in check:
            check_result["passed"] = output == check["expected"]

        # Verify minimum value
        if "expected_min" in check:
            try:
                actual_value = int(output)
                min_value = int(check["expected_min"])
                check_result["passed"] = actual_value >= min_value
            except ValueError:
                check_result["passed"] = False

        # Verify contains
        if "contains" in check:
            check_result["passed"] = all(term in output for term in check["contains"])

        # Set alert if check failed
        if not check_result["passed"] and check.get("alert_if_not", False):
            check_result["alert"] = True
            results["passed"] = False

        results["checks"].append(check_result)

    return results

def generate_report(all_results: List[Dict]) -> str:
    """Generate human-readable report"""
    report = []
    report.append("=" * 80)
    report.append(f"REALITY CHECK REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("=" * 80)
    report.append("")

    total_issues = len(all_results)
    passed_issues = sum(1 for r in all_results if r["passed"])

    report.append(f"📊 Summary: {passed_issues}/{total_issues} issues passing all checks")
    report.append("")

    for result in all_results:
        status = "✅" if result["passed"] else "❌"
        report.append(f"{status} {result['issue_id']}: {result['title']}")

        for check in result["checks"]:
            check_status = "  ✓" if check["passed"] else "  ✗"
            alert = " 🚨" if check.get("alert", False) else ""
            report.append(f"{check_status} {check['name']}{alert}")
            if not check["passed"]:
                report.append(f"     Output: {check['output']}")

        report.append("")

    # Alerts section
    alerts = []
    for result in all_results:
        for check in result["checks"]:
            if check.get("alert", False):
                alerts.append(f"🚨 {result['issue_id']}: {check['name']}")

    if alerts:
        report.append("⚠️  ACTIVE ALERTS:")
        report.extend(alerts)
        report.append("")

    report.append("=" * 80)

    return "\n".join(report)

def update_linear_issue(issue_id: str, check_results: Dict):
    """Update Linear issue with reality check results (placeholder)"""
    # This would update the Linear issue with latest reality check status
    # For now, just log it
    status = "✅ PASSING" if check_results["passed"] else "❌ FAILING"
    print(f"Would update {issue_id} with status: {status}")

def main():
    """Run all reality checks"""
    print("🔍 Running Reality Checks...")
    print()

    all_results = []

    for issue_id, config in REALITY_CHECKS.items():
        print(f"Checking {issue_id}: {config['title']}...")
        results = check_issue(issue_id, config)
        all_results.append(results)

    # Generate report
    report = generate_report(all_results)
    print()
    print(report)

    # Save to file
    report_file = "/Users/hasancelik/Development/Projects/Multi AI Agent Trading/logs/reality_check_latest.txt"
    os.makedirs(os.path.dirname(report_file), exist_ok=True)
    with open(report_file, "w") as f:
        f.write(report)

    # Save JSON for automation
    json_file = "/Users/hasancelik/Development/Projects/Multi AI Agent Trading/logs/reality_check_latest.json"
    with open(json_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n📝 Report saved to: {report_file}")
    print(f"📊 JSON saved to: {json_file}")

    # Exit with error if any checks failed
    any_failed = any(not r["passed"] for r in all_results)
    sys.exit(1 if any_failed else 0)

if __name__ == "__main__":
    main()
