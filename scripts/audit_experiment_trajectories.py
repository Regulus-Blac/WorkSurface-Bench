#!/usr/bin/env python3
"""Replay and audit every saved C0-C3 experiment trajectory.

No model calls are made. Tool calls are replayed against each run's locked
workspace so the audit can recover the observation that the ReAct loop sent
to the model (including its 1,500-character truncation). The output separates
signal exposure, successful proper-subset bypasses, expected abstentions, and
ordinary retrieval/integration failures.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

from runner.react import _dispatch, _truncate
from runner.tools import ProfileTools
from worksurface.common import persona_slug


GROUPS = [
    ("C0-pro", "c0_pro_20260921", "valid"),
    ("C1-pro", "c1_pro_20260921", "valid"),
    ("C2a", "c2a_pro_20260921", "valid_sentinel"),
    ("C2b-v1", "c2b_pro_20260921", "invalid_join_contract"),
    ("C2b-r2", "c2b_pro_r2_20260921", "valid_sentinel"),
    ("C2-final-v1", "c2_final_pro_20260921", "diagnostic_full_failure"),
    ("C2-final-r2", "c2_final_pro_r2_20260921", "diagnostic_full_failure"),
    ("C3-v1", "c3_pro_20260921", "invalid_sql_semantics"),
    ("C3-r2", "c3_pro_r2_20260921", "valid_causal_gate"),
]

INSUFFICIENT = "INSUFFICIENT_EVIDENCE"
RAW_TASK_RE = re.compile(r"(?<![A-Za-z0-9])(?:task[_ ]?\d+|t\d+(?=__|::))", re.I)
FILENAME_RE = re.compile(r"\b[^\s\"']+\.(?:md|txt|csv|xlsx|pdf)\b", re.I)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_single_jsonl(path: Path) -> dict:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    if len(rows) != 1:
        raise ValueError(f"{path}: expected one row, found {len(rows)}")
    return rows[0]


def write_json_atomic(path: Path, payload: Any) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def write_text_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def answer_components(answer: Any) -> list[str]:
    if isinstance(answer, dict):
        values = answer.values()
    elif isinstance(answer, list):
        values = answer
    else:
        text = str(answer)
        if ";" in text:
            values = text.split(";")
        elif ": " in text:
            values = text.split(": ")
        else:
            values = [text]
    return [str(value).strip().strip('"\'') for value in values
            if str(value).strip()]


def contains_component(text: str, component: str) -> bool:
    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?%?", component):
        return re.search(
            rf"(?<![A-Za-z0-9.]){re.escape(component)}(?![A-Za-z0-9.])",
            text,
            flags=re.I,
        ) is not None
    return component.casefold() in text.casefold()


def recursive_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(str(key))
            keys.update(recursive_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(recursive_keys(item))
    return keys


def inventory(data_root: str, task: dict, source_task_id: str | None) -> dict:
    slug = task.get("profile_slug") or persona_slug(task["source"].get("persona", ""))
    tools = ProfileTools(
        data_root,
        slug,
        source_task_id=source_task_id,
        contract=task.get("tool_contract", "v1"),
    )
    try:
        return {
            "rag_documents": len(tools.kb),
            "table_views": len(tools.views),
            "graph_nodes": len(tools._nodes),
        }
    finally:
        tools.close()


def replay(task: dict, trace: dict, manifest: dict) -> tuple[list[dict], dict, dict]:
    scope = manifest["scope"]
    source_task_id = str(task["source"]["task_id"]) if scope == "task" else None
    data_root = manifest["data_root"]
    slug = task.get("profile_slug") or persona_slug(task["source"].get("persona", ""))
    tools = ProfileTools(
        data_root,
        slug,
        source_task_id=source_task_id,
        contract=task.get("tool_contract", "v1"),
    )
    calls = []
    try:
        actual_inventory = {
            "rag_documents": len(tools.kb),
            "table_views": len(tools.views),
            "graph_nodes": len(tools._nodes),
        }
        for index, saved in enumerate(trace.get("tool_trace", []), 1):
            before = len(tools.trace)
            observation = _dispatch(tools, saved.get("tool"), saved.get("args") or {})
            replay_summary = tools.trace[-1]["result"] if len(tools.trace) > before else None
            visible = _truncate(observation)
            keys = recursive_keys(observation)
            calls.append({
                "index": index,
                "tool": saved.get("tool"),
                "surface": saved.get("surface"),
                "args": saved.get("args") or {},
                "saved_result_summary": saved.get("result"),
                "replayed_result_summary": replay_summary,
                "summary_matches": replay_summary == saved.get("result"),
                "visible_observation": visible,
                "visible_chars": len(visible),
                "observation_truncated": visible.endswith("…(truncated)"),
                "observation_keys": sorted(keys),
            })
    finally:
        tools.close()
    persona_inventory = inventory(data_root, task, None)
    return calls, actual_inventory, persona_inventory


def original_id_map(group_manifest: dict) -> dict[tuple[str, str], str]:
    return {
        (row["public_id"], row["variant"]): row["original_id"]
        for row in group_manifest.get("matrix", [])
    }


def expected_gate_pass(stage: str, variant: str, answer: str,
                       answer_correct: bool) -> bool | None:
    if stage != "C3-r2":
        return None
    if variant in {"subset", "subset_table"}:
        return answer == INSUFFICIENT
    return answer_correct


def classify(row: dict) -> str:
    variant = row["variant"]
    is_subset = bool(row["missing_surfaces"])
    if row["stage"] == "C3-r2":
        return "causal_gate_pass" if row["gate_pass"] else "causal_gate_failure"
    if is_subset and row["answer_correct"]:
        return "confirmed_bypass"
    if is_subset and row["all_gold_components_context_visible"]:
        return "latent_closure_not_exploited"
    if is_subset:
        return "no_observed_subset_closure"
    if row["answer_correct"]:
        return "full_success"
    if row["answer"] == INSUFFICIENT:
        if row["all_gold_components_context_visible"]:
            return "synthesis_failure_after_exposure"
        if row["tool_calls"] >= 8:
            return "search_budget_exhaustion_or_integration_failure"
        if row["evidence_score"] == 1.0:
            return "evidence_or_gold_mismatch"
        return "retrieval_or_integration_failure"
    if variant in {"mutation", "negative"}:
        return "control_wrong_answer"
    return "wrong_answer"


def audit_run(stage: str, role: str, group_dir: Path, run_path: Path,
              group_manifest: dict, id_map: dict[tuple[str, str], str]) -> dict:
    stem = run_path.name.removesuffix(".run.jsonl")
    public_id, variant = stem.rsplit("__", 1)
    task_path = group_dir / f"{stem}.jsonl"
    status_path = group_dir / f"{stem}.status.json"
    score_path = group_dir / f"{stem}.run.scored.json"
    manifest_path = group_dir / f"{stem}.manifest.json"
    for path in (task_path, status_path, score_path, manifest_path):
        if not path.is_file():
            raise ValueError(f"{run_path}: missing {path.name}")
    task = read_single_jsonl(task_path)
    trace = read_single_jsonl(run_path)
    status = read_json(status_path)
    score_rows = read_json(score_path).get("per_task", [])
    manifest = read_json(manifest_path)
    if status.get("state") != "completed" or status.get("errors") != 0:
        raise ValueError(f"{run_path}: status is not a zero-error completion")
    if len(score_rows) != 1 or score_rows[0].get("id") != task["id"]:
        raise ValueError(f"{run_path}: score/task mismatch")
    if trace.get("id") != task["id"]:
        raise ValueError(f"{run_path}: trace/task mismatch")

    score = score_rows[0]
    calls, actual_inventory, persona_inventory = replay(task, trace, manifest)
    allowed = task.get("_allowed_surfaces")
    effective_allowed = set(allowed or ("rag", "table", "graph"))
    required = set(task.get("required_surfaces", []))
    missing = sorted(required - effective_allowed)
    question = task.get("question", "")
    visible_observations = "\n".join(call["visible_observation"] for call in calls)
    prompt_and_observations = question + "\n" + visible_observations
    components = answer_components(task.get("gold_answer"))
    question_components = [item for item in components if contains_component(question, item)]
    observation_components = [
        item for item in components if contains_component(visible_observations, item)
    ]
    context_components = [
        item for item in components if contains_component(prompt_and_observations, item)
    ]

    if "graph_entry_node" in task:
        graph_entry = task.get("graph_entry_node")
        graph_entry_kind = "public" if graph_entry else "none"
    else:
        graph_entry = f"task_{task['source']['task_id']}"
        graph_entry_kind = "legacy_raw_task"
    graph_allowed = "graph" in effective_allowed
    entry_calls = [
        call for call in calls
        if graph_entry and call["surface"] == "graph"
        and call["args"].get("node") == graph_entry
    ]
    observation_keys = {key for call in calls for key in call["observation_keys"]}
    visible_lower = visible_observations.casefold()
    question_lower = question.casefold()
    final_answer = str(trace.get("answer", ""))
    answer_correct = score["answer"]["score"] == 1.0

    row = {
        "stage": stage,
        "group_role": role,
        "run_group": group_dir.name,
        "original_id": id_map.get((public_id, variant), task["id"]),
        "public_id": task["id"],
        "variant": variant,
        "scope": manifest["scope"],
        "required_surfaces": sorted(required),
        "allowed_surfaces": sorted(effective_allowed),
        "missing_surfaces": missing,
        "called_surfaces": sorted({call["surface"] for call in calls}),
        "chosen_surfaces": trace.get("chosen_surfaces", []),
        "answer": final_answer,
        "gold_answer": task.get("gold_answer"),
        "answer_correct": answer_correct,
        "answer_score": score["answer"]["score"],
        "evidence_score": score["evidence"]["score"],
        "route_f1": score["route"]["f1"],
        "total_tokens": int(trace.get("total_tokens") or 0),
        "tool_calls": len(calls),
        "truncated_observation_calls": sum(
            call["observation_truncated"] for call in calls
        ),
        "replay_summary_mismatches": sum(not call["summary_matches"] for call in calls),
        "actual_inventory": actual_inventory,
        "persona_inventory": persona_inventory,
        "task_scope_reduction": {
            key: persona_inventory[key] - actual_inventory[key]
            for key in actual_inventory
        },
        "graph_entry": graph_entry,
        "graph_entry_kind": graph_entry_kind,
        "graph_entry_prompt_visible": graph_allowed and bool(graph_entry),
        "graph_entry_called": bool(entry_calls),
        "task_membership_observed": any(
            call["replayed_result_summary"] not in (None, [], {}, "not_found")
            for call in entry_calls
        ),
        "raw_task_label_in_question": bool(RAW_TASK_RE.search(question)),
        "opaque_work_item_in_question": "work_item_" in question_lower,
        "raw_task_label_in_observation": bool(RAW_TASK_RE.search(visible_observations)),
        "opaque_work_item_in_observation": "work_item_" in visible_lower,
        "source_file_field_visible": "source_file" in observation_keys,
        "source_task_provenance_visible": "source_task" in visible_lower,
        "table_row_metadata_visible": "rows" in observation_keys,
        "artifact_id_visible": "artifact_id" in observation_keys,
        "filename_like_observation": bool(FILENAME_RE.search(visible_observations)),
        "gold_components": components,
        "gold_components_in_question": question_components,
        "gold_components_in_observations": observation_components,
        "gold_components_in_context": context_components,
        "all_gold_components_observation_visible": bool(components)
        and len(observation_components) == len(components),
        "all_gold_components_context_visible": bool(components)
        and len(context_components) == len(components),
        "gate_pass": expected_gate_pass(
            stage, variant, final_answer, answer_correct
        ),
        "calls": calls,
    }
    row["classification"] = classify(row)
    return row


def summarize_stage(rows: list[dict], role: str) -> dict:
    classifications = Counter(row["classification"] for row in rows)
    variants = Counter(row["variant"] for row in rows)
    correct_variants = Counter(row["variant"] for row in rows if row["answer_correct"])
    exposure_fields = [
        "graph_entry_prompt_visible",
        "graph_entry_called",
        "task_membership_observed",
        "raw_task_label_in_question",
        "raw_task_label_in_observation",
        "opaque_work_item_in_question",
        "opaque_work_item_in_observation",
        "source_file_field_visible",
        "source_task_provenance_visible",
        "table_row_metadata_visible",
        "artifact_id_visible",
        "all_gold_components_observation_visible",
        "all_gold_components_context_visible",
    ]
    return {
        "role": role,
        "runs": len(rows),
        "answer_correct": sum(row["answer_correct"] for row in rows),
        "answer_incorrect": sum(not row["answer_correct"] for row in rows),
        "variants": dict(sorted(variants.items())),
        "correct_by_variant": dict(sorted(correct_variants.items())),
        "tool_calls": sum(row["tool_calls"] for row in rows),
        "mean_tool_calls": round(sum(row["tool_calls"] for row in rows) / len(rows), 4),
        "truncated_observation_calls": sum(
            row["truncated_observation_calls"] for row in rows
        ),
        "replay_summary_mismatches": sum(
            row["replay_summary_mismatches"] for row in rows
        ),
        "exposure_run_counts": {
            key: sum(bool(row[key]) for row in rows) for key in exposure_fields
        },
        "classifications": dict(sorted(classifications.items())),
        "confirmed_bypasses": [
            {"task": row["original_id"], "variant": row["variant"],
             "answer": row["answer"], "missing_surfaces": row["missing_surfaces"]}
            for row in rows if row["classification"] == "confirmed_bypass"
        ],
        "latent_closure_candidates": [
            {"task": row["original_id"], "variant": row["variant"],
             "answer": row["answer"], "missing_surfaces": row["missing_surfaces"]}
            for row in rows if row["classification"] == "latent_closure_not_exploited"
        ],
    }


def c0_c1_pairs(all_rows: list[dict]) -> list[dict]:
    index = {(row["stage"], row["original_id"], row["variant"]): row
             for row in all_rows}
    pairs = []
    keys = sorted({(row["original_id"], row["variant"])
                   for row in all_rows if row["stage"] == "C0-pro"})
    for task_id, variant in keys:
        c0 = index.get(("C0-pro", task_id, variant))
        c1 = index.get(("C1-pro", task_id, variant))
        if not c0 or not c1:
            raise ValueError(f"missing C0/C1 pair: {task_id} {variant}")
        pairs.append({
            "task": task_id,
            "variant": variant,
            "c0_correct": c0["answer_correct"],
            "c1_correct": c1["answer_correct"],
            "c0_classification": c0["classification"],
            "c1_classification": c1["classification"],
            "c0_tool_calls": c0["tool_calls"],
            "c1_tool_calls": c1["tool_calls"],
            "c0_truncated_calls": c0["truncated_observation_calls"],
            "c1_truncated_calls": c1["truncated_observation_calls"],
            "c0_rag_documents": c0["actual_inventory"]["rag_documents"],
            "c1_rag_documents": c1["actual_inventory"]["rag_documents"],
            "c0_table_views": c0["actual_inventory"]["table_views"],
            "c1_table_views": c1["actual_inventory"]["table_views"],
        })
    return pairs


def markdown_report(summary: dict) -> str:
    lines = [
        "# C0-C3 全量 trajectory 审计",
        "",
        "本报告由既有 trajectory 离线重放生成，不调用模型。`正确`是官方 answer scorer 的结果；C3 proper subset 返回 `INSUFFICIENT_EVIDENCE` 虽记为 answer score 0，但按因果门禁属于通过。",
        "",
        "## 阶段汇总",
        "",
        "| 阶段 | 角色 | Runs | 正确 | 工具调用 | 截断 observation | 重放不一致 |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for stage, stage_summary in summary["stages"].items():
        lines.append(
            f"| {stage} | `{stage_summary['role']}` | {stage_summary['runs']} | "
            f"{stage_summary['answer_correct']} | {stage_summary['tool_calls']} | "
            f"{stage_summary['truncated_observation_calls']} | "
            f"{stage_summary['replay_summary_mismatches']} |"
        )
    lines += [
        "",
        "## 暴露计数",
        "",
        "计数单位是出现该信号的 run，不等于成功泄露数。",
        "",
        "| 阶段 | task Graph prompt | task membership 被调用 | 原始 task 标签 observation | source_file | source_task | 行数元数据 | 全 gold 字段在可见上下文 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for stage, stage_summary in summary["stages"].items():
        e = stage_summary["exposure_run_counts"]
        lines.append(
            f"| {stage} | {e['graph_entry_prompt_visible']} | "
            f"{e['task_membership_observed']} | {e['raw_task_label_in_observation']} | "
            f"{e['source_file_field_visible']} | {e['source_task_provenance_visible']} | "
            f"{e['table_row_metadata_visible']} | "
            f"{e['all_gold_components_context_visible']} |"
        )
    lines += ["", "## 确认的 proper-subset 绕过", ""]
    for stage, stage_summary in summary["stages"].items():
        for row in stage_summary["confirmed_bypasses"]:
            lines.append(
                f"- {stage} `{row['task']}` / `{row['variant']}`，缺少 "
                f"`{','.join(row['missing_surfaces'])}`，答案 `{row['answer']}`。"
            )
    lines += [
        "",
        "## C0/C1 配对变化",
        "",
        "| Task | Variant | C0 | C1 | C0 KB/Table | C1 KB/Table | C0/C1 截断调用 |",
        "|---|---|---|---|---:|---:|---:|",
    ]
    for pair in summary["c0_c1_pairs"]:
        if pair["variant"] == "full" and pair["c0_correct"] == pair["c1_correct"]:
            continue
        c0_status = "correct" if pair["c0_correct"] else "incorrect"
        c1_status = "correct" if pair["c1_correct"] else "incorrect"
        lines.append(
            f"| `{pair['task']}` | `{pair['variant']}` | {c0_status} | {c1_status} | "
            f"{pair['c0_rag_documents']}/{pair['c0_table_views']} | "
            f"{pair['c1_rag_documents']}/{pair['c1_table_views']} | "
            f"{pair['c0_truncated_calls']}/{pair['c1_truncated_calls']} |"
        )
    static = summary.get("c2c_static_audit")
    if static:
        lines += [
            "",
            "## C2c 静态门禁",
            "",
            f"C2c 没有 API trajectory。静态审计覆盖 {static['source_tasks']} 题："
            f"retain {static['retained']}、downgrade {static['downgraded']}、"
            f"delete {static['deleted']}。固定哨兵全部在调用前被淘汰。",
        ]
    lines += [
        "",
        "## 解释边界",
        "",
        "- `confirmed_bypass` 必须同时满足 strict proper subset 和答案正确。",
        "- 失败或拒答不能单独证明无泄露；暴露计数用于识别 latent exposure。",
        "- 重放恢复的是工具 observation，不恢复模型隐藏思维链；原 runner 没有持久化中间 assistant 消息。",
        "- 文件名、行数或 task 标签出现只表示可见信号，是否构成泄露还需结合 required surface、gold 和静态 oracle。",
        "",
    ]
    return "\n".join(lines)


def write_checksums(out_dir: Path) -> None:
    rows = []
    for path in sorted(out_dir.iterdir()):
        if path.is_file() and path.name != "checksums.sha256":
            rows.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n")
    write_text_atomic(out_dir / "checksums.sha256", "".join(rows))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot-root", type=Path, default=Path("pilot"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    pilot_root = args.pilot_root.resolve()
    out_dir = args.out.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    all_rows = []
    stage_summaries = {}
    for stage, dirname, role in GROUPS:
        group_dir = pilot_root / dirname
        group_manifest = read_json(group_dir / "run_manifest.json")
        mapping = original_id_map(group_manifest)
        rows = [
            audit_run(stage, role, group_dir, path, group_manifest, mapping)
            for path in sorted(group_dir.glob("*.run.jsonl"))
        ]
        if not rows:
            raise ValueError(f"{group_dir}: no run trajectories")
        all_rows.extend(rows)
        stage_summaries[stage] = summarize_stage(rows, role)

    static_path = (pilot_root / "c2c_projection_r2_20260921" / "private"
                   / "classification_report.json")
    static = read_json(static_path) if static_path.is_file() else None
    summary = {
        "state": "completed",
        "method": "offline deterministic tool replay with original 1500-char observation truncation",
        "api_calls": 0,
        "runs": len(all_rows),
        "tool_calls": sum(row["tool_calls"] for row in all_rows),
        "replay_summary_mismatches": sum(
            row["replay_summary_mismatches"] for row in all_rows
        ),
        "stages": stage_summaries,
        "c0_c1_pairs": c0_c1_pairs(all_rows),
        "c2c_static_audit": ({
            key: static[key] for key in (
                "state", "source_tasks", "retained", "downgraded", "deleted",
                "sentinel_api_runs", "sentinel_reason",
            )
        } if static else None),
    }
    jsonl = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in all_rows)
    write_text_atomic(out_dir / "trajectory_audit.jsonl", jsonl)
    write_json_atomic(out_dir / "summary.json", summary)
    write_text_atomic(out_dir / "report.md", markdown_report(summary))
    write_checksums(out_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
