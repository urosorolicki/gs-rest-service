import time
import requests

URL = 'https://gs-rest-service-mphw.onrender.com/greeting'
INTERVAL = 30  # u sekundama
STATUS_UP = True

SLACK_WEBHOOK = 'https://hooks.slack.com/services/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'

def send_slack(message):
    payload = {"text": message}
    response = requests.post(SLACK_WEBHOOK, json=payload)
    if response.status_code != 200:
        print(f"Slack error: {response.status_code} - {response.text}")
    else:
        print("Slack poruka poslata uspešno")


def check_service():
    global STATUS_UP
    try:
        response = requests.get(URL, timeout=10)
        if response.status_code == 200:
            if not STATUS_UP:
                STATUS_UP = True
                msg = f":white_check_mark: Servis je ponovo UP na {URL}"
                print(msg)
                send_slack(msg)
            else:
                print(f"Servis je UP ({time.ctime()})")
        else:
            raise Exception(f"Status code: {response.status_code}")
    except Exception as e:
        if STATUS_UP:
            STATUS_UP = False
            msg = f":x: Servis je DOWN na {URL} - {e}"
            print(msg)
            send_slack(msg)
        else:
            print(f"Servis je i dalje DOWN ({time.ctime()}) - {e}")

if __name__ == "__main__":
    while True:
        check_service()
        time.sleep(INTERVAL)
