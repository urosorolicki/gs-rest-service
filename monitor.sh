#!/bin/bash

# GS Rest Service Monitoring Tool
# Author: DevOps Team
# Description: Monitors the deployed gs-rest-service and sends notifications

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
DEFAULT_CHECK_INTERVAL=30
DEFAULT_TIMEOUT=10
DEFAULT_RETRIES=3
DEFAULT_LOG_FILE="$SCRIPT_DIR/monitor.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Slack webhook URL (set this via environment variable or config file)
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
SLACK_CHANNEL="${SLACK_CHANNEL:-#gs-rest-service-monitor}"

# Global variables
SERVICE_STATUS="unknown"
CONSECUTIVE_FAILURES=0
CONSECUTIVE_SUCCESSES=0
LAST_NOTIFICATION=""

# Logging function
log() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local message="[$timestamp] $1"
    echo -e "${BLUE}$message${NC}"
    echo "$message" >> "$LOG_FILE"
}

error() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local message="[$timestamp] ERROR: $1"
    echo -e "${RED}$message${NC}" >&2
    echo "$message" >> "$LOG_FILE"
}

success() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local message="[$timestamp] SUCCESS: $1"
    echo -e "${GREEN}$message${NC}"
    echo "$message" >> "$LOG_FILE"
}

warning() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local message="[$timestamp] WARNING: $1"
    echo -e "${YELLOW}$message${NC}"
    echo "$message" >> "$LOG_FILE"
}

# Help function
show_help() {
    cat << EOF
GS Rest Service Monitoring Tool

Usage: $0 [OPTIONS]

Options:
    -h, --help                  Show this help message
    -u, --url URL              Service URL to monitor (required)
    -i, --interval SECONDS     Check interval in seconds (default: $DEFAULT_CHECK_INTERVAL)
    -t, --timeout SECONDS      Request timeout in seconds (default: $DEFAULT_TIMEOUT)
    -r, --retries COUNT        Number of retries before marking as failed (default: $DEFAULT_RETRIES)
    -l, --log-file FILE        Log file path (default: $DEFAULT_LOG_FILE)
    -s, --slack-webhook URL    Slack webhook URL for notifications
    -c, --slack-channel NAME   Slack channel name (default: $SLACK_CHANNEL)
    --daemon                   Run as daemon (background process)
    --pid-file FILE            PID file for daemon mode
    --check-once               Perform single check and exit
    --no-slack                 Disable Slack notifications

Examples:
    $0 --url http://localhost:777/greeting
    $0 --url http://myserver.com:777/greeting --interval 60 --daemon
    $0 --url http://192.168.1.100:777/greeting --slack-webhook https://hooks.slack.com/...

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -u|--url)
                SERVICE_URL="$2"
                shift 2
                ;;
            -i|--interval)
                CHECK_INTERVAL="$2"
                shift 2
                ;;
            -t|--timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -r|--retries)
                RETRIES="$2"
                shift 2
                ;;
            -l|--log-file)
                LOG_FILE="$2"
                shift 2
                ;;
            -s|--slack-webhook)
                SLACK_WEBHOOK_URL="$2"
                shift 2
                ;;
            -c|--slack-channel)
                SLACK_CHANNEL="$2"
                shift 2
                ;;
            --daemon)
                DAEMON_MODE=true
                shift
                ;;
            --pid-file)
                PID_FILE="$2"
                shift 2
                ;;
            --check-once)
                CHECK_ONCE=true
                shift
                ;;
            --no-slack)
                NO_SLACK=true
                shift
                ;;
            *)
                error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

# Set defaults
set_defaults() {
    CHECK_INTERVAL="${CHECK_INTERVAL:-$DEFAULT_CHECK_INTERVAL}"
    TIMEOUT="${TIMEOUT:-$DEFAULT_TIMEOUT}"
    RETRIES="${RETRIES:-$DEFAULT_RETRIES}"
    LOG_FILE="${LOG_FILE:-$DEFAULT_LOG_FILE}"
    DAEMON_MODE="${DAEMON_MODE:-false}"
    CHECK_ONCE="${CHECK_ONCE:-false}"
    NO_SLACK="${NO_SLACK:-false}"
    PID_FILE="${PID_FILE:-$SCRIPT_DIR/monitor.pid}"
}

# Validate configuration
validate_config() {
    if [ -z "$SERVICE_URL" ]; then
        error "Service URL must be specified with --url"
        exit 1
    fi
    
    if [ "$NO_SLACK" = false ] && [ -z "$SLACK_WEBHOOK_URL" ]; then
        warning "Slack webhook URL not provided. Slack notifications will be disabled."
        NO_SLACK=true
    fi
    
    # Create log directory if it doesn't exist
    local log_dir=$(dirname "$LOG_FILE")
    mkdir -p "$log_dir"
}

# Send Slack notification
send_slack_notification() {
    local status="$1"
    local message="$2"
    local color="$3"
    
    if [ "$NO_SLACK" = true ] || [ -z "$SLACK_WEBHOOK_URL" ]; then
        return 0
    fi
    
    local payload=$(cat << EOF
{
    "channel": "$SLACK_CHANNEL",
    "attachments": [
        {
            "color": "$color",
            "title": "GS Rest Service Monitor Alert",
            "text": "$message",
            "fields": [
                {
                    "title": "Service URL",
                    "value": "$SERVICE_URL",
                    "short": true
                },
                {
                    "title": "Status",
                    "value": "$status",
                    "short": true
                },
                {
                    "title": "Timestamp",
                    "value": "$(date '+%Y-%m-%d %H:%M:%S')",
                    "short": true
                }
            ]
        }
    ]
}
EOF
)
    
    curl -s -X POST -H 'Content-type: application/json' \
        --data "$payload" \
        "$SLACK_WEBHOOK_URL" > /dev/null 2>&1 || \
        warning "Failed to send Slack notification"
}

# Check service health
check_service() {
    local attempt=1
    local success=false
    
    while [ $attempt -le $RETRIES ]; do
        log "Health check attempt $attempt/$RETRIES for $SERVICE_URL"
        
        if curl -f -s --max-time "$TIMEOUT" "$SERVICE_URL" > /dev/null 2>&1; then
            success=true
            break
        fi
        
        if [ $attempt -lt $RETRIES ]; then
            warning "Attempt $attempt failed, retrying in 5 seconds..."
            sleep 5
        fi
        
        ((attempt++))
    done
    
    return $success
}

# Handle status change
handle_status_change() {
    local new_status="$1"
    local old_status="$SERVICE_STATUS"
    
    if [ "$new_status" != "$old_status" ]; then
        if [ "$new_status" = "up" ]; then
            success "Service is now UP - recovered from failure"
            if [ "$old_status" = "down" ]; then
                send_slack_notification "UP" "✅ Service has recovered and is now responding normally" "good"
                LAST_NOTIFICATION="recovery"
            fi
            CONSECUTIVE_FAILURES=0
            CONSECUTIVE_SUCCESSES=$((CONSECUTIVE_SUCCESSES + 1))
        else
            error "Service is now DOWN - not responding"
            if [ "$old_status" = "up" ] || [ "$old_status" = "unknown" ]; then
                send_slack_notification "DOWN" "🚨 Service is not responding and appears to be down" "danger"
                LAST_NOTIFICATION="failure"
            fi
            CONSECUTIVE_SUCCESSES=0
            CONSECUTIVE_FAILURES=$((CONSECUTIVE_FAILURES + 1))
        fi
        
        SERVICE_STATUS="$new_status"
    else
        if [ "$new_status" = "up" ]; then
            CONSECUTIVE_SUCCESSES=$((CONSECUTIVE_SUCCESSES + 1))
            CONSECUTIVE_FAILURES=0
        else
            CONSECUTIVE_FAILURES=$((CONSECUTIVE_FAILURES + 1))
            CONSECUTIVE_SUCCESSES=0
        fi
    fi
}

# Monitor loop
monitor_loop() {
    log "Starting monitoring of $SERVICE_URL"
    log "Check interval: ${CHECK_INTERVAL}s, Timeout: ${TIMEOUT}s, Retries: $RETRIES"
    
    while true; do
        if check_service; then
            log "Service is responding normally"
            handle_status_change "up"
        else
            error "Service is not responding"
            handle_status_change "down"
        fi
        
        log "Status: $SERVICE_STATUS, Consecutive successes: $CONSECUTIVE_SUCCESSES, Consecutive failures: $CONSECUTIVE_FAILURES"
        
        if [ "$CHECK_ONCE" = true ]; then
            break
        fi
        
        sleep "$CHECK_INTERVAL"
    done
}

# Daemon functions
start_daemon() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        error "Monitor is already running (PID: $(cat "$PID_FILE"))"
        exit 1
    fi
    
    log "Starting monitor daemon..."
    nohup "$0" "${ORIGINAL_ARGS[@]}" --no-daemon > "$LOG_FILE.daemon" 2>&1 &
    local pid=$!
    echo $pid > "$PID_FILE"
    success "Monitor daemon started (PID: $pid)"
}

stop_daemon() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid"
            rm -f "$PID_FILE"
            success "Monitor daemon stopped (PID: $pid)"
        else
            warning "Monitor daemon not running"
            rm -f "$PID_FILE"
        fi
    else
        warning "PID file not found"
    fi
}

status_daemon() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            log "Monitor daemon is running (PID: $pid)"
        else
            warning "Monitor daemon is not running (stale PID file)"
            rm -f "$PID_FILE"
        fi
    else
        log "Monitor daemon is not running"
    fi
}

# Signal handlers
cleanup() {
    log "Received termination signal, shutting down..."
    if [ -f "$PID_FILE" ]; then
        rm -f "$PID_FILE"
    fi
    exit 0
}

# Main function
main() {
    # Store original arguments for daemon mode
    ORIGINAL_ARGS=("$@")
    
    parse_args "$@"
    set_defaults
    validate_config
    
    # Set up signal handlers
    trap cleanup SIGTERM SIGINT
    
    # Handle daemon operations
    if [ "$DAEMON_MODE" = true ]; then
        case "${1:-start}" in
            start)
                start_daemon
                ;;
            stop)
                stop_daemon
                ;;
            restart)
                stop_daemon
                sleep 2
                start_daemon
                ;;
            status)
                status_daemon
                ;;
            *)
                start_daemon
                ;;
        esac
        exit 0
    fi
    
    # Add --no-daemon flag for actual monitoring
    if [[ ! " ${ORIGINAL_ARGS[*]} " =~ " --no-daemon " ]]; then
        ORIGINAL_ARGS+=("--no-daemon")
    fi
    
    # Start monitoring
    monitor_loop
}

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
