"""Parse the coding-interview-university study plan into a topic graph.

The README encodes the curriculum as markdown: ``##`` topic sections,
``- ###`` subtopics, checkbox resources and implementation tasks. This module
turns that into structured data the drill generator and progress tracker use.
Stdlib only; no kgirl import needed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

CORE_TOPICS = [
    "Algorithmic complexity / Big-O / Asymptotic analysis",
    "Data Structures",
    "More Knowledge",
    "Trees",
    "Sorting",
    "Graphs",
    "Even More Knowledge",
    "Final Review",
]
ELECTIVE_TOPICS = ["System Design, Scalability, Data Handling"]

_H2 = re.compile(r"^## (.+?)\s*$")
_SUB = re.compile(r"^- ### (.+?)\s*$")
_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_TASK = re.compile(r"^\s*- \[ \] (?!\[)(.+?)\s*$")


def slugify(name: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", name.lower())).strip("-")


def _resources(lines: list[str]) -> list[dict]:
    out, seen = [], set()
    for line in lines:
        if "back to top" in line:
            continue
        for title, url in _LINK.findall(line):
            if url not in seen:
                seen.add(url)
                out.append({"title": title.strip(), "url": url})
    return out


def _tasks(lines: list[str]) -> list[str]:
    out = []
    for line in lines:
        m = _TASK.match(line)
        if m:
            text = m.group(1).strip()
            if text and not text.endswith(":"):
                out.append(text[:160])
    return out[:40]


def _subtopic(name: str, line_no: int, lines: list[str]) -> dict:
    return {
        "id": slugify(name),
        "name": name,
        "line": line_no,
        "tasks": _tasks(lines),
        "resources": _resources(lines),
    }


def parse_readme(path: str | Path) -> dict:
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    headings = [(i, m.group(1)) for i, line in enumerate(lines) if (m := _H2.match(line))]
    wanted = {name: kind for kind, names in (("core", CORE_TOPICS), ("elective", ELECTIVE_TOPICS))
              for name in names}
    topics = []
    for idx, (start, name) in enumerate(headings):
        if name not in wanted:
            continue
        end = headings[idx + 1][0] if idx + 1 < len(headings) else len(lines)
        body = lines[start + 1:end]
        sub_starts = [(j, m.group(1)) for j, line in enumerate(body) if (m := _SUB.match(line))]
        if sub_starts:
            subtopics = []
            for k, (j, sub_name) in enumerate(sub_starts):
                stop = sub_starts[k + 1][0] if k + 1 < len(sub_starts) else len(body)
                subtopics.append(_subtopic(sub_name, start + 2 + j, body[j + 1:stop]))
        else:
            subtopics = [_subtopic(name, start + 1, body)]
        topics.append({"id": slugify(name), "name": name, "line": start + 1,
                       "kind": wanted[name], "subtopics": subtopics})
    order = {name: i for i, name in enumerate(CORE_TOPICS + ELECTIVE_TOPICS)}
    topics.sort(key=lambda t: order[t["name"]])
    return {"source": str(path), "topics": topics}


def load_or_parse(cache_path: str | Path, readme_path: str | Path) -> dict:
    cache, readme = Path(cache_path), Path(readme_path)
    if cache.exists() and cache.stat().st_mtime >= readme.stat().st_mtime:
        return json.loads(cache.read_text(encoding="utf-8"))
    cur = parse_readme(readme)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(cur, indent=1), encoding="utf-8")
    return cur


def find_topic(cur: dict, name_or_id: str) -> dict | None:
    key = slugify(name_or_id)
    for topic in cur["topics"]:
        if topic["id"] == key or topic["name"].lower() == name_or_id.lower():
            return topic
    return None


def find_subtopic(cur: dict, topic_name: str, sub_name: str) -> dict | None:
    topic = find_topic(cur, topic_name)
    if not topic:
        return None
    key = slugify(sub_name)
    for sub in topic["subtopics"]:
        if sub["id"] == key or sub["name"].lower() == sub_name.lower():
            return sub
    return None


def render_tree(cur: dict, families: dict | None = None) -> str:
    covered = {}
    if families:
        for fam in families.values():
            covered.setdefault(fam["topic"], set()).add(fam.get("subtopic") or fam["topic"])
    rows = []
    for topic in cur["topics"]:
        mark = "*" if topic["name"] in covered else " "
        rows.append(f"{mark} {topic['name']}  [{topic['kind']}]")
        for sub in topic["subtopics"]:
            hit = topic["name"] in covered and sub["name"] in covered[topic["name"]]
            rows.append(f"  {'*' if hit else ' '} {sub['name']}"
                        f"  ({len(sub['resources'])} resources, {len(sub['tasks'])} tasks)")
    rows.append("")
    rows.append("* = drill family available")
    return "\n".join(rows)