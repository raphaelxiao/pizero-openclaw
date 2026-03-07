"""Doubao / Volcano Engine STT using the Big Model Flash Recognition API.

API docs: https://www.volcengine.com/docs/6561/1354868
Endpoint: POST https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash
"""

import base64
import os
import uuid

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core import config

_http_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _http_session
    if _http_session is None:
        _http_session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[502, 503, 504],
            allowed_methods=["POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        _http_session.mount("http://", adapter)
        _http_session.mount("https://", adapter)
    return _http_session


def transcribe(wav_path: str) -> str:
    """Transcribe a WAV file using Volcano Engine Big Model Flash Recognition API.

    In dry-run mode, prompts for typed input instead.
    """
    if config.DRY_RUN and not config.DOUBAO_ACCESS_TOKEN:
        print("[transcribe] DRY RUN — type your message:")
        try:
            return input("> ").strip()
        except EOFError:
            return ""

    if not config.DOUBAO_ACCESS_TOKEN or not config.DOUBAO_APPID:
        print("[transcribe] ERROR: DOUBAO_ACCESS_TOKEN or DOUBAO_APPID is not set.")
        return ""

    if not os.path.exists(wav_path):
        raise FileNotFoundError(f"WAV file not found: {wav_path}")

    file_size = os.path.getsize(wav_path)
    if file_size < 100:
        raise ValueError(f"WAV file too small ({file_size} bytes), likely empty recording")

    url = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"
    headers = {
        "X-Api-App-Key": config.DOUBAO_APPID,
        "X-Api-Access-Key": config.DOUBAO_ACCESS_TOKEN,
        "X-Api-Resource-Id": "volc.bigasr.auc_turbo",
        "X-Api-Request-Id": str(uuid.uuid4()),
        "X-Api-Sequence": "-1",
        "Content-Type": "application/json",
    }

    with open(wav_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode("utf-8")

    payload = {
        "user": {"uid": "openclaw"},
        "audio": {"data": audio_b64, "format": "wav"},
        "request": {"model_name": "bigmodel"},
    }

    try:
        resp = _get_session().post(url, json=payload, headers=headers, timeout=60)
    except (requests.ConnectionError, requests.Timeout) as e:
        raise RuntimeError(f"Transcription request failed: {e}") from e

    if resp.status_code != 200:
        raise RuntimeError(
            f"Transcription failed ({resp.status_code}): {resp.text[:300]}"
        )

    try:
        data = resp.json()
        # The flash API returns result in resp.result[0].text or similar structure
        result = data.get("result", [])
        if isinstance(result, list) and len(result) > 0:
            transcript = result[0].get("text", "").strip()
        else:
            transcript = data.get("text", "").strip()
    except (ValueError, KeyError, IndexError) as e:
        raise RuntimeError(
            f"Transcription response parsing failed: {e}. Output was {resp.text[:300]}"
        )

    print(f"[transcribe] result: {transcript[:120]}")
    return transcript
