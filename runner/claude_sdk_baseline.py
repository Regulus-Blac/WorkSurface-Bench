"""Restricted Claude Agent SDK baseline for WorkSurface-Bench.

This adapter evaluates an off-the-shelf agent loop while preserving the
benchmark's controlled environment. The SDK receives only the seven canonical
RAG, table, and graph tools; Claude Code's built-in shell, filesystem, web, and
sub-agent tools are disabled.

The dependency is optional. Install it with::

    pip install -e ".[claude-sdk]"

Authentication can use the native Anthropic variables or the benchmark's
OpenAI-compatible proxy variables. The latter are translated for the SDK::

    ANTHROPIC_BASE_URL=... ANTHROPIC_API_KEY=...
    # or
    WSB_API_BASE=... WSB_API_KEY=...
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any

from worksurface.common import persona_slug

from .tools import ProfileTools

SERVER_NAME = "worksurface"
SETTING_NAME = "SDK"
DEFAULT_MAX_TURNS = 14
DEFAULT_MAX_TOOL_CALLS = 8

TOOL_NAMES = (
    "kb_search",
    "table_list",
    "table_describe",
    "table_query",
    "graph_search_entities",
    "graph_neighbors",
    "graph_traverse",
)
ALLOWED_TOOLS = tuple(f"mcp__{SERVER_NAME}__{name}" for name in TOOL_NAMES)


@dataclass
class SDKOutcome:
    answer: str
    total_tokens: int
    num_turns: int
    total_cost_usd: float | None
    session_id: str | None
    finalization_prompted: bool


def _load_sdk():
    try:
        import claude_agent_sdk
    except ImportError as exc:
        raise RuntimeError(
            'Claude Agent SDK is optional; install with '
            '`pip install -e ".[claude-sdk]"`.'
        ) from exc
    return claude_agent_sdk


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def _tool_result(value: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": _json_text(value)}]}


def build_sdk_server(
    profile_tools: ProfileTools,
    max_tool_calls: int = DEFAULT_MAX_TOOL_CALLS,
):
    """Bind the canonical benchmark tools to one in-process SDK MCP server."""
    sdk = _load_sdk()
    tool = sdk.tool

    def invoke(func, *args, **kwargs):
        if len(profile_tools.trace) >= max_tool_calls:
            return _tool_result(
                {
                    "error": "tool_budget_exhausted",
                    "instruction": "No tool calls remain; return final_answer now.",
                }
            )
        return _tool_result(func(*args, **kwargs))

    @tool(
        "kb_search",
        "Search task-scoped workspace documents and return grounded snippets.",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "k": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    )
    async def kb_search(args):
        return invoke(
            profile_tools.kb_search,
            args["query"],
            int(args.get("k", 3)),
        )

    @tool(
        "table_list",
        "List the task-scoped SQL views and their row counts.",
        {"type": "object", "properties": {}, "additionalProperties": False},
    )
    async def table_list(_args):
        return invoke(profile_tools.table_list)

    @tool(
        "table_describe",
        "Return the columns and row count for one task-scoped SQL view.",
        {
            "type": "object",
            "properties": {"view": {"type": "string"}},
            "required": ["view"],
            "additionalProperties": False,
        },
    )
    async def table_describe(args):
        return invoke(profile_tools.table_describe, args["view"])

    @tool(
        "table_query",
        "Execute a read-only SELECT or WITH query over task-scoped SQL views.",
        {
            "type": "object",
            "properties": {"sql": {"type": "string"}},
            "required": ["sql"],
            "additionalProperties": False,
        },
    )
    async def table_query(args):
        return invoke(profile_tools.table_query, args["sql"])

    @tool(
        "graph_search_entities",
        "Find dependency-graph node IDs matching a query.",
        {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
            "additionalProperties": False,
        },
    )
    async def graph_search_entities(args):
        return invoke(profile_tools.graph_search_entities, args["query"])

    @tool(
        "graph_neighbors",
        "Return outgoing dependency edges from one graph node.",
        {
            "type": "object",
            "properties": {"node": {"type": "string"}},
            "required": ["node"],
            "additionalProperties": False,
        },
    )
    async def graph_neighbors(args):
        return invoke(profile_tools.graph_neighbors, args["node"])

    @tool(
        "graph_traverse",
        "Traverse dependency edges from a graph node, optionally by relation.",
        {
            "type": "object",
            "properties": {
                "node": {"type": "string"},
                "rel": {"type": ["string", "null"]},
                "depth": {"type": "integer", "minimum": 1, "maximum": 4},
            },
            "required": ["node"],
            "additionalProperties": False,
        },
    )
    async def graph_traverse(args):
        return invoke(
            profile_tools.graph_traverse,
            args["node"],
            rel=args.get("rel"),
            depth=int(args.get("depth", 2)),
        )

    return sdk.create_sdk_mcp_server(
        name=SERVER_NAME,
        version="1.0.0",
        tools=[
            kb_search,
            table_list,
            table_describe,
            table_query,
            graph_search_entities,
            graph_neighbors,
            graph_traverse,
        ],
    )


def _sdk_environment() -> dict[str, str]:
    base = os.environ.get("ANTHROPIC_BASE_URL") or os.environ.get("WSB_API_BASE")
    key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("WSB_API_KEY")
    if not (base and key):
        raise RuntimeError(
            "Claude SDK baseline requires ANTHROPIC_BASE_URL + "
            "ANTHROPIC_API_KEY (or WSB_API_BASE + WSB_API_KEY)."
        )
    # OpenAI-compatible configs commonly end in /v1, while Claude Code itself
    # appends /v1/messages to the base URL.
    base = base.rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    return {"ANTHROPIC_BASE_URL": base, "ANTHROPIC_API_KEY": key}


def _usage_tokens(usage: dict[str, Any] | None) -> int:
    usage = usage or {}
    return sum(
        int(usage.get(key, 0) or 0)
        for key in (
            "input_tokens",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
            "output_tokens",
        )
    )


def _system_prompt(task: dict) -> str:
    task_node = f"task_{task['source']['task_id']}"
    answer_type = task.get("answer_type", "string")
    format_instruction = {
        "number": "final_answer must be a JSON number.",
        "list": "final_answer must be a JSON array.",
        "string": (
            "final_answer must be a JSON string. For a multi-part answer, join "
            "the requested fields in question order with '; ' and do not return "
            "a JSON object."
        ),
        "abstain": (
            "final_answer must be a JSON string; use INSUFFICIENT_EVIDENCE when "
            "the evidence does not support an answer."
        ),
    }.get(answer_type, "final_answer must be a JSON string.")
    return (
        "You are an enterprise data agent evaluated in a controlled benchmark. "
        "Use only the provided WorkSurface tools; do not answer from unsupported "
        "prior knowledge. Select whichever document, table, and dependency-graph "
        "surfaces are necessary, retrieve the evidence, and then answer the "
        "question. Your workspace graph entry node is "
        f'"{task_node}". File nodes use "t<id>::<filename>"; return bare '
        "filenames in the final answer. Return only the final answer: a bare "
        "number for numeric questions, a JSON array for list questions, a short "
        "string otherwise, or INSUFFICIENT_EVIDENCE when the available evidence "
        "does not support an answer. Do not include explanation or supporting "
        f"prose in final_answer. {format_instruction}"
    )


def _final_answer_schema(task: dict) -> dict[str, Any]:
    answer_type = task.get("answer_type")
    if answer_type == "number":
        value_schema: dict[str, Any] = {"type": "number"}
    elif answer_type == "list":
        value_schema = {"type": "array"}
    else:
        value_schema = {"type": "string"}
    return {
        "type": "object",
        "properties": {"final_answer": value_schema},
        "required": ["final_answer"],
        "additionalProperties": False,
    }


def _answer_text(value: Any) -> str:
    if isinstance(value, (list, dict)):
        return _json_text(value)
    if value is None:
        return "INSUFFICIENT_EVIDENCE"
    return str(value)


async def _run_agent(
    task: dict,
    model: str,
    profile_tools: ProfileTools,
    max_turns: int,
    max_tool_calls: int,
) -> SDKOutcome:
    sdk = _load_sdk()
    server = build_sdk_server(profile_tools, max_tool_calls=max_tool_calls)
    options = sdk.ClaudeAgentOptions(
        model=model,
        system_prompt=_system_prompt(task),
        tools=[],
        allowed_tools=list(ALLOWED_TOOLS),
        disallowed_tools=[
            "Bash",
            "Read",
            "Write",
            "Edit",
            "Glob",
            "Grep",
            "WebFetch",
            "WebSearch",
            "Task",
            "Skill",
        ],
        mcp_servers={SERVER_NAME: server},
        strict_mcp_config=True,
        permission_mode="dontAsk",
        max_turns=max_turns,
        setting_sources=[],
        skills=[],
        env=_sdk_environment(),
        output_format={
            "type": "json_schema",
            "schema": _final_answer_schema(task),
        },
    )

    answer = ""
    result_message = None
    finalization_prompted = False

    async def receive_once(client):
        nonlocal answer, result_message
        result_message = None
        async for message in client.receive_response():
            if isinstance(message, sdk.AssistantMessage):
                text = "".join(
                    block.text
                    for block in message.content
                    if isinstance(block, sdk.TextBlock)
                ).strip()
                if text:
                    answer = text
            elif isinstance(message, sdk.ResultMessage):
                result_message = message

    async with sdk.ClaudeSDKClient(options=options) as client:
        await client.query(f"QUESTION: {task['question']}")
        await receive_once(client)
        if result_message and result_message.subtype == "error_max_turns":
            # Match the hand-controlled ReAct runner: after the interaction
            # budget, allow one answer-only continuation with the accumulated
            # conversation, but execute no additional WorkSurface calls.
            finalization_prompted = True
            await client.query(
                "The interaction budget is exhausted. Do not request any more "
                "tools. Return the structured final_answer now using the "
                "evidence already obtained."
            )
            await receive_once(client)

    if result_message is None:
        raise RuntimeError("Claude Agent SDK returned no ResultMessage")
    if result_message.is_error:
        details = "; ".join(result_message.errors or [])
        raise RuntimeError(
            f"Claude Agent SDK failed ({result_message.subtype}): {details}"
        )
    structured = result_message.structured_output
    if isinstance(structured, dict) and "final_answer" in structured:
        answer = _answer_text(structured["final_answer"])
    elif result_message.result:
        answer = result_message.result.strip()
    if not answer:
        answer = "INSUFFICIENT_EVIDENCE"

    return SDKOutcome(
        answer=answer,
        total_tokens=_usage_tokens(result_message.usage),
        num_turns=result_message.num_turns,
        total_cost_usd=result_message.total_cost_usd,
        session_id=result_message.session_id,
        finalization_prompted=finalization_prompted,
    )


def run_claude_sdk_task(
    task: dict,
    model: str,
    out_root: str,
    max_turns: int = DEFAULT_MAX_TURNS,
    max_tool_calls: int = DEFAULT_MAX_TOOL_CALLS,
) -> dict:
    """Run one task and return the canonical WorkSurface trace."""
    slug = persona_slug(task["source"].get("persona", ""))
    profile_tools = ProfileTools(
        out_root,
        slug,
        source_task_id=str(task["source"]["task_id"]),
    )
    try:
        outcome = asyncio.run(
            _run_agent(
                task,
                model,
                profile_tools,
                max_turns=max_turns,
                max_tool_calls=max_tool_calls,
            )
        )
    finally:
        profile_tools.close()

    answer = outcome.answer
    return {
        "id": task["id"],
        "setting": SETTING_NAME,
        "model": f"claude-agent-sdk:{model}",
        "chosen_surfaces": sorted(profile_tools.surfaces_used),
        "rag_files": sorted(profile_tools.rag_files),
        "tables": sorted(profile_tools.tables_used),
        "graph_nodes": sorted(profile_tools.graph_nodes),
        "answer": answer,
        "total_tokens": outcome.total_tokens,
        "tool_trace": profile_tools.trace,
        "question_text": task["question"],
        "output_text": answer,
        "sdk": {
            "name": "claude-agent-sdk",
            "max_turns": max_turns,
            "max_tool_calls": max_tool_calls,
            "num_turns": outcome.num_turns,
            "total_cost_usd": outcome.total_cost_usd,
            "session_id": outcome.session_id,
            "finalization_prompted": outcome.finalization_prompted,
            "allowed_tools": list(ALLOWED_TOOLS),
        },
    }
