import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

NOTIFY_EMAIL = os.getenv("NOTIFY_EMAIL", "victor.epunae@gmail.com")
GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

async def send_order_notification(order_id, order_name, items, total, customer):
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        return
    items_html = "".join([f"<li>{i.get('title','?')} x{i.get('quantity',1)}</li>" for i in items])
    customer_name = f"{customer.get('first_name','')} {customer.get('last_name','')}".strip()
    html = f"<h2>New Sale - {order_name}</h2><p>Customer: {customer_name}</p><p>Total: ${total}</p><ul>{items_html}</ul><p><a href='https://shop-wit-sazy.myshopify.com/admin/orders'>View Order</a></p>"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"APEX Sale - {order_name} - ${total}"
    msg["From"] = GMAIL_USER
    msg["To"] = NOTIFY_EMAIL
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, NOTIFY_EMAIL, msg.as_string())
    except Exception as e:
        print(f"Notification failed: {e}")
