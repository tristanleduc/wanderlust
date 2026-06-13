"""Lazy MiniCPM5-1B client (Tiny Titan ≤4B, in-Space ZeroGPU).

One model serves both inference calls — vibe→weights extraction and route
narration — so the weights load once and are reused. Standard LlamaForCausalLM
(no custom kernels). Loaded only when a GPU is present (off-Space the
``@spaces.GPU`` decorator is an identity no-op, and callers fall back), so
importing the rest of the app never pulls in torch/transformers.
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
def _load():
    """Load (tokenizer, model) once. MiniCPM5-1B → fp16, device_map=auto."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(config.LLM_MODEL, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        config.LLM_MODEL,
        torch_dtype=torch.float16,
        device_map="auto",
        trust_remote_code=True,
    )
    return tok, model


@_gpu
def run_inference(messages: list[dict], max_new_tokens: int = 320,
                  temperature: float = 0.7) -> str:
    """Run a chat completion. ``messages`` = [{"role","content"}, ...]."""
    tok, model = _load()
    text = tok.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tok([text], return_tensors="pt").to(model.device)
    out = model.generate(
        **inputs, max_new_tokens=max_new_tokens,
        temperature=temperature, top_p=0.8, top_k=20, do_sample=True,
    )
    gen = out[0][inputs.input_ids.shape[1]:]
    return tok.decode(gen, skip_special_tokens=True).strip()
