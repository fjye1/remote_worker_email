import os
import smtplib
import time
import io
from email.message import EmailMessage
from xhtml2pdf import pisa
import requests
from dotenv import load_dotenv

load_dotenv()

SECRET = os.getenv("SECRET")
SECRET_URL = os.getenv("SECRET_URL")




# ----------------------------
# Wait for invoice HTML
# ----------------------------
def wait_for_invoice(order_id, timeout=10, wait_seconds=4 * 60, max_attempts=30):
    """
    Poll the invoice URL until it returns 200 or max_attempts reached.
    Returns HTML string or None if not available.
    """
    url = f"{SECRET_URL}/{order_id}/{SECRET}"
    for attempt in range(max_attempts):
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code == 200:
                return response.text
            else:
                print(f"[Invoice Wait] Got {response.status_code}, retrying in {wait_seconds//60} mins...")
        except requests.RequestException as e:
            print(f"[Invoice Wait] Request failed: {e}, retrying in {wait_seconds//60} mins...")

        time.sleep(wait_seconds)

    print("[Invoice Wait] Max attempts reached. Giving up.")
    return None

# ----------------------------
# Generate PDF from HTML
# ----------------------------
def generate_invoice(order_id):
    """Wait for invoice page to be available, then return PDF bytes."""
    invoice_html = wait_for_invoice(order_id)
    if not invoice_html:
        return None

    with io.BytesIO() as pdf_stream:
        pisa_status = pisa.CreatePDF(invoice_html, dest=pdf_stream)
        if pisa_status.err:
            print("[PDF Generation] Error creating PDF.")
            return None
        return pdf_stream.getvalue()

# ----------------------------
# Email sending helper
# ----------------------------
def send_email(user_email, subject, body, pdf=None, pdf_filename=None):
    """Send an email with optional PDF attachment."""
    try:
        CHOC_EMAIL = os.getenv("CHOC_EMAIL")
        CHOC_PASSWORD = os.getenv("CHOC_PASSWORD")

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = CHOC_EMAIL
        msg["To"] = user_email
        msg.set_content(body)

        if pdf:
            filename = pdf_filename or "attachment.pdf"
            msg.add_attachment(pdf, maintype="application", subtype="pdf", filename=filename)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(CHOC_EMAIL, CHOC_PASSWORD)
            smtp.send_message(msg)

        print("[Email] Sent successfully.")
        return True

    except Exception as e:
        print(f"[Email Error]: {e}")
        return False

# ----------------------------
# Send invoice email
# ----------------------------

def send_invoice(order_id, user_email, pdf_filename=None):
    """Generate PDF for given order and send it via email."""
    pdf = generate_invoice(order_id)
    if not pdf:
        print("[Send Invoice Error]: Could not generate invoice PDF.")
        return False

    subject = f"Your Invoice - {order_id}"
    body = "Thanks for your order! Your invoice is attached."

    return send_email(
        user_email=user_email,
        subject=subject,
        body=body,
        pdf=pdf,
        pdf_filename=pdf_filename or f"Invoice_{order_id}.pdf"
    )

# ----------------------------
# Send tracking email
# ----------------------------

def send_tracking(order_id, user_email, tracking_number, body=None):
    """Send tracking email with invoice attached."""
    pdf = generate_invoice(order_id)
    if not pdf:
        print("[Send Tracking Error]: Could not generate invoice PDF.")
        return False

    subject = f"Your Order Has Shipped - Tracking: {tracking_number}"
    if body is None:
        body = (
            f"Hi,\n\nYour order {order_id} has been shipped!\n"
            f"Tracking number: {tracking_number}\n\n"
            "Your invoice is attached.\n\nThanks for shopping with us!"
        )

    return send_email(
        user_email=user_email,
        subject=subject,
        body=body,
        pdf=pdf,
        pdf_filename=f"Invoice_{order_id}.pdf"
    )
