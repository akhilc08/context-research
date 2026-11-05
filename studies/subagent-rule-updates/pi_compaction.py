"""A faithful port of pi 1.5.0 compaction for OpenAI-style chat histories.

Reproduced from dist/core/compaction/compaction.js: the cut point that keeps the most
recent `keepRecentTokens` verbatim (default 20,000, chars/4 estimates), split-turn
handling, the [User]/[Assistant]/[Tool result] transcript with tool results cut to 2,000
characters, the structured summary and update prompts, cumulative file lists appended to
the summary, and the summary message pi inserts into context. Prompts are copied byte
for byte into pi_compaction_prompts.json.

Not reproduced: when pi triggers compaction (near the context window). The caller decides.
pi's read/write/edit tools map to read_file/write_file here. List calls have no path.
"""
from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

P = json.loads((Path(__file__).resolve().parent / "pi_compaction_prompts.json").read_text())
KEEP_RECENT_TOKENS = 20000
TOOL_RESULT_MAX_CHARS = 2000
FILE_TOOLS = {"read_file": "read", "write_file": "write"}


@dataclass
class PiState:
    """What pi keeps between compactions: the last summary and cumulative file lists."""
    previous_summary: str | None = None
    read: set[str] = field(default_factory=set)
    written: set[str] = field(default_factory=set)


def _js(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _args(call: dict) -> dict:
    try:
        value = json.loads(call["function"].get("arguments") or "{}")
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def estimate_tokens(message: dict) -> int:
    role = message["role"]
    if role == "assistant":
        chars = len(message.get("content") or "")
        if isinstance(message.get("reasoning"), str):
            chars += len(message["reasoning"])
        for call in message.get("tool_calls") or []:
            chars += len(call["function"]["name"]) + len(_js(_args(call)))
        return math.ceil(chars / 4)
    return math.ceil(len(message.get("content") or "") / 4)


def truncate_for_summary(text: str, max_chars: int = TOOL_RESULT_MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n\n[... {len(text) - max_chars} more characters truncated]"


def serialize_conversation(messages: list[dict]) -> str:
    parts = []
    for msg in messages:
        if msg["role"] == "user":
            if msg.get("content"):
                parts.append(f"[User]: {msg['content']}")
        elif msg["role"] == "assistant":
            calls = [f"{c['function']['name']}(" + ", ".join(f"{k}={_js(v)}" for k, v in _args(c).items()) + ")"
                     for c in msg.get("tool_calls") or []]
            if msg.get("content"):
                parts.append(f"[Assistant]: {msg['content']}")
            if calls:
                parts.append(f"[Assistant tool calls]: {'; '.join(calls)}")
        elif msg["role"] == "tool":
            if msg.get("content"):
                parts.append(f"[Tool result]: {truncate_for_summary(msg['content'])}")
    return "\n\n".join(parts)


def find_cut_point(history: list[dict], start: int, end: int, keep_recent_tokens: int = KEEP_RECENT_TOKENS) -> dict:
    cut_points = [i for i in range(start, end) if history[i]["role"] in ("user", "assistant")]
    if not cut_points:
        return {"first_kept": start, "turn_start": -1, "split": False}
    accumulated, cut = 0, cut_points[0]
    for i in range(end - 1, start - 1, -1):
        tokens = estimate_tokens(history[i])
        if tokens == 0:
            continue
        accumulated += tokens
        if accumulated >= keep_recent_tokens:
            cut = next((c for c in cut_points if c >= i), cut_points[-1])
            break
    starts_turn = history[cut]["role"] == "user"
    turn_start = -1 if starts_turn else next((i for i in range(cut, start - 1, -1) if history[i]["role"] == "user"), -1)
    return {"first_kept": cut, "turn_start": turn_start, "split": not starts_turn and turn_start != -1}


def _file_ops(messages: list[dict], state: PiState) -> None:
    for msg in messages:
        for call in msg.get("tool_calls") or [] if msg["role"] == "assistant" else []:
            kind, path = FILE_TOOLS.get(call["function"]["name"]), _args(call).get("path")
            if kind and isinstance(path, str):
                (state.read if kind == "read" else state.written).add(path)


def format_file_operations(state: PiState) -> str:
    modified = sorted(state.written)
    read_only = sorted(p for p in state.read if p not in state.written)
    sections = []
    if read_only:
        sections.append("<read-files>\n" + "\n".join(read_only) + "\n</read-files>")
    if modified:
        sections.append("<modified-files>\n" + "\n".join(modified) + "\n</modified-files>")
    return "" if not sections else "\n\n" + "\n\n".join(sections)


def _complete(client: Any, prompt: str, tag: str) -> tuple[str, dict]:
    messages = [{"role": "system", "content": P["SUMMARIZATION_SYSTEM_PROMPT"]}, {"role": "user", "content": prompt}]
    response = client.complete(messages, tag=tag)
    choice = response["choices"][0]
    text = choice["message"].get("content") or ""
    if choice.get("finish_reason") != "stop" or not text.strip() or choice["message"].get("tool_calls"):
        raise RuntimeError("pi summarization did not produce a complete summary")
    return text, {"messages": messages, "response": response}


def generate_summary(client: Any, messages: list[dict], previous_summary: str | None, tag: str) -> tuple[str, dict]:
    prompt = f"<conversation>\n{serialize_conversation(messages)}\n</conversation>\n\n"
    if previous_summary:
        prompt += f"<previous-summary>\n{previous_summary}\n</previous-summary>\n\n"
    prompt += P["UPDATE_SUMMARIZATION_PROMPT"] if previous_summary else P["SUMMARIZATION_PROMPT"]
    return _complete(client, prompt, tag)


def generate_turn_prefix_summary(client: Any, messages: list[dict], tag: str) -> tuple[str, dict]:
    prompt = f"# Conversation\n{serialize_conversation(messages)}\n\n# Instructions\n{P['TURN_PREFIX_SUMMARIZATION_PROMPT']}"
    return _complete(client, prompt, tag)


def summary_message(summary: str) -> dict:
    return {"role": "user", "content": P["COMPACTION_SUMMARY_PREFIX"] + summary + P["COMPACTION_SUMMARY_SUFFIX"]}


def compact(client: Any, history: list[dict], state: PiState, tag: str) -> tuple[list[dict], dict]:
    """Return the compacted history and an event record. `state` is updated in place."""
    start = 1 if state.previous_summary is not None else 0  # history[0] is the previous summary message.
    cut = find_cut_point(history, start, len(history), KEEP_RECENT_TOKENS)
    history_end = cut["turn_start"] if cut["split"] else cut["first_kept"]
    to_summarize = history[start:history_end]
    prefix = history[cut["turn_start"]:cut["first_kept"]] if cut["split"] else []
    if not to_summarize and not prefix:
        return history, {"skipped": True, "cut": cut}
    _file_ops(to_summarize + prefix, state)
    calls = []
    if cut["split"] and prefix:
        history_text = state.previous_summary if state.previous_summary is not None else "No prior history."
        if to_summarize:
            history_text, call = generate_summary(client, to_summarize, state.previous_summary, f"{tag}/history")
            calls.append(call)
        prefix_text, call = generate_turn_prefix_summary(client, prefix, f"{tag}/turn_prefix")
        calls.append(call)
        summary = f"{history_text}\n\n---\n\n**Turn Context (split turn):**\n\n{prefix_text}"
    else:
        summary, call = generate_summary(client, to_summarize, state.previous_summary, tag)
        calls.append(call)
    summary += format_file_operations(state)
    state.previous_summary = summary
    new_history = [summary_message(summary)] + copy.deepcopy(history[cut["first_kept"]:])
    return new_history, {"skipped": False, "cut": cut, "summarized_messages": len(to_summarize), "turn_prefix_messages": len(prefix),
                         "kept_messages": len(history) - cut["first_kept"], "summary": summary, "summary_chars": len(summary),
                         "calls": calls, "history_after_chars": sum(len(m.get("content") or "") for m in new_history)}
