import ssl
import redis
import os
import time
import socket
import subprocess
import sys
import logging

from dotenv import load_dotenv
load_dotenv()
REDIS_URL = os.getenv("REDIS_URL")
QUEUE_NAME = "celery"

load_dotenv()

# --- Settings ---
WIFI_WAIT_SECONDS = 120
CELERY_TIMEOUT_SECONDS = 60 * 5  # Time to allow Celery to run
REDIS_QUEUE_CHECK_COMMAND = "celery -A tasks inspect active"

# --- Helpers ---


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

def is_queue_empty(r):
    try:
        length = r.llen(QUEUE_NAME)
        print(f"Queue length: {length}")
        return length == 0
    except Exception as e:
        print(f"Redis error checking queue length: {e}")
        return True  # assume empty on error to avoid hangs

def run_celery_worker():
    # Set up logging to file
    logging.basicConfig(
        filename='worker.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    r = redis.from_url(REDIS_URL, ssl_cert_reqs=ssl.CERT_NONE)
    hostname = f"worker1@{socket.gethostname()}"

    worker = subprocess.Popen([
        sys.executable, "-m", "celery", "-A", "tasks",
        "worker", "--loglevel=info", "--concurrency=1"
    ])

    try:
        last_queue_length = None
        while True:
            queue_length = r.llen(QUEUE_NAME)
            if queue_length != last_queue_length:
                logging.info(f"Queue length changed: {queue_length} tasks")
                last_queue_length = queue_length
            time.sleep(10)

    except Exception as e:
        logging.error(f"Error: {e}")

    finally:
        logging.info("Stopping worker...")
        worker.terminate()
        worker.wait()



# --- Main Routine ---
if __name__ == "__main__":
    wait_for_wifi()

    while True:
        try:
            run_celery_worker()
        except Exception as e:
            logging.error(f"Worker crashed: {e}")
            time.sleep(5)  # Wait before retrying

