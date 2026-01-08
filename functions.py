import os
import smtplib
import time
import io
from email.message import EmailMessage
import pdfkit
import requests
from dotenv import load_dotenv
from datetime import datetime
from models import Orders
from database import Session
import platform
#TODO add wkhtmltopdf to path on server for this to run

load_dotenv()

SECRET = os.getenv("SECRET")
SECRET_URL = os.getenv("SECRET_URL3")
# ----------------------------
# System Detection helper
# ----------------------------

def get_pdfkit_config():
    """Return a pdfkit configuration object depending on OS."""
    system = platform.system()

    if system == "Windows":
        wkhtmltopdf_path = os.getenv("WINDOWS_PATH")
    else:
        wkhtmltopdf_path = os.getenv("LINUX_PATH")

    if not wkhtmltopdf_path or not os.path.exists(wkhtmltopdf_path):
        raise FileNotFoundError(f"wkhtmltopdf not found at {wkhtmltopdf_path}")

    return pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)



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
    print(url)

    print("[Invoice Wait] Max attempts reached. Giving up.")
    return None

# ----------------------------
# Generate PDF from HTML
# ----------------------------
# def generate_invoice(order_id):
#     """Generate PDF invoice using pdfkit / wkhtmltopdf."""
#     invoice_html = wait_for_invoice(order_id)  # your existing function
#     if not invoice_html:
#         return None
#
#     try:
#         # Linux path to wkhtmltopdf
#         config = pdfkit.configuration(wkhtmltopdf='/usr/bin/wkhtmltopdf')
#
#         pdf_bytes = pdfkit.from_string(invoice_html, False, configuration=config)
#         return pdf_bytes
#     except Exception as e:
#         print(f"[PDF Generation] Error creating PDF: {e}")
#         return None
# ----------------------------
# Updated PDF generation save locally commit path to DB
# ----------------------------
def generate_invoice(order_id):
    session = Session()  # create a DB session
    """Generate PDF invoice, save to local archive, update order.invoice_path, return file path."""
    # Load the order
    order = session.query(Orders).filter_by(order_id=order_id).first()
    if not order:
        print(f"[PDF Generation] Order {order_id} not found")
        return None

    # Get HTML for invoice
    invoice_html = wait_for_invoice(order_id)  # your existing function
    if not invoice_html:
        print(f"[PDF Generation] Invoice HTML not ready for order {order_id}")
        return None

    try:

        config = get_pdfkit_config()


        # Define path to save invoice
        base_dir = "/archives/invoices"  # adjust to your local archive folder
        # Use the order's actual date to determine folder structure
        order_date = order.order_date or datetime.utcnow()  # fallback in case it's missing
        year = order_date.strftime("%Y")
        month = order_date.strftime("%m")
        folder = os.path.join(base_dir, year, month)
        os.makedirs(folder, exist_ok=True)

        filename = f"INV-{order_id}.pdf"
        file_path = os.path.join(folder, filename)

        # Generate PDF and save
        pdfkit.from_string(invoice_html, file_path, configuration=config)

        # Update the order in the database
        order.invoice_path = file_path
        session.commit()

        print(f"[PDF Generation] Invoice saved for order {order_id} at {file_path}")
        return file_path

    except Exception as e:
        print(f"[PDF Generation] Error creating PDF for order {order_id}: {e}")
        session.rollback()
        return None

# ----------------------------
# Email sending helper
# ----------------------------
def send_email(user_email, subject, body, pdf=None, pdf_filename=None):
    """Send an email with optional PDF attachment."""
    try:
        LOGIN_EMAIL = os.getenv("CHOC_EMAIL")  # name@domain.com
        APP_PASSWORD = os.getenv("CHOC_PASSWORD")
        FROM_EMAIL = "no-reply@regalchocolate.in"  # Your alias

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = FROM_EMAIL  # Use the alias
        msg["To"] = user_email
        msg.set_content(body)

        if pdf:
            filename = pdf_filename or "attachment.pdf"
            msg.add_attachment(pdf, maintype="application", subtype="pdf", filename=filename)

        # Use port 587 with STARTTLS (like your working snippet)
        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login(LOGIN_EMAIL, APP_PASSWORD)  # Login with primary account
            smtp.send_message(msg)

        print("[Email] Sent successfully.")
        return True

    except Exception as e:
        print(f"[Email Error]: {e}")
        return False
# ----------------------------
# Send invoice email
# ----------------------------

def send_invoice(order_id, user_email, pdf_filename=None, session=None):
    """Send existing invoice PDF for given order via email."""

    # Load the order
    order = session.query(Orders).filter_by(order_id=order_id).first()
    if not order:
        print(f"[Send Invoice Error]: Order {order_id} not found in DB.")
        return False

    # Check if invoice exists
    if not order.invoice_path or not os.path.exists(order.invoice_path):
        print(f"[Send Invoice Error]: Invoice file not found for order {order_id}.")
        return False

    # Read PDF bytes from file
    try:
        with open(order.invoice_path, "rb") as f:
            pdf = f.read()
    except Exception as e:
        print(f"[Send Invoice Error]: Could not read invoice file: {e}")
        return False

    # Email content
    subject = f"Your Invoice - {order_id}"
    body = "Thanks for your order! Your invoice is attached."

    # Send email
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

def send_tracking(order_id, user_email, tracking_number, body=None, session=None):
    """Send tracking email with existing invoice attached."""

    # Load the order
    order = session.query(Orders).filter_by(order_id=order_id).first()
    if not order:
        print(f"[Send Tracking Error]: Order {order_id} not found in DB.")
        return False

    # Check if invoice exists
    if not order.invoice_path or not os.path.exists(order.invoice_path):
        print(f"[Send Tracking Error]: Invoice file not found for order {order_id}.")
        return False

    # Read PDF bytes from file
    try:
        with open(order.invoice_path, "rb") as f:
            pdf = f.read()
    except Exception as e:
        print(f"[Send Tracking Error]: Could not read invoice file: {e}")
        return False

    # Default email body
    subject = f"Your Order Has Shipped - Tracking: {tracking_number}"
    if body is None:
        body = (
            f"Hi,\n\nYour order {order_id} has been shipped!\n"
            f"Tracking number: {tracking_number}\n\n"
            "Your invoice is attached.\n\nThanks for shopping with us!"
        )

    # Send email with PDF attached
    return send_email(
        user_email=user_email,
        subject=subject,
        body=body,
        pdf=pdf,
        pdf_filename=f"Invoice_{order_id}.pdf"
    )


# generate_invoice("ORD1767531974")