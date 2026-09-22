"""Summarize hidden blocks with a cheap model so the stub carries the gist."""

from __future__ import annotations

from typing import Protocol

from winnow.config import Config
from winnow.transcript import Task

SYSTEM = (
    "You summarize one section of a tool output that a coding agent will not see in full. "
    "Write at most three sentences, plain text, no preamble. Preserve anything the agent "
    "might need later: identifiers, file paths, line numbers, counts, versions, and any "
    "error or warning text verbatim. If the section is uniform boilerplate, say so in one sentence."
)


class Summarizer(Protocol):
    name: str

    def summarize(self, text: str, task: Task, describe: str) -> str | None: ...


class ClaudeSummarizer:
    name = "claude"

    def __init__(self, model: str, timeout: float = 20.0) -> None:
        import anthropic

        self._anthropic = anthropic
        self._client = anthropic.Anthropic(timeout=timeout, max_retries=1)
        self.model = model

    def summarize(self, text: str, task: Task, describe: str) -> str | None:
        prompt = (
            f"Tool call: {describe}\n"
            f"Current task: {task.user_request or '(unknown)'}\n\n"
            f"Section to summarize:\n<section>\n{text}\n</section>"
        )
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=300,
                system=SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
        except self._anthropic.RateLimitError:
            return None
        except self._anthropic.APIStatusError:
            return None
        except self._anthropic.APIConnectionError:
            return None
        summary = " ".join(block.text for block in response.content if block.type == "text").strip()
        return summary or None


def build_summarizer(cfg: Config) -> Summarizer | None:
    if not cfg.summary:
        return None
    try:
        return ClaudeSummarizer(cfg.summary_model)
    except ImportError:
        return None
