#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import textwrap
from pathlib import Path, PurePosixPath

DOMAIN = "social.bb610.com.ua"
EXPECTED_IP = "173.242.53.156"
APP = Path("/opt/twofamily-social-control")
STATE = Path("/var/lib/twofamily-social-control")
STAGE = STATE / "staging"
BUNDLE = STAGE / "twofamily-social-control.production.tar.gz"
UPLOAD_PORT = 18100
UPLOAD_SCRIPT = Path("/usr/local/sbin/twofamily-upload-receiver.py")
UPLOAD_SERVICE = Path("/etc/systemd/system/twofamily-upload.service")


def run(args, *, check=True, env=None, cwd=None):
    print("+", " ".join(str(x) for x in args), flush=True)
    return subprocess.run([str(x) for x in args], check=check, env=env, cwd=cwd, text=True)


def output(args):
    return subprocess.check_output([str(x) for x in args], text=True).strip()


def valid_sha(value: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise SystemExit("invalid SHA256")
    return value


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def nginx_paths(name: str):
    if Path("/etc/nginx/sites-available").is_dir():
        available = Path("/etc/nginx/sites-available") / name
        enabled = Path("/etc/nginx/sites-enabled") / name
        return available, enabled
    return Path("/etc/nginx/conf.d") / name, None


def write_file(path: Path, content: str, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    os.chmod(path, mode)


def safe_tar(path: Path):
    with tarfile.open(path, "r:gz") as tf:
        for member in tf.getmembers():
            p = PurePosixPath(member.name)
            if p.is_absolute() or ".." in p.parts:
                raise SystemExit(f"unsafe tar path: {member.name}")
    print("BUNDLE_PATHS=SAFE")


def parse_env(path: Path):
    data = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key] = value
    return data


def prepare_upload(expected: str):
    expected = valid_sha(expected)
    STAGE.mkdir(parents=True, exist_ok=True)
    os.chmod(STAGE, 0o700)

    receiver = """#!/usr/bin/env python3
import hashlib, os, sys, threading
from http.server import BaseHTTPRequestHandler, HTTPServer

expected, dest = sys.argv[1], sys.argv[2]
limit = 10 * 1024 * 1024

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_POST(self):
        if self.path != "/upload":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > limit:
            self.send_error(413)
            return
        tmp = dest + ".part"
        h = hashlib.sha256()
        remaining = length
        try:
            with open(tmp, "wb") as fh:
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise RuntimeError("unexpected EOF")
                    fh.write(chunk)
                    h.update(chunk)
                    remaining -= len(chunk)
            if h.hexdigest() != expected:
                os.unlink(tmp)
                self.send_error(422, "SHA256 mismatch")
                return
            os.replace(tmp, dest)
            os.chmod(dest, 0o600)
            self.send_response(201)
            self.end_headers()
            self.wfile.write(b"STAGED\n")
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        except Exception:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            self.send_error(500)

HTTPServer(("127.0.0.1", 18100), Handler).serve_forever()
"""
    write_file(UPLOAD_SCRIPT, receiver, 0o700)
    unit = f"""[Unit]
Description=TwoFamily one-shot deployment upload receiver
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 {UPLOAD_SCRIPT} {expected} {BUNDLE}
Restart=no
PrivateTmp=yes
NoNewPrivileges=yes
ProtectSystem=strict
ReadWritePaths={STAGE}

[Install]
WantedBy=multi-user.target
"""
    write_file(UPLOAD_SERVICE, unit)

    conf, enabled = nginx_paths("twofamily-upload.conf")
    nginx = f"""server {{
    listen 80;
    server_name {DOMAIN};
    client_max_body_size 10m;
    server_tokens off;
    add_header X-Robots-Tag "noindex, nofollow, noarchive" always;

    location = /__twofamily_upload/{expected} {{
        proxy_pass http://127.0.0.1:{UPLOAD_PORT}/upload;
        proxy_request_buffering off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }}

    location / {{
        return 503;
    }}
}}
"""
    write_file(conf, nginx)
    if enabled:
        enabled.parent.mkdir(parents=True, exist_ok=True)
        if enabled.exists() or enabled.is_symlink():
            enabled.unlink()
        enabled.symlink_to(conf)

    run(["nginx", "-t"])
    run(["systemctl", "reload", "nginx"])

    resolved = socket.gethostbyname(DOMAIN)
    if resolved != EXPECTED_IP:
        raise SystemExit(f"REFUSED: {DOMAIN} resolves to {resolved}, expected {EXPECTED_IP}")

    cert = Path(f"/etc/letsencrypt/live/{DOMAIN}/fullchain.pem")
    if not cert.is_file():
        run([
            "certbot", "--nginx", "-d", DOMAIN,
            "--non-interactive", "--agree-tos",
            "--register-unsafely-without-email", "--redirect",
        ])

    run(["nginx", "-t"])
    run(["systemctl", "reload", "nginx"])
    run(["systemctl", "daemon-reload"])
    run(["systemctl", "restart", "twofamily-upload.service"])
    print(f"TWOFAMILY_UPLOAD_READY=https://{DOMAIN}/__twofamily_upload/{expected}")


def install_packages():
    if shutil.which("dnf"):
        run(["dnf", "-y", "install", "nodejs", "npm", "postgresql-server", "postgresql-contrib"])
        if not shutil.which("ffmpeg"):
            if subprocess.run(["dnf", "-y", "install", "ffmpeg"]).returncode != 0:
                subprocess.run(["dnf", "-y", "install", "ffmpeg-free"])
    elif shutil.which("yum"):
        run(["yum", "-y", "install", "nodejs", "npm", "postgresql-server", "postgresql-contrib"])
        if not shutil.which("ffmpeg"):
            subprocess.run(["yum", "-y", "install", "ffmpeg"])
    elif shutil.which("apt-get"):
        run(["apt-get", "update"])
        run([
            "apt-get", "install", "-y", "nodejs", "npm", "postgresql",
            "postgresql-client", "python3-venv", "ffmpeg",
        ])
    else:
        raise SystemExit("REFUSED: unsupported package manager")


def ensure_postgres(env):
    if not shutil.which("psql"):
        raise SystemExit("REFUSED: psql unavailable after package install")
    pg_version = Path("/var/lib/pgsql/data/PG_VERSION")
    if shutil.which("postgresql-setup") and not pg_version.is_file():
        if subprocess.run(["postgresql-setup", "--initdb"]).returncode != 0:
            run(["postgresql-setup", "--initdb", "--unit", "postgresql"])
    run(["systemctl", "enable", "--now", "postgresql"])

    password = env.get("POSTGRES_PASSWORD", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,}", password):
        raise SystemExit("REFUSED: unsafe/missing PostgreSQL password")

    exists = output(["runuser", "-u", "postgres", "--", "psql", "-tAc",
                     "SELECT 1 FROM pg_roles WHERE rolname='twofamily'"])
    if "1" not in exists:
        run(["runuser", "-u", "postgres", "--", "psql", "-v", "ON_ERROR_STOP=1",
             "-c", f"CREATE ROLE twofamily LOGIN PASSWORD '{password}';"])
    else:
        run(["runuser", "-u", "postgres", "--", "psql", "-v", "ON_ERROR_STOP=1",
             "-c", f"ALTER ROLE twofamily WITH LOGIN PASSWORD '{password}';"])

    db_exists = output(["runuser", "-u", "postgres", "--", "psql", "-tAc",
                        "SELECT 1 FROM pg_database WHERE datname='twofamily_social'"])
    if "1" not in db_exists:
        run(["runuser", "-u", "postgres", "--", "createdb", "-O", "twofamily", "twofamily_social"])


def ensure_www_data():
    if subprocess.run(["getent", "group", "www-data"], stdout=subprocess.DEVNULL).returncode != 0:
        run(["groupadd", "--system", "www-data"])
    if subprocess.run(["id", "-u", "www-data"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode != 0:
        run(["useradd", "--system", "-g", "www-data", "-d", "/nonexistent", "-s", "/sbin/nologin", "www-data"])


def final_nginx():
    upload_conf, upload_enabled = nginx_paths("twofamily-upload.conf")
    if upload_enabled and (upload_enabled.exists() or upload_enabled.is_symlink()):
        upload_enabled.unlink()
    if upload_conf.exists():
        upload_conf.unlink()

    conf, enabled = nginx_paths("twofamily-social.conf")
    nginx = f"""server {{
    listen 80;
    server_name {DOMAIN};
    return 301 https://$host$request_uri;
}}

server {{
    listen 443 ssl;
    server_name {DOMAIN};

    ssl_certificate /etc/letsencrypt/live/{DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{DOMAIN}/privkey.pem;

    root {APP}/frontend/dist;
    index index.html;

    server_tokens off;
    add_header X-Robots-Tag "noindex, nofollow, noarchive" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "same-origin" always;

    location = /robots.txt {{
        default_type text/plain;
        return 200 "User-agent: *\\nDisallow: /\\n";
    }}

    location /api/ {{
        proxy_pass http://127.0.0.1:8100/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}

    location / {{
        try_files $uri $uri/ /index.html;
    }}
}}
"""
    write_file(conf, nginx)
    if enabled:
        enabled.parent.mkdir(parents=True, exist_ok=True)
        if enabled.exists() or enabled.is_symlink():
            enabled.unlink()
        enabled.symlink_to(conf)


def install_bundle(expected: str):
    expected = valid_sha(expected)
    if not BUNDLE.is_file():
        raise SystemExit("REFUSED: staged bundle missing")
    if sha256(BUNDLE) != expected:
        raise SystemExit("REFUSED: staged bundle SHA mismatch")
    safe_tar(BUNDLE)

    install_packages()

    previous = None
    if APP.exists():
        previous = Path(f"{APP}.preinstall.{output(['date', '+%Y%m%d%H%M%S'])}")
        APP.rename(previous)
    APP.mkdir(parents=True, exist_ok=True)
    with tarfile.open(BUNDLE, "r:gz") as tf:
        tf.extractall(APP)

    env_path = APP / ".env"
    if not env_path.is_file():
        raise SystemExit("REFUSED: production .env missing from bundle")
    os.chmod(env_path, 0o600)
    env_data = parse_env(env_path)
    ensure_postgres(env_data)
    ensure_www_data()

    media = STATE / "media"
    media.mkdir(parents=True, exist_ok=True)
    shutil.chown(media, user="www-data", group="www-data")
    os.chmod(media, 0o750)

    secrets_dir = APP / "secrets"
    secrets_dir.mkdir(parents=True, exist_ok=True)
    shutil.chown(secrets_dir, user="root", group="www-data")
    os.chmod(secrets_dir, 0o750)

    backups = Path("/var/backups/twofamily-social-control")
    backups.mkdir(parents=True, exist_ok=True)
    os.chmod(backups, 0o750)

    run(["python3", "-m", "venv", APP / "backend/.venv"])
    pip = APP / "backend/.venv/bin/pip"
    run([pip, "install", "--upgrade", "pip"])
    run([pip, "install", "-r", APP / "backend/requirements.txt"])

    proc_env = os.environ.copy()
    proc_env.update(env_data)
    run([APP / "backend/.venv/bin/alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=APP / "backend", env=proc_env)

    run(["npm", "install"], cwd=APP / "frontend")
    run(["npm", "run", "build"], cwd=APP / "frontend")

    for unit in (APP / "deploy").glob("twofamily-social-*.service"):
        shutil.copy2(unit, Path("/etc/systemd/system") / unit.name)
    shutil.copy2(APP / "deploy/twofamily-social-backup.timer",
                 "/etc/systemd/system/twofamily-social-backup.timer")

    final_nginx()

    run(["systemctl", "daemon-reload"])
    units = [
        "twofamily-social-api.service",
        "twofamily-social-worker.service",
        "twofamily-social-visual-worker.service",
        "twofamily-social-meta-health.service",
        "twofamily-social-analytics.service",
        "twofamily-social-backup.timer",
    ]
    run(["systemctl", "enable", *units])
    run(["systemctl", "restart", "twofamily-social-api.service"])
    run(["sleep", "3"])
    for unit in units[1:-1]:
        run(["systemctl", "restart", unit])
    run(["systemctl", "start", "twofamily-social-backup.timer"])

    run(["nginx", "-t"])
    run(["systemctl", "reload", "nginx"])
    run(["curl", "-fsS", "--max-time", "20", "http://127.0.0.1:8100/api/health"])
    run(["curl", "-fsS", "--max-time", "30", f"https://{DOMAIN}/api/health"])

    owner_email = env_data.get("BOOTSTRAP_OWNER_EMAIL", "")
    owner_password = env_data.get("BOOTSTRAP_OWNER_PASSWORD", "")
    write_file(Path("/root/twofamily-initial-owner.txt"),
               f"OWNER_EMAIL={owner_email}\\nOWNER_PASSWORD={owner_password}\\n", 0o600)

    lines = []
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("BOOTSTRAP_OWNER_PASSWORD="):
            lines.append("BOOTSTRAP_OWNER_PASSWORD=")
        else:
            lines.append(raw)
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(env_path, 0o600)
    run(["systemctl", "restart", "twofamily-social-api.service"])

    subprocess.run(["systemctl", "disable", "--now", "twofamily-upload.service"])
    UPLOAD_SERVICE.unlink(missing_ok=True)
    UPLOAD_SCRIPT.unlink(missing_ok=True)
    run(["systemctl", "daemon-reload"])

    print("TWOFAMILY_INSTALL=PASS")
    print(f"APP=https://{DOMAIN}")
    print("FFMPEG=READY" if shutil.which("ffmpeg") else "FFMPEG=MISSING")
    if previous:
        print(f"PREVIOUS={previous}")


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: twofamily-rollout.py prepare-upload|install SHA256")
    action, sha = sys.argv[1], sys.argv[2]
    if action == "prepare-upload":
        prepare_upload(sha)
    elif action == "install":
        install_bundle(sha)
    else:
        raise SystemExit("unsupported action")


if __name__ == "__main__":
    main()
