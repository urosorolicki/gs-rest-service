#!/usr/bin/env python3

"""
GS Rest Service Monitoring Tool
Author: DevOps Team
Description: Monitors the deployed gs-rest-service and sends notifications
"""

import argparse
import sys
import time
import requests
import logging
import json
import signal
import os
from datetime import datetime
from typing import Optional
import threading
from pathlib import Path


class ServiceMonitor:
    def __init__(self, config: dict):
        self.config = config
        self.service_status = "unknown"
        self.consecutive_failures = 0
        self.consecutive_successes = 0
        self.last_notification = ""
        self.shutdown_event = threading.Event()
        
        # Setup logging
        self.setup_logging()
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        
        # Create log directory if it doesn't exist
        log_file = Path(self.config['log_file'])
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(self.config['log_file']),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.shutdown_event.set()
    
    def send_slack_notification(self, status: str, message: str, color: str):
        """Send notification to Slack"""
        if self.config['no_slack'] or not self.config['slack_webhook_url']:
            return
        
        payload = {
            "channel": self.config['slack_channel'],
            "attachments": [
                {
                    "color": color,
                    "title": "GS Rest Service Monitor Alert",
                    "text": message,
                    "fields": [
                        {
                            "title": "Service URL",
                            "value": self.config['service_url'],
                            "short": True
                        },
                        {
                            "title": "Status", 
                            "value": status,
                            "short": True
                        },
                        {
                            "title": "Timestamp",
                            "value": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            "short": True
                        }
                    ]
                }
            ]
        }
        
        try:
            response = requests.post(
                self.config['slack_webhook_url'],
                json=payload,
                timeout=10
            )
            response.raise_for_status()
        except Exception as e:
            self.logger.warning(f"Failed to send Slack notification: {e}")
    
    def check_service(self) -> bool:
        """Check if service is responding"""
        for attempt in range(1, self.config['retries'] + 1):
            self.logger.info(f"Health check attempt {attempt}/{self.config['retries']} for {self.config['service_url']}")
            
            try:
                response = requests.get(
                    self.config['service_url'],
                    timeout=self.config['timeout']
                )
                
                if response.status_code == 200:
                    return True
                else:
                    self.logger.warning(f"Service returned status code: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request failed: {e}")
            
            if attempt < self.config['retries']:
                self.logger.warning("Retrying in 5 seconds...")
                time.sleep(5)
        
        return False
    
    def handle_status_change(self, new_status: str):
        """Handle service status changes"""
        old_status = self.service_status
        
        if new_status != old_status:
            if new_status == "up":
                self.logger.info("Service is now UP - recovered from failure")
                if old_status == "down":
                    self.send_slack_notification(
                        "UP", 
                        "✅ Service has recovered and is now responding normally", 
                        "good"
                    )
                    self.last_notification = "recovery"
                self.consecutive_failures = 0
                self.consecutive_successes += 1
            else:
                self.logger.error("Service is now DOWN - not responding")
                if old_status in ["up", "unknown"]:
                    self.send_slack_notification(
                        "DOWN",
                        "🚨 Service is not responding and appears to be down",
                        "danger"
                    )
                    self.last_notification = "failure"
                self.consecutive_successes = 0
                self.consecutive_failures += 1
            
            self.service_status = new_status
        else:
            if new_status == "up":
                self.consecutive_successes += 1
                self.consecutive_failures = 0
            else:
                self.consecutive_failures += 1
                self.consecutive_successes = 0
    
    def monitor_loop(self):
        """Main monitoring loop"""
        self.logger.info(f"Starting monitoring of {self.config['service_url']}")
        self.logger.info(f"Check interval: {self.config['check_interval']}s, "
                        f"Timeout: {self.config['timeout']}s, "
                        f"Retries: {self.config['retries']}")
        
        while not self.shutdown_event.is_set():
            try:
                if self.check_service():
                    self.logger.info("Service is responding normally")
                    self.handle_status_change("up")
                else:
                    self.logger.error("Service is not responding")
                    self.handle_status_change("down")
                
                self.logger.info(f"Status: {self.service_status}, "
                               f"Consecutive successes: {self.consecutive_successes}, "
                               f"Consecutive failures: {self.consecutive_failures}")
                
                if self.config['check_once']:
                    break
                
                # Wait for next check or shutdown signal
                self.shutdown_event.wait(timeout=self.config['check_interval'])
                
            except KeyboardInterrupt:
                self.logger.info("Monitoring interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Unexpected error in monitoring loop: {e}")
                time.sleep(self.config['check_interval'])
        
        self.logger.info("Monitoring stopped")
    
    def start(self):
        """Start monitoring"""
        if self.config['daemon_mode']:
            self.run_as_daemon()
        else:
            self.monitor_loop()
    
    def run_as_daemon(self):
        """Run as daemon process"""
        pid_file = self.config['pid_file']
        
        # Check if already running
        if os.path.exists(pid_file):
            try:
                with open(pid_file, 'r') as f:
                    old_pid = int(f.read().strip())
                
                # Check if process is still running
                try:
                    os.kill(old_pid, 0)
                    self.logger.error(f"Monitor is already running (PID: {old_pid})")
                    sys.exit(1)
                except OSError:
                    # Process not running, remove stale PID file
                    os.remove(pid_file)
            except (ValueError, FileNotFoundError):
                pass
        
        # Fork process
        try:
            pid = os.fork()
            if pid > 0:
                # Parent process
                with open(pid_file, 'w') as f:
                    f.write(str(pid))
                self.logger.info(f"Monitor daemon started (PID: {pid})")
                sys.exit(0)
        except OSError as e:
            self.logger.error(f"Failed to fork daemon: {e}")
            sys.exit(1)
        
        # Child process
        os.setsid()
        os.umask(0)
        
        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Start monitoring
        try:
            self.monitor_loop()
        finally:
            # Clean up PID file
            try:
                os.remove(pid_file)
            except FileNotFoundError:
                pass


def manage_daemon(action: str, pid_file: str):
    """Manage daemon process"""
    if action == "stop":
        if os.path.exists(pid_file):
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                os.kill(pid, signal.SIGTERM)
                time.sleep(2)
                
                # Check if process stopped
                try:
                    os.kill(pid, 0)
                    print(f"Force killing process {pid}")
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
                
                os.remove(pid_file)
                print(f"Monitor daemon stopped (PID: {pid})")
            except (ValueError, FileNotFoundError, OSError) as e:
                print(f"Error stopping daemon: {e}")
        else:
            print("PID file not found")
    
    elif action == "status":
        if os.path.exists(pid_file):
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                try:
                    os.kill(pid, 0)
                    print(f"Monitor daemon is running (PID: {pid})")
                except OSError:
                    print("Monitor daemon is not running (stale PID file)")
                    os.remove(pid_file)
            except (ValueError, FileNotFoundError):
                print("Invalid PID file")
        else:
            print("Monitor daemon is not running")
    
    elif action == "restart":
        manage_daemon("stop", pid_file)
        time.sleep(2)
        # Restart will be handled by returning to main


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='GS Rest Service Monitoring Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 monitor.py --url http://localhost:777/greeting
  python3 monitor.py --url http://myserver.com:777/greeting --interval 60 --daemon
  python3 monitor.py --url http://192.168.1.100:777/greeting --slack-webhook https://hooks.slack.com/...
  
Daemon management:
  python3 monitor.py --daemon start --url http://localhost:777/greeting
  python3 monitor.py --daemon stop
  python3 monitor.py --daemon status
  python3 monitor.py --daemon restart --url http://localhost:777/greeting
        """
    )
    
    parser.add_argument('-u', '--url', help='Service URL to monitor (required)')
    parser.add_argument('-i', '--interval', type=int, default=30, help='Check interval in seconds (default: 30)')
    parser.add_argument('-t', '--timeout', type=int, default=10, help='Request timeout in seconds (default: 10)')
    parser.add_argument('-r', '--retries', type=int, default=3, help='Number of retries before marking as failed (default: 3)')
    parser.add_argument('-l', '--log-file', default='monitor.log', help='Log file path (default: monitor.log)')
    parser.add_argument('-s', '--slack-webhook', help='Slack webhook URL for notifications')
    parser.add_argument('-c', '--slack-channel', default='#gs-rest-service-monitor', help='Slack channel name (default: #gs-rest-service-monitor)')
    parser.add_argument('--daemon', choices=['start', 'stop', 'status', 'restart'], help='Daemon management')
    parser.add_argument('--pid-file', default='monitor.pid', help='PID file for daemon mode (default: monitor.pid)')
    parser.add_argument('--check-once', action='store_true', help='Perform single check and exit')
    parser.add_argument('--no-slack', action='store_true', help='Disable Slack notifications')
    
    return parser.parse_args()


def main():
    """Main function"""
    args = parse_arguments()
    
    # Handle daemon management
    if args.daemon in ['stop', 'status']:
        manage_daemon(args.daemon, args.pid_file)
        return
    
    if args.daemon == 'restart':
        manage_daemon('stop', args.pid_file)
        # Continue to restart
    
    # Validate required arguments
    if not args.url:
        print("Error: Service URL must be specified with --url")
        sys.exit(1)
    
    # Prepare configuration
    config = {
        'service_url': args.url,
        'check_interval': args.interval,
        'timeout': args.timeout,
        'retries': args.retries,
        'log_file': args.log_file,
        'slack_webhook_url': args.slack_webhook,
        'slack_channel': args.slack_channel,
        'daemon_mode': args.daemon == 'start',
        'pid_file': args.pid_file,
        'check_once': args.check_once,
        'no_slack': args.no_slack or not args.slack_webhook
    }
    
    # Print configuration
    print("GS Rest Service Monitoring Tool Starting...")
    print("Monitoring Configuration:")
    print(f"  Service URL: {config['service_url']}")
    print(f"  Check Interval: {config['check_interval']}s")
    print(f"  Timeout: {config['timeout']}s")
    print(f"  Retries: {config['retries']}")
    print(f"  Log File: {config['log_file']}")
    print(f"  Slack Notifications: {'Enabled' if not config['no_slack'] else 'Disabled'}")
    print(f"  Daemon Mode: {config['daemon_mode']}")
    
    # Start monitoring
    try:
        monitor = ServiceMonitor(config)
        monitor.start()
    except KeyboardInterrupt:
        print("\nMonitoring interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
