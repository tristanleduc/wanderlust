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

# ZeroGPU reserves the requested ``duration`` seconds of quota *per call*, so a
# fat slice drains a day's allowance in a dozen requests (the live Space was
# erroring "180s requested vs. 170s left" then falling back to the template). A
# 1B model loading from cache + generating ≤480 tokens on an A10G finishes well
# inside 45s, so request that — ~3× more calls per day, with headroom over the
# first-call weight-load cost.
GPU_DURATION_S = 45

try:
    import spaces  # ZeroGPU; effect-free off-Spaces
    _gpu = spaces.GPU(duration=GPU_DURATION_S)
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
                  temperature: float | None = None,
                  enable_thinking: bool = False) -> str:
    """Run a chat completion. ``messages`` = [{"role","content"}, ...].

    MiniCPM5-1B is a hybrid-reasoning model (verified on the model card: built-in
    ``<think>`` template, switched by ``enable_thinking``). With thinking ON it
    first emits a ``<think>…</think>`` reasoning block and *then* the answer; we
    strip the block and return only the answer, so callers parse clean output.
    With thinking OFF the template injects an empty block and there's nothing to
    strip — the fast direct path.

    ``temperature`` defaults to the model card's recommended sampling for the
    chosen mode (Think 0.9 / No-Think 0.7), both with top_p 0.95.
    """
    tok, model = _load()
    if temperature is None:
        temperature = 0.9 if enable_thinking else 0.7
    text = tok.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True,
        enable_thinking=enable_thinking,
    )
    inputs = tok([text], return_tensors="pt").to(model.device)
    out = model.generate(
        **inputs, max_new_tokens=max_new_tokens,
        temperature=temperature, top_p=0.95, top_k=20, do_sample=True,
    )
    gen = out[0][inputs.input_ids.shape[1]:]
    decoded = tok.decode(gen, skip_special_tokens=True).strip()
    if enable_thinking:
        # Keep only what follows the reasoning block. If the model never closed
        # </think> (reasoning ran to the token budget), there's no usable answer —
        # return "" so the caller falls back rather than parsing half a thought.
        if "</think>" in decoded:
            decoded = decoded.split("</think>")[-1].strip()
        else:
            decoded = ""
    return decoded
