import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import GMAIL_ADDRESS, GMAIL_APP_PASSWORD, GOOGLE_SHEET_ID


def send_notification(summary: str) -> str:
    """Send a Gmail notification with the pipeline summary."""
    sheet_url = f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}"
    body = f"{summary}\n\nFull list: {sheet_url}"

    # Extract subject line from first line of summary if it starts with "Subject:"
    lines = summary.strip().splitlines()
    if lines and lines[0].startswith("Subject:"):
        subject = lines[0].replace("Subject:", "").strip()
        body = "\n".join(lines[1:]).strip() + f"\n\nFull list: {sheet_url}"
    else:
        subject = "Lead Gen Pipeline — Daily Report"

    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = GMAIL_ADDRESS
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, GMAIL_ADDRESS, msg.as_string())
        return "Email notification sent."
    except Exception as e:
        return f"Email failed: {e}"
