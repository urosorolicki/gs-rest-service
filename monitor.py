import time
import requests
from datetime import datetime

URL = 'http://gs-rest-service-mphw.onrender.com/greeting'

INTERVAL = 30

STATUS_UP = True

SLACK_WEBHOOK = 'https://hooks.slack.com/services/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'

LOG_FILE = 'monitoring.log'


def log_status(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full_message = f"[{timestamp}] {message}"
    print(full_message)
    with open(LOG_FILE, 'a') as f:
        f.write(full_message + '\n')


def send_slack(message: str):
    payload = {"text": message}
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(SLACK_WEBHOOK, json=payload, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Slack error: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Slack request failed: {e}")


def check_service():
    global STATUS_UP
    try:
        response = requests.get(URL, timeout=10)
        if response.status_code == 200:
            if not STATUS_UP:
                STATUS_UP = True
                msg = f":white_check_mark: Servis je ponovo UP na {URL}"
                log_status(msg)
                send_slack(msg)
            else:
                print(f"Servis je UP ({datetime.now().strftime('%H:%M:%S')})")
        else:
            raise Exception(f"Status code: {response.status_code}")
    except Exception as e:
        if STATUS_UP:
            STATUS_UP = False
            msg = f":x: Servis je DOWN na {URL} - {e}"
            log_status(msg)
            send_slack(msg)
        else:
            print(f"Servis je i dalje DOWN ({datetime.now().strftime('%H:%M:%S')}) - {e}")


if __name__ == "__main__":
    log_status("Pokretanje monitoring skripte...")
    while True:
        check_service()
        time.sleep(INTERVAL)
