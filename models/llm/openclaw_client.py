import json
from typing import Generator
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from core import config

_http_session: requests.Session | None = None


def _get_session() -> requests.Session:
    global _http_session
    if _http_session is None:
        _http_session = requests.Session()
        _http_session.trust_env = False  # Ignore HTTP_PROXY for internal OpenClaw Gateway
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


def stream_response(
    user_text: str,
) -> Generator[str, None, None]:
    """Send user_text to OpenClaw /v1/responses with streaming.

    Yields text deltas as they arrive via SSE.
    """
    url = f"{config.OPENCLAW_BASE_URL}/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.OPENCLAW_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "x-openclaw-session-key": "pizero-device-001",
        "x-openclaw-agent-id": "main"
    }

    messages = [{"role": "user", "content": user_text}]

    body = {
        "model": "openclaw",
        "stream": True,
        "messages": messages,
    }

    print(f"[openclaw] POST {url} (stream=true)")

    try:
        resp = _get_session().post(url, json=body, headers=headers, stream=True, timeout=(30, 120))
    except (requests.ConnectionError, requests.Timeout) as e:
        raise RuntimeError(f"Cannot reach OpenClaw at {config.OPENCLAW_BASE_URL}: {e}") from e

    if resp.status_code != 200:
        raise RuntimeError(
            f"OpenClaw request failed ({resp.status_code}): {resp.text[:300]}"
        )

    # Process SSE stream line by line instead of buffering in 512-byte chunks
    # (iter_content(512) blocks and waits until 512 bytes are complete, causing chunky UI updates).
    event_type = None
    for line_bytes in resp.iter_lines():
        if not line_bytes:
            event_type = None
            continue
            
        line = line_bytes.decode("utf-8")
        if line.startswith("event:"):
            event_type = line[len("event:"):].strip()
            continue
            
        if line.startswith("data:"):
            data_str = line[len("data:"):].strip()
            if not data_str or data_str == "[DONE]":
                continue
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue
                
            if "error" in data:
                err_msg = data.get("error", {}).get("message", str(data))
                raise RuntimeError(f"OpenClaw stream error: {err_msg}")
                
            choices = data.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                content = delta.get("content")
                if content:
                    yield content
