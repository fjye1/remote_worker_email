import time
import socket
import functions
from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, select, delete
from sqlalchemy.orm import sessionmaker
import psycopg2
from models import Tasks

load_dotenv()

RENDER_DATABASE_URL = os.getenv("RENDER_DATABASE_URL")

engine = create_engine(RENDER_DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

WIFI_WAIT_SECONDS = 120

def is_connected(host="8.8.8.8", port=53, timeout=3):
    """Check if we have internet (assumes Wi-Fi is ready)."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        return False

def wait_for_wifi():
    print(f"Waiting up to {WIFI_WAIT_SECONDS} seconds for Wi-Fi...")
    for _ in range(WIFI_WAIT_SECONDS):
        if is_connected():
            print("Wi-Fi connected.")
            return
        time.sleep(1)
    print("Wi-Fi not detected. Continuing anyway.")


try:
    while True:
        # Grab one pending task
        task = session.execute(
            select(Tasks)
            .where(Tasks.status == Tasks.TaskStatus.PENDING)
            .limit(1)
            .with_for_update(skip_locked=True)
        ).scalar_one_or_none()

        if not task:
            # No more pending tasks → exit
            break

        # Mark as in-progress
        task.status = Tasks.TaskStatus.IN_PROGRESS
        session.commit()

        print(f"Running task: {task.task_name} with args: {task.arg1}, {task.arg2}, {task.arg3}")

        # === Run the actual task here ===
        # Example:
        if task.task_name == "send_invoice":
            functions.send_invoice(task.arg1, task.arg2)
        elif task.task_name == "send_tracking":
            functions.send_tracking(task.arg1, task.arg2, task.arg3)

        # Delete task after completion (ORM way)
        session.delete(task)
        session.commit()

except Exception as e:
    session.rollback()
    print(f"[Worker Error]: {e}")
finally:
    session.close()

#Tracking
# new_task = Tasks(
#             task_name="send_tracking",
#             arg1=order.order_id,
#             arg2=order.user.email,
#             arg3=order.tracking_number

#invoice
# new_task = Tasks(
#             task_name="send_invoice",
#             arg1=order.order_id,
#             arg2=order.user.email

