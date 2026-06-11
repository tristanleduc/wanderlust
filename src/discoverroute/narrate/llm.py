"""Lazy Qwen3.5-9B client for narration/posture (≤32B, ZeroGPU).

Loaded only when narration explicitly enables the LLM (GPU present). Runs with
thinking disabled for fast, direct itinerary text. Kept isolated so importing the
rest of the app never pulls in the model.
"""
from __future__ import annotations

import functools

from discoverroute import config

try:
    import spaces  # ZeroGPU; effect-free off-Spaces
    _gpu = spaces.GPU(duration=120)
except Exception:  # noqa: BLE001 - not on a Space / package absent
    def _gpu(fn):
        return fn


@functools.lru_cache(maxsize=1)
def _pipe():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(config.LLM_MODEL)
    model = AutoModelForCausalLM.from_pretrained(
        config.LLM_MODEL, torch_dtype="auto", device_map="auto"
    )
    return tok, model


@_gpu
def generate(prompt: str, max_new_tokens: int = 320) -> str:
    tok, model = _pipe()
    messages = [{"role": "user", "content": prompt}]
    text = tok.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
        enable_thinking=False,  # Qwen3.5: direct answer, no <think> block
    )
    inputs = tok([text], return_tensors="pt").to(model.device)
    out = model.generate(
        **inputs, max_new_tokens=max_new_tokens,
        temperature=0.7, top_p=0.8, top_k=20, do_sample=True,
    )
    gen = out[0][inputs.input_ids.shape[1]:]
    return tok.decode(gen, skip_special_tokens=True).strip()
