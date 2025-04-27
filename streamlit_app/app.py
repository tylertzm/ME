# app.py
# ─────────────────────────────────────────────────────────────────────────────
# ME-Journal front-end – shows only today’s entries and allows date-scoped journaling.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import copy
import datetime as _dt
import itertools
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple

import requests
import streamlit as st

from database import (
    add_entry,
    entries_by_date,
    search_entries,
)

# ─── Restack agent config ───────────────────────────────────────────────────
BASE_URL = os.getenv(
    "RESTACK_BASE_URL",
    "https://res2tsut.clj5khk.gcp.restack.it",
).rstrip("/")
AGENT_ID = os.getenv("RESTACK_AGENT_ID", "d7e08832-AgentStructureResult")
RUN_ID = os.getenv("RESTACK_RUN_ID", "01967657-63b9-7272-9413-c01c93a13c6e")
RESTACK_ENDPOINT = (
    f"{BASE_URL}/api/agents/AgentStructureResult/{AGENT_ID}/{RUN_ID}"
)

# ─── page & CSS ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="ME Journal", page_icon="📝", layout="wide")
css_path = Path(__file__).parent / "style.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

# ─── agent call ─────────────────────────────────────────────────────────────
def _call_agent(prompt_text: str) -> dict:
    payload = {
        "eventName": "messages",
        "eventInput": {"messages": [{"role": "user", "content": prompt_text}]},
    }
    resp = requests.put(RESTACK_ENDPOINT, json=payload, timeout=90)
    resp.raise_for_status()
    messages: list[dict] = resp.json()
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            return json.loads(msg["content"])
    raise RuntimeError("No assistant message returned")

# ─── HTML helpers ───────────────────────────────────────────────────────────
def _block(html: str) -> None:
    st.markdown(f"<div class='block'>{html}</div>", unsafe_allow_html=True)

def _render_schedule(items: list[dict]) -> None:
    if not items:
        _block("<h3>Schedule</h3><p><em>Nothing scheduled.</em></p>")
        return
    li = "".join(f"<li><strong>{i['time']}</strong> – {i['task']}</li>" for i in items)
    _block(f"<h3>Schedule</h3><ul>{li}</ul>")

def _render_relationships(items: list[dict]) -> None:
    if not items:
        _block("<h3>Relationships</h3><p><em>No relationship info.</em></p>")
        return
    html = ["<h3>Relationships</h3>"]
    for r in items:
        html.append(f"<p><strong>{r['name']}</strong> — {r.get('role','—')}<br>")
        if details := r.get("details"):
            html.append("<br>".join(f"{k}: {v}" for k, v in details.items()) + "<br>")
        if r.get("notes"):
            html.append("<ul>" + "".join(f"<li>{n}</li>" for n in r["notes"]) + "</ul>")
        html.append("</p>")
    _block("".join(html))

def _render_mind_space(items: list[dict]) -> None:
    if not items:
        _block("<h3>Mind Space</h3><p><em>Mind is clear! ✨</em></p>")
        return
    li = "".join(f"<li>{t['thought']}</li>" for t in items)
    _block(f"<h3>Mind Space</h3><ul>{li}</ul>")

# ─── relationship utils ─────────────────────────────────────────────────────
def _relationship_key(r: dict) -> str:
    return r["name"].strip().lower()

def _merge_additive(existing: dict, new: dict) -> dict:
    merged = copy.deepcopy(existing)
    if new.get("role"):
        merged["role"] = new["role"]
    merged.setdefault("details", {}).update(new.get("details", {}))
    merged.setdefault("notes", [])
    for note in new.get("notes", []):
        if note not in merged["notes"]:
            merged["notes"].append(note)
    return merged

def _diff_conflicts(existing: dict, new: dict) -> Tuple[bool, List[str]]:
    conflicts = []
    if new.get("role") and existing.get("role") and new["role"] != existing["role"]:
        conflicts.append("role")
    for k, v in (new.get("details") or {}).items():
        if k in existing.get("details", {}) and existing["details"][k] != v:
            conflicts.append(f"detail:{k}")
    return bool(conflicts), conflicts

def _dedup_relationships(rel_list: List[dict]) -> List[dict]:
    """Return one merged entry per person, using chronological order."""
    result: Dict[str, dict] = {}
    for rel in rel_list:  # oldest ➜ newest
        key = _relationship_key(rel)
        if key not in result:
            result[key] = copy.deepcopy(rel)
        else:
            result[key] = _merge_additive(result[key], rel)
    return list(result.values())

def _rel_label(r: dict) -> str:
    role = r.get("role", "—")
    det = ", ".join(f"{k}:{v}" for k, v in (r.get("details") or {}).items())
    return f"{role} | {det}" if det else role


def _schedule_key(s: dict) -> str:
    """Use the task description (lower-case) as key."""
    return s["task"].strip().lower()


def _dedup_schedule(events: List[dict]) -> List[dict]:
    """
    Keep **one entry per task**; when the task occurs again
    with a different time, the most recent record wins.
    """
    dedup: Dict[str, dict] = {}
    for ev in events:  # oldest ➜ newest
        dedup[_schedule_key(ev)] = ev  # later items overwrite earlier
    # sort by time for nicer display
    return sorted(dedup.values(), key=lambda e: e["time"])

# ─── main ───────────────────────────────────────────────────────────────────
def main() -> None:
    st.markdown("<h1>ME Journal</h1>", unsafe_allow_html=True)

    # pick your journal date
    selected_date = st.date_input(
        "Journal Date",
        _dt.date.today(),
        label_visibility="collapsed",
    )
    st.divider()

    # load only entries for that date
    entries = entries_by_date(selected_date)

    raw_schedule = list(
        itertools.chain.from_iterable(e["structured"].get("Schedule", []) for e in entries)
    )
    raw_rels_all: List[dict] = list(
        itertools.chain.from_iterable(
            e["structured"].get("Relationships", []) for e in entries
        )
    )

    schedule_all = _dedup_schedule(raw_schedule)
    rels_all = _dedup_relationships(raw_rels_all)
    mind_all = list(
        itertools.chain.from_iterable(
            e["structured"].get("Mind Space", []) for e in entries
        )
    )

    # ── display blocks ────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        _render_schedule(schedule_all)
    with c2:
        _render_relationships(rels_all)
    with c3:
        _render_mind_space(mind_all)

    st.divider()

    # ── Handle pending clarifications for Relationships ──────────────────────
    if st.session_state.get("await_clarify"):
        structured = st.session_state["pending_structured"]
        prompt_txt = st.session_state["pending_prompt"]
        conflicts = st.session_state["conflicts"]

        st.markdown("#### Resolve conflicts")
        with st.form("clarify_form"):
            decisions: dict[int, str] = {}
            for idx, info in enumerate(conflicts):
                new_rel, ex_rel = info["new"], info["existing"]
                label = (
                    f"Info about **{new_rel['name']}** conflicts with existing "
                    "data. How should I handle it?"
                )
                opts = {
                    f"Update existing profile ({_rel_label(ex_rel)})": "update",
                    "Keep as separate person": "separate",
                    "Discard the new information": "discard",
                }
                choice = st.radio(label, list(opts.keys()), key=f"choice_{idx}")
                decisions[info["new_index"]] = opts[choice]
            confirmed = st.form_submit_button("Confirm")

        if confirmed:
            final_rels: List[dict] = []
            for idx, rel in enumerate(structured["Relationships"]):
                decision = decisions.get(idx)
                if decision == "discard":
                    continue
                if decision == "update":
                    final_rels.append(_merge_additive(conflicts[0]["existing"], rel))
                else:  # separate or untouched
                    final_rels.append(rel)
            structured["Relationships"] = final_rels
            add_entry(prompt_txt, structured, selected_date)
            for k in ("await_clarify", "pending_structured", "pending_prompt", "conflicts"):
                st.session_state.pop(k, None)
            st.success("Saved!")
            st.rerun()
        return

    # ── Thought / Schedule Input form ────────────────────────────────────────
    st.markdown("### Thought Input / Scheduling")

    with st.form("prompt_form"):
        cols = st.columns([8, 2])
        prompt = cols[0].text_input(
            label="Thought prompt",
            placeholder="Reflect on today's achievements… or 'At 3pm call Alice'",
            label_visibility="hidden",
        )
        cols[1].markdown("<br>", unsafe_allow_html=True)
        submitted = cols[1].form_submit_button("Submit →", use_container_width=True)

    if submitted:
        if not prompt.strip():
            st.warning("Please enter some text first.")
            st.stop()

        with st.spinner("Talking to your agent…"):
            try:
                structured = _call_agent(prompt)
            except Exception as exc:
                st.error(str(exc))
                st.stop()

        # reconcile relationships
        rel_map = {_relationship_key(r): r for r in rels_all}
        conflicts: list[dict] = []
        merged_rels: list[dict] = []

        for idx, new_rel in enumerate(structured["Relationships"]):
            key = _relationship_key(new_rel)
            if key not in rel_map:
                merged_rels.append(new_rel)
                continue
            existing = rel_map[key]
            has_conflict, _ = _diff_conflicts(existing, new_rel)
            if not has_conflict:
                merged_rels.append(_merge_additive(existing, new_rel))
            else:
                conflicts.append(
                    {"new_index": idx, "new": new_rel, "existing": existing}
                )
                merged_rels.append(new_rel)

        if conflicts:
            st.session_state.update(
                await_clarify=True,
                conflicts=conflicts,
                pending_structured=structured,
                pending_prompt=prompt,
            )
            st.rerun()
        else:
            structured["Relationships"] = merged_rels
            add_entry(prompt, structured, selected_date)
            st.success("Saved!")
            st.rerun()

    # ── Knowledge Search ─────────────────────────────────────────────────
    st.divider()
    st.markdown("### Knowledge Search")
    q = st.text_input("Search your journal", placeholder="Enter search terms…")
    if q:
        hits = search_entries(q)
        if not hits:
            st.info("No matches found.")
        else:
            for doc in hits:
                with st.expander(doc["prompt"][:80] + "…"):
                    st.json(doc["structured"])


if __name__ == "__main__":
    main()
