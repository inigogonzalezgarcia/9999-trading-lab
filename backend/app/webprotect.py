"""Split each exported run into a public file and an encrypted Lab Pro part.

The site stays static. What Lab Pro sells (trade explainers, the detailed research sections, the PDF) is encrypted
at export time with a key derived from ``DATA_KEY`` and the run id; the public JSON keeps everything a reader needs
to verify the result (trades, metrics, equity curve, candles, hashes, baseline verdict). A Pages Function hands the
per-run key to Pro sessions (and to everyone for the 2024 demo runs); the browser decrypts with WebCrypto.

    DATA_KEY=... python -m backend.cli protect-web           # process every run already exported
    export-web calls the same step after writing each run when DATA_KEY is set.

The key is read from the ``DATA_KEY`` environment variable or from ``secrets/data_key.txt`` (git-ignored). The same
value must be set as a Pages secret so the Function derives the same per-run keys.

Format of ``<id>.enc`` / ``<id>.pdf.enc``: 12-byte random nonce + AES-256-GCM ciphertext (tag appended).
Per-run key: SHA-256(DATA_KEY + ":" + run_id).
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
from pathlib import Path
from typing import Any

DEMO_MARKER = "2024"  # runs whose id contains this stay fully public (the demonstration year)
PRIVATE_BACKTEST_KEYS = ("trade_explainers",)
PRIVATE_RESEARCH_KEYS = ("splits", "walk_forward", "monte_carlo", "benchmark", "sensitivity")


def is_demo(run_id: str) -> bool:
    return DEMO_MARKER in run_id


def load_data_key(root: Path | None = None) -> str | None:
    key = os.environ.get("DATA_KEY", "").strip()
    if not key:
        path = (root or Path.cwd()) / "secrets" / "data_key.txt"
        if path.exists():
            key = path.read_text(encoding="utf-8").strip()
    if not key:
        return None
    if len(key) < 32 or "PEGA" in key.upper() or "PASTE" in key.upper():
        raise SystemExit("DATA_KEY looks like a placeholder or is too short: generate one with `openssl rand -hex 32`")
    return key


def run_key(data_key: str, run_id: str) -> bytes:
    return hashlib.sha256(f"{data_key}:{run_id}".encode()).digest()


def encrypt(key: bytes, data: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    nonce = secrets.token_bytes(12)
    return nonce + AESGCM(key).encrypt(nonce, data, None)


def split_payload(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (public, private). Research keeps a summary of benchmark and walk-forward for the verdict tiles."""
    public = dict(payload)
    private: dict[str, Any] = {}
    if "trades" in payload:  # backtest
        for key in PRIVATE_BACKTEST_KEYS:
            if key in public:
                private[key] = public.pop(key)
    else:  # research
        for key in PRIVATE_RESEARCH_KEYS:
            if key in public:
                private[key] = public.pop(key)
        bench = private.get("benchmark") or {}
        if bench:
            public["benchmark"] = {k: bench.get(k) for k in ("simulations", "baseline_expectancy_r", "baseline_percentile_vs_random", "empirical_p_value_one_sided")}
        wf = private.get("walk_forward") or {}
        if wf:
            public["walk_forward"] = {"parameters": wf.get("parameters"), "fold_count": wf.get("fold_count"), "out_of_sample_concatenated": wf.get("out_of_sample_concatenated"), "folds": []}
    web = dict(public.get("web_export") or {})
    web["protected"] = bool(private)
    web["private_keys"] = sorted(private)
    public["web_export"] = web
    return public, private


def protect_run(out: Path, run_id: str, data_key: str) -> dict[str, Any]:
    """Split one exported run in place. Idempotent: a run already split is left alone."""
    runs = out / "runs"
    json_path = runs / f"{run_id}.json"
    enc_path = runs / f"{run_id}.enc"
    pdf_path = runs / f"{run_id}.pdf"
    pdf_enc_path = runs / f"{run_id}.pdf.enc"
    meta_path = runs / f"{run_id}.meta.json"
    info: dict[str, Any] = {"id": run_id, "demo": is_demo(run_id)}
    if is_demo(run_id):
        for stale in (enc_path, pdf_enc_path):
            if stale.exists():
                stale.unlink()
        return info
    key = run_key(data_key, run_id)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if (payload.get("web_export") or {}).get("protected") and enc_path.exists():
        info["already"] = True
        if pdf_path.exists():  # a fresh PDF next to an already split run
            pdf_enc_path.write_bytes(encrypt(key, pdf_path.read_bytes()))
            pdf_path.unlink()
            info["pdf"] = "encrypted"
        return info
    public, private = split_payload(payload)
    if private:
        enc_path.write_bytes(encrypt(key, json.dumps(private, default=str, separators=(",", ":")).encode()))
        json_path.write_text(json.dumps(public, default=str, separators=(",", ":")), encoding="utf-8")
        info["private_keys"] = sorted(private)
    elif not enc_path.exists():
        json_path.write_text(json.dumps(public, default=str, separators=(",", ":")), encoding="utf-8")
    if pdf_path.exists():
        pdf_enc_path.write_bytes(encrypt(key, pdf_path.read_bytes()))
        pdf_path.unlink()
        info["pdf"] = "encrypted"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if pdf_enc_path.exists():
            meta["pdf"] = f"runs/{run_id}.pdf.enc"
        meta["protected"] = True
        meta["size_bytes"] = json_path.stat().st_size
        meta_path.write_text(json.dumps(meta, indent=1, default=str), encoding="utf-8")
    return info


def protect_all(out: Path, data_key: str) -> list[dict[str, Any]]:
    return [protect_run(out, path.stem, data_key) for path in sorted((out / "runs").glob("*.json")) if not path.name.endswith(".meta.json")]


def decrypt(key: bytes, blob: bytes) -> bytes:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    return AESGCM(key).decrypt(blob[:12], blob[12:], None)


def rekey_all(out: Path, old_key: str, new_key: str) -> list[str]:
    """Re-encrypt every ``.enc`` / ``.pdf.enc`` from ``old_key`` to ``new_key`` (after a key mix-up or rotation)."""
    done: list[str] = []
    for path in sorted((out / "runs").glob("*.enc")):
        run_id = path.name[: -len(".pdf.enc")] if path.name.endswith(".pdf.enc") else path.stem
        plain = decrypt(run_key(old_key, run_id), path.read_bytes())
        path.write_bytes(encrypt(run_key(new_key, run_id), plain))
        done.append(path.name)
    return done
