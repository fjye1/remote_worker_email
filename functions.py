import os
import platform
import smtplib
import time
from datetime import datetime
from email.message import EmailMessage

import pdfkit
import requests
from dotenv import load_dotenv

from models import Orders

# TODO add wkhtmltopdf to path on server for this to run

load_dotenv()

INTERNAL_API_TOKEN = os.getenv("INTERNAL_API_TOKEN")
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

# def wait_for_invoice(order_id, timeout=10, wait_seconds=4 * 60, max_attempts=30):
#     """
#     Poll the invoice URL until it returns 200 or max_attempts reached.
#     Returns HTML string or None if not available.
#     """
#     url = f"{SECRET_URL}/{order_id}"
#
#     headers = {
#         "Authorization": f"Bearer {INTERNAL_API_TOKEN}"
#     }
#
#     for attempt in range(max_attempts):
#         try:
#             response = requests.get(url, headers=headers, timeout=timeout)
#
#             if response.status_code == 200:
#                 return response.text
#             else:
#                 print(f"[Invoice Wait] Got {response.status_code}, retrying in {wait_seconds//60} mins...")
#
#         except requests.RequestException as e:
#             print(f"[Invoice Wait] Request failed: {e}, retrying in {wait_seconds//60} mins...")
#
#         time.sleep(wait_seconds)
#
#     print("[Invoice Wait] Max attempts reached. Giving up.")
#     return None
# ----------------------------
# Return Internal Invoice JSON
# ----------------------------
def get_internal_invoice_JSON(order_id, timeout=10, wait_seconds=4 * 60, max_attempts=30):
    """
    Fetch invoice JSON from the online server with retry logic.
    Polls until 200 response or max_attempts reached.
    Returns a Python dict or None if not available.
    """
    url = f"{os.getenv('SECRET_URL3')}/{order_id}/json"
    headers = {
        "Authorization": f"Bearer {os.getenv('INTERNAL_API_TOKEN')}"
    }

    for attempt in range(max_attempts):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)

            if resp.status_code == 200:
                return resp.json()
            else:
                print(
                    f"[Invoice Wait] Attempt {attempt + 1}/{max_attempts}: Got {resp.status_code}, retrying in {wait_seconds // 60} mins...")

        except requests.RequestException as e:
            print(
                f"[Invoice Wait] Attempt {attempt + 1}/{max_attempts}: Request failed: {e}, retrying in {wait_seconds // 60} mins...")

        # Don't sleep after the last attempt
        if attempt < max_attempts - 1:
            time.sleep(wait_seconds)

    print(f"[Invoice Wait] Max attempts ({max_attempts}) reached for order {order_id}. Giving up.")
    return None


# ----------------------------
# Send invoice body
# ----------------------------
def build_invoice_email(invoice):
    """Build HTML email body from internal invoice JSON that matches the site design."""

    # Build items rows
    items_html = "".join(
        f"""
        <tr>
            <td align="center" style="padding: 12px; border: 1px solid #dee2e6;">
                <img src="{item.get('product_image')}"
                     alt="{item['product_name']}"
                     style="max-width: 100px; height: 100px; object-fit: cover; 
                            border: 1px solid #dee2e6; border-radius: 4px;">
            </td>
            <td style="padding: 12px; border: 1px solid #dee2e6;">{item['product_name']}</td>
            <td align="center" style="padding: 12px; border: 1px solid #dee2e6;">{item.get('box_id', '-')}</td>
            <td align="center" style="padding: 12px; border: 1px solid #dee2e6;">{item.get('shipment_id', '-')}</td>
            <td align="center" style="padding: 12px; border: 1px solid #dee2e6;">{item['quantity']}</td>
            <td align="right" style="padding: 12px; border: 1px solid #dee2e6;">&#8377;{item['price_at_purchase']:.2f}</td>
            <td align="right" style="padding: 12px; border: 1px solid #dee2e6;">&#8377;{item['line_total']:.2f}</td>
        </tr>
        """
        for item in invoice["items"]
    )

    shipping = invoice["shipping_address"]

    return f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
      </head>
      <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; 
                    margin: 0; padding: 20px; background-color: #f8f9fa;">

        <div style="max-width: 900px; margin: 0 auto; background: white; padding: 20px;">

          <!-- Header -->
<div style="background: linear-gradient(135deg, #afc08f 0%, #FCE7A3 100%); 
            padding: 30px; border-radius: 8px 8px 0 0; margin-bottom: 30px;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td style="width: 150px; vertical-align: middle;">
        <img src="https://regalchocolate.in/static/images/Logo_small.png"
             alt="Site Logo"
             width="150" height="150" 
             style="border-radius: 8px; display: block; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
      </td>
      <td style="padding-left: 30px; vertical-align: middle;">
        <h1 style="margin: 0 0 8px 0; font-size: 32px; font-weight: 600; color: #2d3748;">Invoice</h1>
        <p style="margin: 0 0 16px 0; font-size: 16px; color: #4a5568;">Thank you for your order!</p>
        <div style="background: rgba(255,255,255,0.5); padding: 16px; border-radius: 6px; backdrop-filter: blur(10px);">
          <p style="margin: 0 0 6px 0; color: #2d3748;"><strong>Order ID:</strong> {invoice['order_id']}</p>
          <p style="margin: 0 0 6px 0; color: #2d3748;"><strong>Date:</strong> {invoice['created_at_formatted']}</p>
          <p style="margin: 0; color: #2d3748;"><strong>Status:</strong> <span style="text-transform: capitalize;">{invoice['status']}</span></p>
        </div>
      </td>
    </tr>
  </table>
</div>

          <!-- Shipping Address -->
          <h4 style="margin: 0 0 12px 0; font-size: 20px; font-weight: 500;">Shipping Address</h4>
          <p style="margin: 0 0 20px 0; line-height: 1.6;">
            {shipping['street']}<br>
            {shipping['city']}, {shipping['postcode']}
          </p>

          <hr style="border: none; border-top: 1px solid #dee2e6; margin: 20px 0;">

          <!-- Items Table -->
          <h4 style="margin: 0 0 16px 0; font-size: 20px; font-weight: 500;">Items</h4>
          <div style="border: 1px solid #dee2e6; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 20px;">
            <div style="padding: 12px;">
              <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse: collapse;">
                <thead>
                  <tr style="background-color: #f8f9fa;">
                    <th align="center" style="padding: 12px; border: 1px solid #dee2e6; font-weight: 600; width: 120px;">Image</th>
                    <th align="left" style="padding: 12px; border: 1px solid #dee2e6; font-weight: 600;">Product</th>
                    <th align="center" style="padding: 12px; border: 1px solid #dee2e6; font-weight: 600;">Box ID</th>
                    <th align="center" style="padding: 12px; border: 1px solid #dee2e6; font-weight: 600;">Shipment ID</th>
                    <th align="center" style="padding: 12px; border: 1px solid #dee2e6; font-weight: 600;">Qty</th>
                    <th align="right" style="padding: 12px; border: 1px solid #dee2e6; font-weight: 600;">Price</th>
                    <th align="right" style="padding: 12px; border: 1px solid #dee2e6; font-weight: 600;">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {items_html}
                </tbody>
              </table>
            </div>
          </div>

          <!-- Total -->
          <div style="text-align: right;">
            <div style="display: inline-block; padding: 16px 24px; border: 1px solid #dee2e6; 
                        border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); background-color: #f8f9fa;">
              <h5 style="margin: 0; font-size: 18px; font-weight: 400;">
                Total: <strong style="font-weight: 700;">&#8377;{invoice['total_amount']:.2f}</strong>
              </h5>
            </div>
          </div>

        </div>
        <!-- Footer -->
          <div style="padding: 20px 30px; background: #f9fafb; border-radius: 0 0 8px 8px; 
                      text-align: center; color: #6b7280; font-size: 14px;">
            <p style="margin: 0;">Questions? Contact us at support@regalchocolate.in</p>
          </div>

      </body>
    </html>
    """


# ----------------------------
# Generate and save the PDF invoice
# ----------------------------
def generate_invoice_PDF(order_id, session):
    """Generate PDF invoice, save to local archive, update order.invoice_path, return file path."""
    # Load the order
    order = session.query(Orders).filter_by(order_id=order_id).first()
    if not order:
        print(f"[PDF Generation] Order {order_id} not found")
        return None

    # Get HTML for invoice
    invoice = get_internal_invoice_JSON(order_id)
    invoice_html = build_invoice_email(invoice)  # your existing function
    if not invoice_html:
        print(f"[PDF Generation] Invoice HTML not ready for order {order_id}")
        return None

    try:

        config = get_pdfkit_config()

        # Define path to save invoice

        base_dir = "/home/frede/archives/invoices"  # adjust to your local archive folder
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
        # --- THE CHANGE IS HERE ---
        # Set a plain text fallback
        msg.set_content("Please view this email in an HTML-compatible client.")
        # Add the HTML body
        msg.add_alternative(body, subtype='html')
        # --------------------------

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
    """Send invoice PDF with HTML email body. Generate PDF first if it does not exist."""

    if session is None:
        print("[Send Invoice Error]: No DB session provided.")
        return False

    # Load the order
    order = session.query(Orders).filter_by(order_id=order_id).first()
    if not order:
        print(f"[Send Invoice Error]: Order {order_id} not found in DB.")
        return False

    # Generate invoice if missing
    if not order.invoice_path or not os.path.exists(order.invoice_path):
        print(f"[Send Invoice] Invoice missing for {order_id}, generating now...")
        file_path = generate_invoice_PDF(order_id, session=session)
        if not file_path:
            print(f"[Send Invoice] Failed to generate invoice for {order_id}.")
            return False
        order.invoice_path = file_path
        session.commit()

    # Read PDF bytes from file
    try:
        with open(order.invoice_path, "rb") as f:
            pdf = f.read()
    except Exception as e:
        print(f"[Send Invoice Error]: Could not read invoice file: {e}")
        return False

    # Fetch invoice data and build HTML email body
    try:
        invoice_data = get_internal_invoice_JSON(order_id)
        if not invoice_data:
            print(f"[Send Invoice Warning]: Could not fetch invoice JSON for {order_id}, using plain text.")
            body = "Thank you for your order. Please find your invoice attached."
        else:
            body = build_invoice_email(invoice_data)
    except Exception as e:
        print(f"[Send Invoice Warning]: Error building HTML email: {e}, using plain text.")
        body = "Thank you for your order. Please find your invoice attached."

    # Email content
    subject = f"Your Invoice - {order_id}"

    # Send email
    return send_email(
        user_email=user_email,
        subject=subject,
        body=body,
        pdf=pdf,
        pdf_filename=pdf_filename or f"Invoice_{order_id}.pdf"
    )


# ----------------------------
# Send tracking body
# ----------------------------
def build_tracking_email(order_id, tracking_number, carrier="India Post", tracking_url=None):
    """Build HTML email body for shipping notification with tracking."""

    # Auto-generate tracking URL if not provided
    if not tracking_url:
        tracking_url = f"https://www.indiapost.gov.in/_layouts/15/dop.portal.tracking/trackconsignment.aspx?consignmentno={tracking_number}"

    return f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
      </head>
      <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; 
                    margin: 0; padding: 20px; background-color: #f8f9fa;">

        <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; 
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);">

          <!-- Header -->
          <div style="background: linear-gradient(135deg, #afc08f 0%, #FCE7A3 100%); padding: 40px 30px; text-align: center;">
            <div style="background: white; width: 80px; height: 80px; margin: 0 auto 20px; border-radius: 50%; 
            display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
  <img src="https://regalchocolate.in/static/images/box.png" 
       alt="Package" 
       width="40" 
       height="40" 
       style="display: block;">
</div>
            <h1 style="margin: 0; font-size: 28px; font-weight: 600; color: #2d3748;">Your Order Has Shipped!</h1>
            <p style="margin: 12px 0 0 0; font-size: 16px; color: #4a5568;">Your package is on its way</p>
          </div>

          <!-- Content -->
          <div style="padding: 40px 30px;">

            <!-- Order Info -->
            <div style="text-align: center; margin-bottom: 32px;">
              <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 14px;">Order Number</p>
              <p style="margin: 0; font-size: 18px; font-weight: 600; color: #1f2937;">{order_id}</p>
            </div>

            <!-- Tracking Card -->
            <div style="background: #f9fafb; border: 2px solid #e5e7eb; border-radius: 8px; padding: 24px; margin-bottom: 24px;">
              <div style="text-align: center; margin-bottom: 20px;">
                <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px;">
                  Tracking Number
                </p>
                <p style="margin: 0; font-size: 20px; font-weight: 700; color: #1f2937; font-family: 'Courier New', monospace;">
                  {tracking_number}
                </p>
              </div>

              <div style="text-align: center; margin-bottom: 20px;">
                <p style="margin: 0; color: #6b7280; font-size: 14px;">
                  <strong>Carrier:</strong> {carrier}
                </p>
              </div>

              <!-- Track Button -->
              <div style="text-align: center;">
                <a href="{tracking_url}" 
                   style="display: inline-block; background: linear-gradient(135deg, #afc08f 0%, #9fb080 100%); 
                          color: white; text-decoration: none; padding: 14px 32px; border-radius: 6px; 
                          font-weight: 600; font-size: 16px; box-shadow: 0 2px 8px rgba(175,192,143,0.3);">
                  Track Your Package
                </a>
              </div>
            </div>

            <!-- Delivery Info -->
            <div style="background: #ecfdf5; border-left: 4px solid #10b981; padding: 16px; border-radius: 4px; margin-bottom: 24px;">
              <p style="margin: 0; color: #065f46; font-size: 14px; line-height: 1.6;">
                <strong>📦 What's next?</strong><br>
                Your package is now with our delivery partner. You'll receive updates as it moves through the shipping process.
              </p>
            </div>

            <!-- Support -->
            <div style="text-align: center; padding-top: 20px; border-top: 1px solid #e5e7eb;">
              <p style="margin: 0; color: #6b7280; font-size: 14px;">
                Questions about your order?<br>
                <a href="mailto:support@regalchocolate.in" style="color: #afc08f; text-decoration: none; font-weight: 600;">
                  Contact Support
                </a>
              </p>
            </div>

          </div>

        </div>

      </body>
    </html>
    """


# ----------------------------
# Send tracking email
# ----------------------------

def send_tracking(order_id, user_email, tracking_number, tracking_url=None, body=None, session=None):
    # TODO update the arguments coming from the task service to include a Tracking URL
    """Send tracking email with existing invoice attached."""

    # Load the order
    order = session.query(Orders).filter_by(order_id=order_id).first()
    if not order:
        print(f"[Send Tracking Error]: Order {order_id} not found in DB.")
        return False

    # Check if invoice exists
    # Generate invoice if missing
    if not order.invoice_path or not os.path.exists(order.invoice_path):
        print(f"[Send Invoice] Invoice missing for {order_id}, generating now...")
        file_path = generate_invoice_PDF(order_id, session=session)
        if not file_path:
            print(f"[Send Invoice] Failed to generate invoice for {order_id}.")
            return False
        order.invoice_path = file_path
        session.commit()

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
        body = build_tracking_email(order_id, tracking_number)

    # Send email with PDF attached
    return send_email(
        user_email=user_email,
        subject=subject,
        body=body,
        pdf=pdf,
        pdf_filename=f"Invoice_{order_id}.pdf"
    )
