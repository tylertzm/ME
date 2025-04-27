# app.py
# ─────────────────────────────────────────────────────────────────────────────
# Streamlit front-end for ME-Journal – with relationship disambiguation.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import datetime as _dt
import itertools
import json
import os
from pathlib import Path

import requests
import streamlit as st

from database import add_entry, all_entries, search_entries

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
st.set_page_config(
    page_title="ME Journal",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed",
)
css_path = Path(__file__).parent / "style.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

# ─── helpers ────────────────────────────────────────────────────────────────
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
    raise RuntimeError("No assistant message in Restack response")


def _block(inner_html: str) -> None:
    st.markdown(f"<div class='block'>{inner_html}</div>", unsafe_allow_html=True)


def _render_schedule(items: list[dict]) -> None:
    if not items:
        _block("<h3>Schedule</h3><p><em>Nothing scheduled.</em></p>")
        return
    lis = "".join(f"<li><strong>{x['time']}</strong> – {x['task']}</li>" for x in items)
    _block(f"<h3>Schedule</h3><ul>{lis}</ul>")


def _render_relationships(items: list[dict]) -> None:
    if not items:
        _block("<h3>Relationships</h3><p><em>No relationship info.</em></p>")
        return
    html = ["<h3>Relationships</h3>"]
    for rel in items:
        html.append(f"<p><strong>{rel['name']}</strong> — {rel.get('role','—')}<br>")
        if details := rel.get("details"):
            html.append("<br>".join(f"{k}: {v}" for k, v in details.items()) + "<br>")
        if rel.get("notes"):
            html.append("<ul>" + "".join(f"<li>{n}</li>" for n in rel["notes"]) + "</ul>")
        html.append("</p>")
    _block("".join(html))


def _render_mind_space(items: list[dict]) -> None:
    if not items:
        _block("<h3>Mind Space</h3><p><em>Mind is clear! ✨</em></p>")
        return
    lis = "".join(f"<li>{t['thought']}</li>" for t in items)
    _block(f"<h3>Mind Space</h3><ul>{lis}</ul>")


# ─── ambiguity helpers ──────────────────────────────────────────────────────
def _find_relationship_ambiguities(
    new_rels: list[dict], existing_rels: list[dict]
) -> list[dict]:
    """Return list of ambiguities: {new_idx, name, options:[existing_rel,…]}."""
    ambiguities: list[dict] = []
    for idx, rel in enumerate(new_rels):
        matches = [e for e in existing_rels if e["name"].lower() == rel["name"].lower()]
        # keep only matches that differ in role or details
        matches = [
            m
            for m in matches
            if m.get("role") != rel.get("role") or m.get("details") != rel.get("details")
        ]
        if matches:
            ambiguities.append(
                {
                    "new_idx": idx,
                    "name": rel["name"],
                    "options": matches,
                }
            )
    return ambiguities


def _rel_as_label(r: dict) -> str:
    role = r.get("role", "—")
    details = ", ".join(f"{k}:{v}" for k, v in (r.get("details") or {}).items())
    return f"{role} | {details}" if details else role


# ─── main ───────────────────────────────────────────────────────────────────
def main() -> None:
    # ── header ────────────────────────────────────────────────────────────
    st.markdown("<h1>ME Journal</h1>", unsafe_allow_html=True)
    st.date_input("Journal Date", _dt.date.today(), label_visibility="collapsed")
    st.divider()

    # ── clarification flow state ──────────────────────────────────────────
    clarify_mode = st.session_state.get("clarify_mode", False)

    # ── display blocks using ALL entries ──────────────────────────────────
    entries = all_entries()
    schedule_all = list(
        itertools.chain.from_iterable(e["structured"].get("Schedule", []) for e in entries)
    )
    relationships_all = list(
        itertools.chain.from_iterable(
            e["structured"].get("Relationships", []) for e in entries
        )
    )
    mind_all = list(
        itertools.chain.from_iterable(
            e["structured"].get("Mind Space", []) for e in entries
        )
    )

    cols = st.columns(3, gap="large")
    with cols[0]:
        _render_schedule(schedule_all)
    with cols[1]:
        _render_relationships(relationships_all)
    with cols[2]:
        _render_mind_space(mind_all)

    st.divider()

    # ── Clarification UI (if needed) ──────────────────────────────────────
    if clarify_mode:
        st.markdown("#### Quick clarification")
        ambiguities = st.session_state["ambiguities"]
        structured = st.session_state["pending_structured"]

        # Build form
        with st.form("clarify_form"):
            selections: dict[int, str] = {}
            for i, amb in enumerate(ambiguities):
                new_rel = structured["Relationships"][amb["new_idx"]]
                label = (
                    f"Multiple people named **{amb['name']}**. "
                    "Which one do you mean?"
                )
                opts = {
                    _rel_as_label(o): f"existing:{j}"
                    for j, o in enumerate(amb["options"])
                }
                opts["Create new person"] = "new"
                choice = st.radio(
                    label,
                    list(opts.keys()),
                    key=f"clarify_{i}",
                    index=len(opts) - 1,
                )
                selections[amb["new_idx"]] = opts[choice]
            submit = st.form_submit_button("Confirm")

        # handle confirmation
        if submit:
            # merge / discard duplicates
            for new_idx, decision in selections.items():
                if decision.startswith("existing:"):
                    # user chose an existing profile: drop new entry
                    structured["Relationships"][new_idx] = None
            structured["Relationships"] = [r for r in structured["Relationships"] if r]

            add_entry(st.session_state["pending_prompt"], structured)
            st.success("Saved!")
            # clean up state
            for k in ("clarify_mode", "ambiguities", "pending_structured", "pending_prompt"):
                st.session_state.pop(k, None)
            st.rerun()

        return  # halt normal UI until clarification resolved

    # ── Thought Input form (normal flow) ──────────────────────────────────
    st.markdown("### Thought Input")
    with st.form("prompt_form"):
        cols = st.columns([1, 6, 1])
        mode = cols[0].radio("Prompt Mode", ["add", "update"], horizontal=True)
        prompt = cols[1].text_input(
            "Thought prompt", placeholder="Reflect on today's achievements…",
            label_visibility="hidden",
        )
        submitted = cols[2].form_submit_button("Submit →")

    if submitted:
        if not prompt.strip():
            st.warning("Please enter some text first.")
        elif mode != "add":
            st.info("Update mode coming soon – only 'add' is live for now.")
        else:
            with st.spinner("Talking to your agent…"):
                try:
                    structured = _call_agent(prompt)
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))
                    return

            # detect ambiguities ------------------------------------------------
            ambiguities = _find_relationship_ambiguities(
                structured["Relationships"], relationships_all
            )
            if ambiguities:
                st.session_state["clarify_mode"] = True
                st.session_state["ambiguities"] = ambiguities
                st.session_state["pending_structured"] = structured
                st.session_state["pending_prompt"] = prompt
                st.rerun()
            else:
                add_entry(prompt, structured)
                st.success("Saved!")
                st.rerun()

    # ── Knowledge Search ─────────────────────────────────────────────────
    st.divider()
    st.markdown("### Knowledge Search")
    query = st.text_input("Search your journal", placeholder="Enter search terms…")
    if query:
        hits = search_entries(query)
        if not hits:
            st.info("No matches found.")
        else:
            for doc in hits:
                with st.expander(doc["prompt"][:80] + "…"):
                    st.json(doc["structured"])


if __name__ == "__main__":
    main()
