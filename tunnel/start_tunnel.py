import os
import re
import time
import subprocess
import requests

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OWNER = os.getenv("GITHUB_OWNER")
REPO = os.getenv("GITHUB_REPO")
WEBHOOK_ID = os.getenv("WEBHOOK_ID")
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")


def wait_backend():
    while True:
        try:
            r = requests.get(
                "http://backend:8000/docs",
                timeout=5
            )

            if r.status_code == 200:
                print("✅ Backend listo")
                return

        except Exception:
            pass

        print("⏳ Esperando backend...")
        time.sleep(3)


def start_tunnel():

    print("🚀 Iniciando Cloudflare Tunnel...")

    process = subprocess.Popen(
        [
            "cloudflared",
            "tunnel",
            "--url",
            "http://backend:8000"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    url = None

    while True:

        line = process.stdout.readline()

        if not line:
            continue

        print(line.strip())

        match = re.search(
            r"https://[a-zA-Z0-9-]+\.trycloudflare\.com",
            line
        )

        if match:
            url = match.group(0)
            break

    if not url:
        raise Exception(
            "❌ No se pudo obtener URL del tunnel"
        )

    print(f"🌎 URL pública: {url}")

    return url, process


def update_webhook(url):

    print("🔄 Actualizando webhook GitHub...")

    api_url = (
        f"https://api.github.com/repos/"
        f"{OWNER}/{REPO}/hooks/{WEBHOOK_ID}"
    )

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    payload = {
        "config": {
            "url": f"{url}/webhook/github",
            "content_type": "json",
            "secret": WEBHOOK_SECRET
        }
    }

    response = requests.patch(
        api_url,
        json=payload,
        headers=headers,
        timeout=20
    )

    print(response.status_code)
    print(response.text)

    response.raise_for_status()

    print("✅ Webhook actualizado")


if __name__ == "__main__":

    wait_backend()

    url, process = start_tunnel()

    update_webhook(url)

    process.wait()