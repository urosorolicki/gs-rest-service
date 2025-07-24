# deploy.py
import requests
import sys

SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/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"

def send_slack_notification(status: str):
    color = "#36a64f" if status == "success" else "#ff0000"
    message = {
        "attachments": [
            {
                "color": color,
                "title": "gs-rest-service Deploy Notification",
                "text": f"Deployment status: *{status.upper()}*",
                "fields": [
                    {
                        "title": "App URL",
                        "value": "https://gs-rest-service-mphw.onrender.com/greeting",
                        "short": False
                    }
                ]
            }
        ]
    }
    requests.post(SLACK_WEBHOOK_URL, json=message)

if __name__ == "__main__":
    status = sys.argv[1] if len(sys.argv) > 1 else "success"
    send_slack_notification(status)
