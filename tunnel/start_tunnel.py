import os
import re
import sys
import time
import subprocess
import requests

sys.stdout.reconfigure(line_buffering=True)

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OWNER = os.getenv("GITHUB_OWNER")
WEBHOOK_ID = os.getenv("WEBHOOK_ID")
WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")


def wait_backend():
    print("⏳ Esperando backend...")

    while True:
        try:
            response = requests.get(
                "http://backend:8000/docs",
                timeout=5
            )

            if response.status_code == 200:
                print("✅ Backend listo")
                return

        except Exception:
            pass

        time.sleep(3)


def start_tunnel():

    print("🚀 Iniciando Cloudflare Tunnel...")

    process = subprocess.Popen(
        [
            "cloudflared",
            "tunnel",
            "--no-autoupdate",
            "--url",
            "http://backend:8000"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    tunnel_url = None

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
            tunnel_url = match.group(0)
            break

    if not tunnel_url:
        raise Exception(
            "❌ No se pudo obtener la URL del túnel"
        )

    print(f"🌎 URL pública: {tunnel_url}")

    return tunnel_url, process


def update_webhook(tunnel_url):

    print("🔄 Actualizando webhook GitHub...")

    api_url = (
        f"https://api.github.com/orgs/"
        f"{OWNER}/hooks/{WEBHOOK_ID}"
    )

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    payload = {
        "active": True,
        "config": {
            "url": f"{tunnel_url}/webhook/github",
            "content_type": "json",
            "secret": WEBHOOK_SECRET,
            "insecure_ssl": "0"
        }
    }

    response = requests.patch(
        api_url,
        headers=headers,
        json=payload,
        timeout=30
    )

    print(f"GitHub Status: {response.status_code}")
    print(response.text)

    response.raise_for_status()

    print("✅ Webhook actualizado correctamente")


if __name__ == "__main__":

    print("===================================")
    print("🚀 INICIANDO SERVICIO DE TÚNEL")
    print("===================================")

    print("OWNER:", OWNER)
    print("WEBHOOK_ID:", WEBHOOK_ID)
    print("TOKEN:", "OK" if GITHUB_TOKEN else "NO")
    print("===================================")

    wait_backend()

    tunnel_url, process = start_tunnel()

    update_webhook(tunnel_url)

    print("✅ Servicio funcionando")

    process.wait()