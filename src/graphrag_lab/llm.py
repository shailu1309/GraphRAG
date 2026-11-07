"""The single Claude call site for the whole project.

Every token the project spends goes through complete(), and every call appends
one usage record to cfg.usage_ledger. Cost per phase is then a groupby on
`stage`, not a guess.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import anthropic

from graphrag_lab.config import Config

logger = logging.getLogger(__name__)

# Routes a refused request to a suitable model by refusal category.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

# complete() is called from worker threads; ledger lines must not interleave.
_LEDGER_LOCK = threading.Lock()


class LLMError(RuntimeError):
    """A response that returned HTTP 200 but cannot be used."""


@dataclass(frozen=True)
class Completion:
    text: str
    usage: dict  # the ledger record: tokens, cost, latency, model

    @property
    def json(self) -> dict:
        return json.loads(self.text)


def make_client(cfg: Config) -> anthropic.Anthropic:
    return anthropic.Anthropic(
        api_key=cfg.anthropic_api_key, max_retries=cfg.llm_max_retries
    )


def cost_usd(cfg: Config, model: str, input_tokens: int, output_tokens: int) -> float | None:
    prices = cfg.price_per_mtok.get(model)
    if prices is None:
        logger.warning("no price for %s in Config.price_per_mtok - cost not recorded", model)
        return None
    price_in, price_out = prices
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


def complete(
    client: anthropic.Anthropic,
    cfg: Config,
    *,
    model: str,
    prompt: str,
    max_tokens: int,
    effort: str,
    stage: str,
    system: str | None = None,
    json_schema: dict | None = None,
) -> Completion:
    """Send one user prompt, return the text and its usage record.

    With json_schema, the API constrains the reply to valid JSON for that schema;
    read it with Completion.json.
    """
    output_config: dict = {"effort": effort}
    if json_schema is not None:
        output_config["format"] = {"type": "json_schema", "schema": json_schema}
    params: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "output_config": output_config,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system is not None:
        params["system"] = system

    started = time.perf_counter()
    if model in cfg.fallback_models:
        response = client.beta.messages.create(
            **params, betas=[FALLBACK_BETA], fallbacks="default"
        )
    else:
        response = client.messages.create(**params)
    latency_s = time.perf_counter() - started

    usage = _record_usage(cfg, stage, model, response, latency_s)

    # Check stop_reason before content: a refusal still returns HTTP 200.
    if response.stop_reason == "refusal":
        raise LLMError(f"[{stage}] refused: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        raise LLMError(f"[{stage}] hit max_tokens={max_tokens} - raise it in Config")

    # Thinking is always on for these models, so filter by block type.
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if not text:
        raise LLMError(f"[{stage}] no text block (stop_reason={response.stop_reason})")
    return Completion(text=text, usage=usage)


def _record_usage(cfg: Config, stage: str, model: str, response, latency_s: float) -> dict:
    usage = response.usage
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "requested_model": model,
        "served_model": response.model,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cache_read_input_tokens": usage.cache_read_input_tokens or 0,
        "cost_usd": cost_usd(cfg, response.model, usage.input_tokens, usage.output_tokens),
        "latency_s": round(latency_s, 2),
        "request_id": response._request_id,
    }
    cfg.usage_ledger.parent.mkdir(parents=True, exist_ok=True)
    with _LEDGER_LOCK, cfg.usage_ledger.open("a") as f:
        f.write(json.dumps(record) + "\n")
    return record
