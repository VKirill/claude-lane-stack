"""The judge: a System One model that answers typed questions with probabilities.

Two backends share one interface so the rest of winnow never knows which is in
use:

- ``typesafe``: TypeSafe's Jev via ``typesafe-sdk``. Calibrated, fast, cheap.
- ``adapter``: TypeSafe's own ``system-one-adapter``, which emulates the same
  request and response on top of an LLM (Claude by default). Not calibrated,
  but it lets you build and test before you have a Jev key.

Questions are built with ``typesafe_sdk.Noul``; the adapter accepts the same
objects.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from winnow.config import Config


@dataclass(frozen=True)
class JudgeResult:
    probabilities: dict[str, float]
    model: str
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int


class Judge(Protocol):
    name: str

    def nouls(self, state: Any, questions: Mapping[str, Any]) -> JudgeResult: ...


def _noul_value(answer: Any) -> float | None:
    value = getattr(answer, "noul", None)
    if value is None and isinstance(answer, dict):
        value = answer.get("noul")
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _collect(response: Any, questions: Mapping[str, Any], model: str, started: float) -> JudgeResult:
    answers = getattr(response, "answers", None) or {}
    probabilities: dict[str, float] = {}
    for key in questions:
        answer = answers.get(key) if hasattr(answers, "get") else None
        value = _noul_value(answer)
        if value is not None:
            probabilities[key] = value
    usage = getattr(response, "usage", None)
    return JudgeResult(
        probabilities=probabilities,
        model=str(getattr(response, "model", None) or model),
        input_tokens=getattr(usage, "input_tokens", None),
        output_tokens=getattr(usage, "output_tokens", None),
        latency_ms=int((time.perf_counter() - started) * 1000),
    )


class TypeSafeJudge:
    name = "typesafe"

    def __init__(self, model: str, timeout: float) -> None:
        from typesafe_sdk import RetryPolicy, TypeSafeClient

        self.model = model
        self._client = TypeSafeClient(
            model=model,
            retry=RetryPolicy(max_retries=1, timeout=timeout),
            timeout=timeout,
        )

    def nouls(self, state: Any, questions: Mapping[str, Any]) -> JudgeResult:
        started = time.perf_counter()
        response = self._client.system_one(state, questions)
        return _collect(response, questions, self.model, started)


class AdapterJudge:
    name = "adapter"

    def __init__(self, provider: str, model: str) -> None:
        from system_one_adapter import SystemOneAdapterClient

        self.model = model
        self._client = SystemOneAdapterClient(
            structured_outputs=True,
            llm_answer_mode="probabilities",
            normalize_probabilities=True,
            provider=provider,  # type: ignore[arg-type]
            model=model,
        )

    def nouls(self, state: Any, questions: Mapping[str, Any]) -> JudgeResult:
        started = time.perf_counter()
        response = self._client.system_one(state, questions)
        return _collect(response, questions, self.model, started)


def build_judge(cfg: Config) -> Judge | None:
    if cfg.judge in ("off", "none", "0"):
        return None
    if cfg.judge == "typesafe":
        return TypeSafeJudge(cfg.model, cfg.judge_timeout)
    if cfg.judge == "adapter":
        return AdapterJudge(cfg.adapter_provider, cfg.adapter_model)
    raise ValueError(f"unknown WINNOW_JUDGE={cfg.judge!r}; expected typesafe, adapter, or off")
