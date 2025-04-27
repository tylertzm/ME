# app.py
# ─────────────────────────────────────────────────────────────────────────────
# Streamlit front-end for ME-Journal – keeps all past items visible.
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

# ─── small helpers ──────────────────────────────────────────────────────────
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
            html.append(
                "<br>".join(f"{k}: {v}" for k, v in details.items()) + "<br>"
            )
        if rel.get("notes"):
            html.append(
                "<ul>" + "".join(f"<li>{n}</li>" for n in rel["notes"]) + "</ul>"
            )
        html.append("</p>")
    _block("".join(html))


def _render_mind_space(items: list[dict]) -> None:
    if not items:
        _block("<h3>Mind Space</h3><p><em>Mind is clear! ✨</em></p>")
        return
    lis = "".join(f"<li>{t['thought']}</li>" for t in items)
    _block(f"<h3>Mind Space</h3><ul>{lis}</ul>")


# ─── main app ───────────────────────────────────────────────────────────────
def main() -> None:
    # ── header ────────────────────────────────────────────────────────────
    st.markdown("<h1>ME Journal</h1>", unsafe_allow_html=True)
    st.date_input(
        "Journal Date",
        value=_dt.date.today(),
        label_visibility="collapsed",
    )
    st.divider()

    # ── gather ALL entries & flatten sections ─────────────────────────────
    entries = all_entries()  # oldest ➜ newest
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

    # ── render three panels ───────────────────────────────────────────────
    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        _render_schedule(schedule_all)
    with c2:
        _render_relationships(relationships_all)
    with c3:
        _render_mind_space(mind_all)

    st.divider()

    # ── Thought Input form ────────────────────────────────────────────────
    st.markdown("### Thought Input")
    with st.form("prompt_form"):
        cols = st.columns([1, 6, 1])
        mode = cols[0].radio(
            "Prompt Mode", options=["add", "update"], horizontal=True
        )
        prompt = cols[1].text_input(
            "Thought prompt",
            placeholder="Reflect on today's achievements…",
            label_visibility="hidden",
        )
        with cols[2]:
            st.markdown("<br>", unsafe_allow_html=True)
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
                    add_entry(prompt, structured)
                    st.success("Saved!")
                    st.rerun()
                except Exception as exc:  # noqa: BLE001
                    st.error(str(exc))

    # ── Knowledge Search ─────────────────────────────────────────────────
    st.divider()
    st.markdown("### Knowledge Search")
    query = st.text_input(
        "Search your journal", placeholder="Enter search terms…"
    )
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
