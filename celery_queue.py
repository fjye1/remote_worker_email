import redis, os, ssl
from dotenv import load_dotenv

load_dotenv()
REDIS_URL = os.getenv("REDIS_URL")
r = redis.from_url(REDIS_URL, ssl_cert_reqs=ssl.CERT_NONE)
print(r.llen("celery"))
