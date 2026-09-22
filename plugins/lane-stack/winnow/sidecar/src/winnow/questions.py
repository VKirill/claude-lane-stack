"""Question sets: the words the judge is asked with.

Phrasing is a lever. Each set below is a hypothesis about what makes a block
"needed", and ``winnow replay judge --questions <name>`` scores it against the
same cases as every other set. ``WINNOW_QUESTIONS`` selects the one the live
hook uses.
"""

from __future__ import annotations

from typing import Any, Callable

from winnow.chunk import Block

ERROR_QUESTION = dict(
    instructions=(
        "Does the tool output (the whole of `blocks`) show an error, failure, warning, "
        "or unexpected result that the assistant needs to know about?"
    ),
    criteria={
        "true": "Tracebacks, non-zero exits, 'not found', permission errors, failing tests, or output that contradicts what `task` expected.",
        "false": "Ordinary successful output.",
    },
)


def _default(block: Block) -> dict[str, Any]:
    return dict(
        instructions=f"Is `blocks.{block.id}` needed to accomplish `task`? Judge it against `task` and `tool`.",
        criteria={
            "true": (
                "The block holds content the task depends on: matching code or text, results, "
                "values the user asked for, definitions being edited, or anything referenced by the task."
            ),
            "false": (
                "The block is boilerplate, unrelated to the task, repetitive noise, or something "
                "the task does not depend on."
            ),
        },
    )


def _structured(block: Block) -> dict[str, Any]:
    return dict(
        instructions=(
            f"Would the assistant have to look at `blocks.{block.id}` to accomplish `task` correctly? "
            "Judge only this block, against `task` and `tool`."
        ),
        criteria={
            "true": {
                "what": "The assistant must read this text to do the task right.",
                "examples": [
                    "the function, class, or setting the user asked to change",
                    "the failing test, the assertion, and the traceback",
                    "the search hit for the symbol in question",
                    "the value or record the task must report or compare",
                ],
            },
            "false": {
                "what": "The task can be completed correctly without ever reading this block.",
                "not_for": "Do not mark a block needed only because it comes from the same file or the same command as something that is needed.",
                "examples": [
                    "license headers, imports, and module docstrings",
                    "functions and settings unrelated to the request",
                    "repeated success lines in a build or test log",
                    "listings of items the task does not mention",
                ],
            },
        },
    )


def _strict(block: Block) -> dict[str, Any]:
    return dict(
        instructions=(
            f"Is `blocks.{block.id}` directly about `task`? Answer yes only if it contains code, output, "
            "or values that `task` explicitly refers to, or that must change to accomplish `task`."
        ),
        criteria={
            "true": "Directly referenced by the task, or must be edited or acted on to complete it.",
            "false": "Context, background, boilerplate, or anything the task does not name or require.",
        },
    )


QUESTION_SETS: dict[str, Callable[[Block], dict[str, Any]]] = {
    "default": _default,
    "structured": _structured,
    "strict": _strict,
}


def build_questions(name: str, blocks: list[Block]) -> dict[str, Any]:
    """One Noul per block plus the shared error question. Imports the SDK lazily."""
    from typesafe_sdk import Noul

    try:
        make = QUESTION_SETS[name]
    except KeyError:
        raise ValueError(f"unknown question set {name!r}; expected one of {', '.join(QUESTION_SETS)}") from None
    questions: dict[str, Any] = {block.id: Noul(**make(block)) for block in blocks}
    questions["error_present"] = Noul(**ERROR_QUESTION)
    return questions
