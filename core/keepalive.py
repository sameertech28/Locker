import logging
import os
import threading
import time
import requests

logger = logging.getLogger(__name__)


def _pinger_worker():
    # Wait 30 seconds after startup before starting periodic requests
    time.sleep(30)

    url = os.environ.get("KEEP_ALIVE_URL")
    if not url:
        render_host = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
        if render_host:
            url = f"https://{render_host}/health/"

    if not url:
        logger.info("[KeepAlive] No KEEP_ALIVE_URL or RENDER_EXTERNAL_HOSTNAME defined. Keep-alive pinger inactive.")
        return

    logger.info(f"[KeepAlive] Keep-alive worker started for {url} (every 10 minutes).")

    while True:
        try:
            resp = requests.get(url, headers={"User-Agent": "Locker-KeepAlive/1.0"}, timeout=15)
            logger.info(f"[KeepAlive] Pinged {url} -> Status: {resp.status_code}")
        except Exception as exc:
            logger.warning(f"[KeepAlive] Ping failed for {url}: {exc}")

        # Sleep for 10 minutes (600 seconds)
        time.sleep(600)


def start_keepalive():
    # Only run in the main process when debugging or in production
    is_debug = os.environ.get("DEBUG", "True") == "True"
    if is_debug and os.environ.get("RUN_MAIN") != "true":
        return

    thread = threading.Thread(target=_pinger_worker, daemon=True, name="LockerKeepAliveThread")
    thread.start()
