# -*- coding: utf-8 -*-
"""Publica Importação de Saídas no GitHub (repo importacao-saidas-sv)."""
from __future__ import annotations

import base64
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

OWNER = "lubrificacaomaquinassv-cloud"
REPO = "importacao-saidas-sv"
BRANCH = "main"
SRC = Path(__file__).resolve().parent
TOKEN_FILES = [
    SRC / "github_token.txt",
    Path(r"D:\pwa-comboio-posto-abastecimento\ATUALIZACAO_CONTROLE_VIAGENS\github_token.txt"),
    Path(r"D:\pwa-comboio-posto-abastecimento\ATUALIZACAO_HORA_OPERADOR\ATUALIZAR PAINEL GESTOR\github_token.txt"),
]


def fail(msg: str) -> None:
    print("ERRO:", msg)
    sys.exit(1)


def read_token() -> str:
    for key in ("GITHUB_TOKEN", "GH_TOKEN"):
        v = os.environ.get(key, "").strip()
        if v.lower().startswith(("github_pat_", "ghp_")):
            return v
    for tf in TOKEN_FILES:
        if not tf.is_file():
            continue
        for line in tf.read_text(encoding="utf-8").splitlines():
            v = line.strip()
            if v.startswith("#") or not v:
                continue
            if v.lower().startswith(("github_pat_", "ghp_")) and "COLE" not in v.upper():
                return v
    fail("Token GitHub ausente em ATUALIZACAO_CONTROLE_VIAGENS\\github_token.txt")


def api(method: str, url: str, token: str, body: dict | None = None) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "importacao-saidas-sv-publisher",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = json.dumps(body).encode() if body else None
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
            raw = r.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode()[:800]
        if e.code == 404:
            return {"_404": True, "detail": body_txt}
        fail(f"GitHub {e.code}: {body_txt}")


def ensure_repo(token: str) -> None:
    url = f"https://api.github.com/repos/{OWNER}/{REPO}"
    res = api("GET", url, token)
    if not res.get("_404"):
        print(f"Repo: {url}")
        return
    print(f"Criando {OWNER}/{REPO} ...")
    api(
        "POST",
        f"https://api.github.com/orgs/{OWNER}/repos",
        token,
        {
            "name": REPO,
            "description": "Importação de Saídas Operacionais — SAP Excel SIGCF",
            "private": False,
            "auto_init": False,
        },
    )


def collect_files() -> dict[str, Path]:
    out: dict[str, Path] = {}
    for name in ("app.py", "sigcf_auth.py", "requirements.txt", "pages_ops.py"):
        p = SRC / name
        if p.is_file():
            out[name] = p
    scripts = SRC / "scripts"
    if scripts.is_dir():
        for p in sorted(scripts.glob("*.py")):
            out[f"scripts/{p.name}"] = p
    assets = SRC / "assets"
    if assets.is_dir():
        for p in assets.rglob("*"):
            if p.is_file():
                out[str(p.relative_to(SRC)).replace("\\", "/")] = p
    return out


def get_sha(token: str, path: str) -> str:
    res = api("GET", f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}?ref={BRANCH}", token)
    return "" if res.get("_404") else res.get("sha", "")


def upload(token: str, path: str, content: bytes, message: str) -> None:
    payload = {
        "message": message,
        "content": base64.b64encode(content).decode("ascii"),
        "branch": BRANCH,
    }
    sha = get_sha(token, path)
    if sha:
        payload["sha"] = sha
    api("PUT", f"https://api.github.com/repos/{OWNER}/{REPO}/contents/{path}", token, payload)
    print(f"  OK  {path}")


def main() -> None:
    token = read_token()
    ensure_repo(token)
    msg = "Lubrificantes: upload baixa e estoque no painel Importação de Saídas"
    files = collect_files()
    print(f"Publicando {len(files)} arquivo(s) em {OWNER}/{REPO} ...")
    for remote, local in files.items():
        upload(token, remote, local.read_bytes(), msg)
    print(f"\nRepo: https://github.com/{OWNER}/{REPO}")
    print("Streamlit Cloud: app.py (main) — Reboot app após conectar")


if __name__ == "__main__":
    main()
