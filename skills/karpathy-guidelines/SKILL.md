---
name: karpathy-guidelines
description: Behavioral guidelines to reduce common LLM coding mistakes. Use when writing, reviewing, or refactoring code. Derived from Andrej Karpathy's LLM coding pitfalls.
license: MIT
---

# Karpathy Guidelines

Derived from [Karpathy on LLM coding pitfalls](https://x.com/karpathy/status/2015883857489522876). Bias: caution over reckless speed. Trivial tasks — use judgment.

## 1. Think Before Coding

Don't assume. Don't hide confusion. Surface tradeoffs.

- State assumptions explicitly. If uncertain, ask.  
- Multiple interpretations → present them; don't pick silently.  
- Prefer simpler approaches; push back when warranted.  
- Unclear → stop, name the confusion, ask.

## 2. Simplicity First

Minimum code that solves the problem. Nothing speculative.

- No features beyond the ask.  
- No single-use abstractions or fake "flexibility".  
- No error handling for impossible cases.  
- 200 lines that could be 50 → rewrite.

## 3. Surgical Changes

Touch only what you must. Clean up only your own mess.

- Don't "improve" adjacent code, comments, or formatting.  
- Don't refactor what isn't broken.  
- Match existing style.  
- Unrelated dead code → mention, don't delete.  
- Remove only what **your** change made unused.

**Test:** every changed line traces to the user request.

## 4. Goal-Driven Execution

Define success criteria. Loop until verified.

- "Add validation" → tests for invalid inputs, then make them pass.  
- "Fix the bug" → failing test first, then green.  
- Multi-step: `step → verify: command` list.

Strong criteria → autonomous loop. Weak ("make it work") → clarify first.

## Autonomy zone (MAY)

Inside the task scope, decide tech details, edit order, and local design without asking.  
Do not ask the user what you can look up in the repo or docs.
