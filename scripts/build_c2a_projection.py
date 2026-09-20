#!/usr/bin/env python3
"""Build and statically validate a C2a public projection.

C2a removes source-task labels and replaces public document, table, file, and
graph identifiers with deterministic aliases. Original resources are only
read. The reversible mapping is written outside the public data root.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from worksurface.convert_tables import connect_registry


HEADER_RE = re.compile(r"^<!-- source_task: .*? \| source_file: .*? \| surface: rag -->\r?\n\r?\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def digest(kind: str, *parts: str, length: int = 12) -> str:
    raw = "\0".join(("worksurface-c2a-v1", kind, *map(str, parts)))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:length]


def file_alias(task_id: str, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return f"file_{digest('file', task_id, filename)}{suffix}"


def load_task_files(task_dir: Path) -> dict[str, list[dict]]:
    paths = sorted(task_dir.glob("*__full.jsonl"))
    paths += sorted(
        path for path in task_dir.glob("*__subset*.jsonl")
        if ".run." not in path.name
    )
    if not paths:
        raise ValueError(f"no task inputs found in {task_dir}")
    loaded = {}
    for path in paths:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()]
        if len(rows) != 1:
            raise ValueError(f"{path}: expected exactly one task")
        loaded[path.name] = rows
    return loaded


class Projection:
    def __init__(self, source_profile: Path, task_files: dict[str, list[dict]],
                 out_dir: Path):
        self.source_profile = source_profile
        self.task_files = task_files
        self.out_dir = out_dir
        self.public_profile = out_dir / "public" / "profiles" / source_profile.name
        self.private_dir = out_dir / "private"
        self.kb_registry = read_json(source_profile / "kb_docs" / "registry.json")
        self.table_registry = read_json(source_profile / "tables" / "registry.json")
        self.graph = read_json(source_profile / "graph" / "surface_graph.json")
        self.task_aliases: dict[str, str] = {}
        self.file_aliases: dict[tuple[str, str], str] = {}
        self.doc_aliases: dict[str, str] = {}
        self.table_aliases: dict[str, str] = {}
        self.graph_aliases: dict[str, str] = {}
        self._index_aliases()

    def _index_aliases(self) -> None:
        task_ids = {str(meta["source_task"]) for meta in self.kb_registry.values()}
        task_ids.update(str(meta["task"]) for meta in self.table_registry.values())
        for node in self.graph["nodes"]:
            if node["type"] == "task" and node["id"].startswith("task_"):
                task_ids.add(node["id"].removeprefix("task_"))
            if node.get("task") is not None:
                task_ids.add(str(node["task"]))
        self.task_aliases = {
            task_id: f"work_item_{digest('task', task_id)}"
            for task_id in sorted(task_ids)
        }

        for meta in self.kb_registry.values():
            key = (str(meta["source_task"]), meta["source_file"])
            self.file_aliases.setdefault(key, file_alias(*key))
        for meta in self.table_registry.values():
            key = (str(meta["task"]), meta["source_file"])
            self.file_aliases.setdefault(key, file_alias(*key))
        for node in self.graph["nodes"]:
            if node.get("task") is not None and node.get("filename"):
                key = (str(node["task"]), node["filename"])
                self.file_aliases.setdefault(key, file_alias(*key))

        self.doc_aliases = {
            old: f"doc_{digest('doc', str(meta['source_task']), old)}.md"
            for old, meta in self.kb_registry.items()
        }
        self.table_aliases = {
            old: f"table_{digest('table', str(meta['task']), old)}"
            for old, meta in self.table_registry.items()
        }
        for node in self.graph["nodes"]:
            old = node["id"]
            task_id = str(node.get("task", ""))
            if node["type"] == "task":
                original_id = old.removeprefix("task_")
                alias = self.task_aliases[original_id]
            elif node.get("filename") and task_id:
                if node["type"] == "output":
                    suffix = Path(node["filename"]).suffix.lower()
                    alias = f"output_{digest('output', task_id, node['filename'])}{suffix}"
                else:
                    alias = self.file_aliases[(task_id, node["filename"])]
            else:
                alias = f"entity_{digest('graph', old)}"
            self.graph_aliases[old] = alias
        if len(set(self.graph_aliases.values())) != len(self.graph_aliases):
            raise ValueError("graph aliases are not unique")

    def _task_replacements(self, task_id: str) -> dict[str, str]:
        replacements = {
            old: new for old, new in self.doc_aliases.items()
            if str(self.kb_registry[old]["source_task"]) == task_id
        }
        replacements.update({
            old: new for old, new in self.table_aliases.items()
            if str(self.table_registry[old]["task"]) == task_id
        })
        replacements.update({
            old: new for (tid, old), new in self.file_aliases.items()
            if tid == task_id
        })
        replacements.update({
            old: new for old, new in self.graph_aliases.items()
            if old == f"task_{task_id}" or old.startswith(f"t{task_id}::")
        })
        return replacements

    @staticmethod
    def _replace_text(text: str, replacements: dict[str, str]) -> str:
        for old in sorted(replacements, key=len, reverse=True):
            text = text.replace(old, replacements[old])
        return text

    def _replace_task_id_text(self, text: str, task_id: str) -> str:
        alias = self.task_aliases[task_id]
        return re.sub(rf"\bTask\s+{re.escape(task_id)}\b", f"work item {alias}",
                      text, flags=re.IGNORECASE)

    def _rewrite_value(self, value: Any, replacements: dict[str, str],
                       task_id: str) -> Any:
        if isinstance(value, str):
            return self._replace_task_id_text(
                self._replace_text(value, replacements), task_id
            )
        if isinstance(value, list):
            return [self._rewrite_value(item, replacements, task_id) for item in value]
        if isinstance(value, dict):
            return {key: self._rewrite_value(item, replacements, task_id)
                    for key, item in value.items()}
        return value

    def _rewrite_evidence(self, evidence: list[dict], task_id: str) -> list[dict]:
        rewritten = copy.deepcopy(evidence)
        graph_replacements = {
            old: new for old, new in self.graph_aliases.items()
            if old == f"task_{task_id}" or old.startswith(f"t{task_id}::")
        }
        doc_replacements = {
            old: new for old, new in self.doc_aliases.items()
            if str(self.kb_registry[old]["source_task"]) == task_id
        }
        table_replacements = {
            old: new for old, new in self.table_aliases.items()
            if str(self.table_registry[old]["task"]) == task_id
        }
        source_replacements = {
            old: new for (tid, old), new in self.file_aliases.items()
            if tid == task_id
        }
        for ev in rewritten:
            if ev.get("file") in doc_replacements:
                ev["file"] = doc_replacements[ev["file"]]
            if ev.get("canonical_rag_file") in doc_replacements:
                ev["canonical_rag_file"] = doc_replacements[ev["canonical_rag_file"]]
            if ev.get("table") in table_replacements:
                ev["table"] = table_replacements[ev["table"]]
            if ev.get("source_file") in source_replacements:
                ev["source_file"] = source_replacements[ev["source_file"]]
            if ev.get("query"):
                ev["query"] = self._replace_text(ev["query"], table_replacements)
            if ev.get("graph_path"):
                ev["graph_path"] = [graph_replacements.get(item, item)
                                    for item in ev["graph_path"]]
            if ev.get("verified_complete_set"):
                ev["verified_complete_set"] = [
                    source_replacements.get(item, item)
                    for item in ev["verified_complete_set"]
                ]
            graph_query = ev.get("graph_query")
            if graph_query and graph_query.get("node") in graph_replacements:
                graph_query["node"] = graph_replacements[graph_query["node"]]
            for key in ("claim", "canonicalization", "verified_candidate_scope"):
                if isinstance(ev.get(key), str):
                    ev[key] = self._replace_task_id_text(ev[key], task_id)
        return rewritten

    def _rewrite_gold_answer(self, task: dict, replacements: dict[str, str]) -> Any:
        answer = task.get("gold_answer")
        if not isinstance(answer, str):
            return self._rewrite_value(answer, replacements,
                                       str(task["source"]["task_id"]))
        spans = {str(ev.get("span")) for ev in task.get("gold_evidence", [])
                 if ev.get("span") is not None}
        separator = "; " if "; " in answer else ": " if ": " in answer else None
        parts = answer.split(separator) if separator else [answer]
        rewritten = []
        for part in parts:
            stripped = part.strip()
            rewritten.append(part if stripped in spans
                             else self._replace_text(part, replacements))
        return separator.join(rewritten) if separator else rewritten[0]

    def project_task(self, task: dict) -> dict:
        projected = copy.deepcopy(task)
        task_id = str(task["source"]["task_id"])
        replacements = self._task_replacements(task_id)
        projected["question"] = self._replace_task_id_text(
            self._replace_text(task["question"], replacements), task_id
        )
        projected["gold_evidence"] = self._rewrite_evidence(
            task.get("gold_evidence", []), task_id
        )
        projected["gold_answer"] = self._rewrite_gold_answer(task, replacements)
        projected["source"]["task_id"] = self.task_aliases[task_id]
        projected["graph_entry_node"] = self.task_aliases[task_id]
        projected["projection"] = "C2a"
        # Scrub references in auxiliary public metadata (for example notes)
        # after identifier-aware evidence rewriting has preserved spans and
        # SQL literals.
        return self._rewrite_task_number_metadata(projected, task_id)

    def _rewrite_task_number_metadata(self, value: Any, task_id: str) -> Any:
        if isinstance(value, str):
            return self._replace_task_id_text(value, task_id)
        if isinstance(value, list):
            return [self._rewrite_task_number_metadata(item, task_id)
                    for item in value]
        if isinstance(value, dict):
            return {key: self._rewrite_task_number_metadata(item, task_id)
                    for key, item in value.items()}
        return value

    def build_kb(self) -> dict:
        out_dir = self.public_profile / "kb_docs"
        out_dir.mkdir(parents=True, exist_ok=True)
        public_registry = {}
        for old_doc, meta in sorted(self.kb_registry.items()):
            task_id = str(meta["source_task"])
            public_doc = self.doc_aliases[old_doc]
            source = self.source_profile / "kb_docs" / old_doc
            body = HEADER_RE.sub("", source.read_text(encoding="utf-8"), count=1)
            (out_dir / public_doc).write_text(body, encoding="utf-8")
            public_registry[public_doc] = {
                "source_file": self.file_aliases[(task_id, meta["source_file"])],
                "ext": meta.get("ext"),
                "chars": len(body),
                "from_table": bool(meta.get("from_table", False)),
            }
        write_json(out_dir / "registry.json", public_registry)
        return public_registry

    def build_tables(self) -> dict:
        out_dir = self.public_profile / "tables"
        out_dir.mkdir(parents=True, exist_ok=True)
        public_registry = {}
        for old_view, meta in sorted(self.table_registry.items()):
            task_id = str(meta["task"])
            public_view = self.table_aliases[old_view]
            public_file = self.file_aliases[(task_id, meta["source_file"])]
            parquet_name = public_view + ".parquet"
            table = pq.read_table(self.source_profile / "tables" / meta["parquet"])
            if "_source_file" in table.column_names:
                index = table.column_names.index("_source_file")
                table = table.set_column(
                    index, "_source_file",
                    pa.array([public_file] * table.num_rows, type=pa.string()),
                )
            pq.write_table(table, out_dir / parquet_name)
            public_registry[public_view] = {
                "source_file": public_file,
                "sheet": meta.get("sheet"),
                "rows": int(meta["rows"]),
                "parquet": parquet_name,
                "columns": copy.deepcopy(meta.get("columns", [])),
            }
        write_json(out_dir / "registry.json", public_registry)
        return public_registry

    def build_graph(self) -> dict:
        out_dir = self.public_profile / "graph"
        out_dir.mkdir(parents=True, exist_ok=True)
        nodes = []
        for node in self.graph["nodes"]:
            public = {key: copy.deepcopy(value) for key, value in node.items()
                      if key not in {"task", "hash"}}
            public["id"] = self.graph_aliases[node["id"]]
            if node.get("task") is not None:
                public["work_item"] = self.task_aliases[str(node["task"])]
            if node.get("filename"):
                task_id = str(node.get("task", ""))
                if node["type"] == "output":
                    public["filename"] = self.graph_aliases[node["id"]]
                elif task_id:
                    public["filename"] = self.file_aliases[(task_id, node["filename"])]
            nodes.append(public)
        edges = []
        for edge in self.graph["edges"]:
            public = copy.deepcopy(edge)
            public["from"] = self.graph_aliases[edge["from"]]
            public["to"] = self.graph_aliases[edge["to"]]
            edges.append(public)
        graph = {"nodes": nodes, "edges": edges}
        write_json(out_dir / "surface_graph.json", graph)
        return graph

    def build_tasks(self) -> dict[str, list[dict]]:
        projected = {
            name: [self.project_task(row) for row in rows]
            for name, rows in self.task_files.items()
        }
        for name, rows in projected.items():
            write_jsonl(self.out_dir / "public" / "tasks" / name, rows)
        return projected

    def write_private_map(self) -> None:
        payload = {
            "version": 1,
            "tasks": self.task_aliases,
            "files": [
                {"source_task": task_id, "source_file": source_file,
                 "public_file": alias}
                for (task_id, source_file), alias in sorted(self.file_aliases.items())
            ],
            "kb_docs": self.doc_aliases,
            "tables": self.table_aliases,
            "graph_nodes": self.graph_aliases,
        }
        write_json(self.private_dir / "alias_map.json", payload)

    def source_lock(self) -> dict:
        files = []
        for path in sorted(self.source_profile.rglob("*")):
            if path.is_file():
                raw = path.read_bytes()
                files.append({
                    "path": str(path.relative_to(self.source_profile)),
                    "size": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                })
        payload = {
            "source_profile": str(self.source_profile.resolve()),
            "files": files,
            "aggregate_sha256": hashlib.sha256(
                "".join(item["sha256"] for item in files).encode("ascii")
            ).hexdigest(),
        }
        write_json(self.private_dir / "source_lock.json", payload)
        return payload


def validate_projection(out_dir: Path, profile_slug: str,
                        projected_tasks: dict[str, list[dict]],
                        task_aliases: dict[str, str]) -> dict:
    public = out_dir / "public"
    profile = public / "profiles" / profile_slug
    kb_registry = read_json(profile / "kb_docs" / "registry.json")
    table_registry = read_json(profile / "tables" / "registry.json")
    graph = read_json(profile / "graph" / "surface_graph.json")
    node_ids = {node["id"] for node in graph["nodes"]}
    edge_keys = {(edge["from"], edge["rel"], edge["to"])
                 for edge in graph["edges"]}
    errors = []
    surface_findings = []

    for edge in graph["edges"]:
        if edge["from"] not in node_ids or edge["to"] not in node_ids:
            errors.append(f"dangling graph edge: {edge}")

    con, views = connect_registry(str(profile / "tables"))
    try:
        for name, rows in projected_tasks.items():
            for task in rows:
                if task["graph_entry_node"] not in node_ids:
                    errors.append(f"{name}: missing graph entry node")
                for ev in task.get("gold_evidence", []):
                    if ev.get("surface") == "rag" and ev.get("file"):
                        doc = ev["file"]
                        if doc not in kb_registry:
                            errors.append(f"{name}: missing RAG doc {doc}")
                        elif ev.get("span") is not None:
                            text = (profile / "kb_docs" / doc).read_text(encoding="utf-8")
                            if str(ev["span"]) not in text:
                                surface_findings.append({
                                    "task_file": name,
                                    "kind": "rag_span_absent_after_provenance_removal",
                                    "document": doc,
                                    "span": str(ev["span"]),
                                })
                    if ev.get("surface") == "table" and ev.get("table"):
                        view = ev["table"]
                        if view not in views:
                            errors.append(f"{name}: missing table {view}")
                        if ev.get("query") and view in views:
                            try:
                                row = con.execute(ev["query"]).fetchone()
                                if ev.get("verified_result") is not None and (
                                    not row or row[0] != ev["verified_result"]
                                ):
                                    errors.append(f"{name}: SQL result mismatch for {view}")
                            except Exception as exc:  # noqa: BLE001
                                errors.append(f"{name}: SQL failed for {view}: {exc}")
                    path = ev.get("graph_path") or []
                    if len(path) == 3 and tuple(path) not in edge_keys:
                        errors.append(f"{name}: missing graph path {path}")
    finally:
        con.close()

    ids = "|".join(re.escape(task_id) for task_id in sorted(task_aliases, key=len,
                                                             reverse=True))
    leak_patterns = {
        "task_number": re.compile(rf"\btask\s+(?:{ids})\b", re.I),
        "task_node": re.compile(rf"\btask_(?:{ids})\b", re.I),
        "prefixed_id": re.compile(rf"\bt(?:{ids})(?:__|::)", re.I),
        "source_task_field": re.compile(r"source_task", re.I),
    }
    violations = []
    for path in sorted(public.rglob("*")):
        if not path.is_file() or path.suffix == ".parquet":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for kind, pattern in leak_patterns.items():
            match = pattern.search(text)
            if match:
                violations.append({"path": str(path.relative_to(public)),
                                   "kind": kind, "match": match.group(0)})
    report = {
        "state": "passed" if not errors and not violations else "failed",
        "task_files": len(projected_tasks),
        "task_rows": sum(len(rows) for rows in projected_tasks.values()),
        "kb_docs": len(kb_registry),
        "table_views": len(table_registry),
        "graph_nodes": len(graph["nodes"]),
        "graph_edges": len(graph["edges"]),
        "validation_errors": errors,
        "surface_findings": surface_findings,
        "leakage_violations": violations,
    }
    write_json(out_dir / "leakage_report.json", report)
    if report["state"] != "passed":
        raise ValueError(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-profile", type=Path, required=True)
    parser.add_argument("--task-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    source_profile = args.source_profile.resolve()
    task_files = load_task_files(args.task_dir.resolve())
    out_dir = args.out.resolve()
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError(f"refusing to overwrite non-empty output: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)

    projection = Projection(source_profile, task_files, out_dir)
    source_lock = projection.source_lock()
    projection.write_private_map()
    kb = projection.build_kb()
    tables = projection.build_tables()
    graph = projection.build_graph()
    tasks = projection.build_tasks()
    report = validate_projection(out_dir, source_profile.name, tasks,
                                 projection.task_aliases)
    manifest = {
        "stage": "C2a",
        "source_lock_sha256": source_lock["aggregate_sha256"],
        "task_files": len(tasks),
        "full_runs": sum(name.endswith("__full.jsonl") for name in tasks),
        "subset_runs": sum("__subset" in name for name in tasks),
        "kb_docs": len(kb),
        "table_views": len(tables),
        "graph_nodes": len(graph["nodes"]),
        "graph_edges": len(graph["edges"]),
        "validation": report["state"],
    }
    write_json(out_dir / "projection_manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
