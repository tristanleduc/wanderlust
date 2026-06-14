"""Inference trace logging (Open Trace badge).

Every model call — vibe→weights extraction and route narration — emits one JSON
row. Rows are always appended to ``logs/traces.jsonl`` locally; when a Hugging
Face write token is present (``HF_TOKEN``), each row is *also* pushed to the
configured HF Dataset on a daemon thread (non-blocking — the user never waits on
the write). With no token the push is a silent no-op, so nothing breaks locally.

Both successful calls and fallback activations are logged (``used_fallback``),
so the dataset reflects exactly what the model did vs. what the safety net did.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone

from discoverroute import config

LOG_DIR = config.PROJECT_ROOT / "logs"
TRACES_PATH = LOG_DIR / "traces.jsonl"
PLANS_PATH = LOG_DIR / "plans.jsonl"

# Monotonic, process-local counter so concurrently-written HF filenames never
# collide (datetime alone can repeat under load).
_seq_lock = threading.Lock()
_seq = 0


def _next_seq() -> int:
    global _seq
    with _seq_lock:
        _seq += 1
        return _seq


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_local(path, row: dict) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 - logging must never break a route
        pass


def _push_hf_async(row: dict, kind: str) -> None:
    """Best-effort async upload of one row to the trace dataset (token-gated)."""
    token = config.HF_TOKEN
    if not token:
        return  # stub: local-only until a token is provided on the Space
    seq = _next_seq()
    stamp = row.get("timestamp", _utcnow_iso()).replace(":", "-")

    def _push() -> None:
        try:
            from huggingface_hub import HfApi

            api = HfApi(token=token)
            api.upload_file(
                path_or_fileobj=json.dumps(row, ensure_ascii=False).encode("utf-8"),
                path_in_repo=f"{kind}/{stamp}-{seq:06d}.json",
                repo_id=config.TRACE_REPO,
                repo_type="dataset",
            )
        except Exception as exc:  # noqa: BLE001 - never break a route, but DO log it
            # A swallowed push failure (bad/scopeless token, wrong repo) is exactly
            # what made the trace dataset silently never appear. Log it so the Space
            # operator can see why instead of debugging blind.
            print(f"[trace] push to {config.TRACE_REPO} FAILED "
                  f"({type(exc).__name__}): {exc}", flush=True)

    threading.Thread(target=_push, daemon=True).start()


def selftest() -> None:
    """Boot-time check: is HF_TOKEN present and can it write to TRACE_REPO?

    Prints a clear verdict to the Space logs so a misconfigured secret (missing,
    wrong name, or a token without org write) is obvious instead of failing silently.
    """
    token = config.HF_TOKEN
    if not token:
        print("[trace] HF_TOKEN NOT detected — traces stay local only. Set a Space "
              "secret named exactly 'HF_TOKEN' to a write token to enable Hub push.",
              flush=True)
        return
    print(f"[trace] HF_TOKEN detected (len={len(token)}); testing write to "
          f"{config.TRACE_REPO} …", flush=True)
    try:
        from huggingface_hub import HfApi
        HfApi(token=token).upload_file(
            path_or_fileobj=b'{"selftest": true}',
            path_in_repo="_selftest/boot.json",
            repo_id=config.TRACE_REPO, repo_type="dataset",
            commit_message="trace selftest",
        )
        print(f"[trace] ✅ push OK — {config.TRACE_REPO} is writable; traces will flow.",
              flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[trace] ❌ push FAILED ({type(exc).__name__}): {exc} — the token "
              "likely lacks WRITE access to the build-small-hackathon org.", flush=True)


def log_trace(call_type: str, input_data: dict, output_data: dict,
              latency_ms: int, used_fallback: bool = False,
              model: str | None = None) -> dict:
    """Record one inference call (``vibe_extraction`` or ``narration``)."""
    row = {
        "timestamp": _utcnow_iso(),
        "call_type": call_type,
        "model": model or config.LLM_MODEL,
        "input": json.dumps(input_data, ensure_ascii=False),
        "output": json.dumps(output_data, ensure_ascii=False),
        "latency_ms": int(latency_ms),
        "used_fallback": bool(used_fallback),
    }
    _append_local(TRACES_PATH, row)
    _push_hf_async(row, "traces")
    return row


def log_plan(params: dict, summary: dict) -> dict:
    """Record one end-to-end plan_route call (feeds the Field Notes write-up)."""
    row = {"timestamp": _utcnow_iso(), "params": params, "summary": summary}
    _append_local(PLANS_PATH, row)
    _push_hf_async(row, "plans")
    return row
