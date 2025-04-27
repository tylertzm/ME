# Home.py
# ─────────────────────────────────────────────────────────────────────────────
# ME-Journal – tidy Morning / Afternoon / Evening / Night / Future layout.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import copy
import datetime as _dt
import itertools
import json
import os
import base64
from pathlib import Path
from typing import Dict, List, Tuple

import dateutil.parser as _dparse
import requests
import streamlit as st

from database import (
    add_entry,
    entries_by_date,
    entries_with_future_events,
    purge_schedule_task,
    search_entries,
)

# ─── Restack agent config (unchanged) ───────────────────────────────────────
BASE_URL = os.getenv("RESTACK_BASE_URL", "https://res2tsut.clj5khk.gcp.restack.it").rstrip("/")
AGENT_ID = os.getenv("RESTACK_AGENT_ID", "d7e08832-AgentStructureResult")
RUN_ID = os.getenv("RESTACK_RUN_ID", "01967657-63b9-7272-9413-c01c93a13c6e")
RESTACK_ENDPOINT = f"{BASE_URL}/api/agents/AgentStructureResult/{AGENT_ID}/{RUN_ID}"

# ─── Page config & CSS injection ───────────────────────────────────────────
st.set_page_config(
    page_title="ME Journal",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed",
)

css_path = Path(__file__).parent / "../style.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

# ─── Utilities ─────────────────────────────────────────────────────────────
def _call_agent(prompt_text: str) -> dict:
    """Send prompt to the Restack agent and return its JSON response."""
    payload = {
        "eventName": "messages",
        "eventInput": {"messages": [{"role": "user", "content": prompt_text}]},
    }
    resp = requests.put(RESTACK_ENDPOINT, json=payload, timeout=90)
    resp.raise_for_status()
    for msg in reversed(resp.json()):
        if msg.get("role") == "assistant":
            return json.loads(msg["content"])
    raise RuntimeError("No assistant message returned")


def _block(html: str) -> None:
    st.markdown(f"<div class='block'>{html}</div>", unsafe_allow_html=True)


def _ordinal(n: int) -> str:
    """Return an ordinal string: 1 → 1st, 2 → 2nd, 3 → 3rd …"""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


# ─── Renderers ─────────────────────────────────────────────────────────────
def _render_schedule(items: list[dict], selected_date: _dt.date) -> None:
    groups = {s: [] for s in ("Morning", "Afternoon", "Evening", "Night", "Future")}

    for ev in items:
        ev_date = _parse_date(ev.get("event_date")) or selected_date
        if ev_date > selected_date:
            groups["Future"].append(ev)
            continue

        hour = _parse_time(ev.get("time", "12:00")).hour
        if   5 <= hour < 12: groups["Morning"].append(ev)
        elif 12 <= hour < 17: groups["Afternoon"].append(ev)
        elif 17 <= hour < 21: groups["Evening"].append(ev)
        else:                 groups["Night"].append(ev)

    html = ["<h3>Schedule</h3>"]
    for section in groups:
        html.append(f"<h4 class='sched-section'>{section}</h4><ul>")
        if not groups[section]:
            html.append("<li class='no-events'>— No events —</li>")
        else:
            for ev in groups[section]:
                label = f"<strong>{ev['time']}</strong>" if ev.get("time") else "—"
                html.append(f"<li>{label} – {ev['task']}</li>")
        html.append("</ul>")
    _block("".join(html))


def _render_relationships(items: list[dict]) -> None:
    if not items:
        _block("<h3>Relationships</h3><p><em>No relationship info.</em></p>")
        return
    html = ["<h3>Relationships</h3>"]
    for r in items:
        html.append(f"<p><strong>{r['name']}</strong> — {r.get('role','—')}<br>")
        if det := r.get("details"):
            html.append("<br>".join(f"{k}: {v}" for k, v in det.items()) + "<br>")
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


# ─── Relationship helpers (logic unchanged) ────────────────────────────────
def _relationship_key(r: dict) -> str: return r["name"].strip().lower()


def _merge_additive(a: dict, b: dict) -> dict:
    merged = copy.deepcopy(a)
    if b.get("role"): merged["role"] = b["role"]
    merged.setdefault("details", {}).update(b.get("details", {}))
    merged.setdefault("notes", [])
    for n in b.get("notes", []):
        if n not in merged["notes"]: merged["notes"].append(n)
    return merged


def _diff_conflicts(a: dict, b: dict) -> Tuple[bool, List[str]]:
    conflicts = []
    if a.get("role") and b.get("role") and a["role"] != b["role"]:
        conflicts.append("role")
    for k, v in (b.get("details") or {}).items():
        if k in a.get("details", {}) and a["details"][k] != v:
            conflicts.append(f"detail:{k}")
    return bool(conflicts), conflicts


def _dedup_relationships(lst: List[dict]) -> List[dict]:
    res: Dict[str, dict] = {}
    for r in lst:
        k = _relationship_key(r)
        res[k] = _merge_additive(res[k], r) if k in res else copy.deepcopy(r)
    return list(res.values())


def _rel_label(r: dict) -> str:
    role = r.get("role", "—")
    det = ", ".join(f"{k}:{v}" for k, v in (r.get("details") or {}).items())
    return f"{role} | {det}" if det else role


# ─── Schedule helpers ──────────────────────────────────────────────────────
def _schedule_key(s: dict) -> str: return s["task"].strip().lower()


def _dedup_schedule(evs: List[dict]) -> List[dict]:
    d = {_schedule_key(e): e for e in evs}
    return sorted(d.values(), key=lambda e: (e.get("event_date") or "", e["time"]))


def _parse_date(txt: str | None) -> _dt.date | None:
    if not txt:
        return None
    try:
        return _dparse.parse(txt, dayfirst=True).date()
    except Exception:
        return None


def _parse_time(txt: str | None) -> _dt.time:
    try:
        return _dparse.parse(txt).time()
    except Exception:
        return _dt.time(hour=12)
    

# Encode the image as base64
def get_base64(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()


# ─── Main application ──────────────────────────────────────────────────────
def main() -> None:
    # ── Centered title ──
    # st.markdown(
    #     "<h1 style='text-align:center; margin-bottom:0.25rem;'>ME Journal</h1>",
    #     unsafe_allow_html=True,
    # )

    # Add the logo and center it
    logo_path = Path(__file__).parent / "../resources/Melogo.png"
    logo_base64 = get_base64(logo_path)
    if logo_path.exists():
        logo_html = f"<img src='data:image/png;base64,{logo_base64}' style='display:block; margin:auto; width: 350px;'>"
        st.markdown(logo_html, unsafe_allow_html=True)

    st.markdown(
        """
        <style>
        /* widen the whole widget container */
        .stDateInput > div {
            width: 100% !important;
        }

        /* beef up the text box itself */
        .stDateInput input {
            font-size: 1.4rem !important;   /* bigger text */
            padding: 0.75rem 1rem !important; /* taller field */
        }

        /* make the calendar-icon button larger */
        .stDateInput button {
            font-size: 1.4rem !important;
            padding: 0.5rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # --- Centered, larger date-picker ---
    today = _dt.date.today()
    col_l, col_mid, col_r = st.columns([3.5, 4, 1], gap="large")  # give the centre more space
    with col_mid:
        selected_date = st.date_input(
            "Journal Date",          # keep the label for a11y
            today,
            label_visibility="collapsed",  # or show it if you prefer
            key="journal_date",
        )

    # Show the chosen date in friendly format
    # friendly_date = f"{_ordinal(selected_date.day)} {selected_date.strftime('%B %Y')}"
    # st.markdown(
    #     f"<p style='text-align:center; opacity:0.75; margin-top:-0.25rem;'>{friendly_date}</p>",
    #     unsafe_allow_html=True,
    # )

    st.divider()

    # ── Fetch entries ──
    entries = entries_by_date(selected_date)
    if selected_date == today:
        entries += entries_with_future_events(start=today, days_ahead=60)

    raw_schedule = list(
        itertools.chain.from_iterable(e["structured"].get("Schedule", []) for e in entries)
    )
    raw_rels_all = list(
        itertools.chain.from_iterable(e["structured"].get("Relationships", []) for e in entries)
    )
    schedule_all = _dedup_schedule(raw_schedule)
    rels_all = _dedup_relationships(raw_rels_all)
    mind_all = list(
        itertools.chain.from_iterable(e["structured"].get("Mind Space", []) for e in entries)
    )

    # ── Main 3-column layout ──
    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        _render_schedule(schedule_all, selected_date)
    with c2:
        _render_relationships(rels_all)
    with c3:
        _render_mind_space(mind_all)

    st.divider()

    # ── Handle pending clarifications (unchanged logic) ──
    if st.session_state.get("await_clarify"):
        _handle_clarifications(selected_date)  # defined further below
        return  # stop early after clarification UI

    # ── Input form ──
    _input_form(selected_date, rels_all, schedule_all)

    # ── Search ──
    st.divider()
    st.markdown("### Knowledge Search")
    q = st.text_input("Talk with ME", placeholder="…")
    if q:
        hits = search_entries(q)
        if not hits:
            st.info("No matches found.")
        else:
            for doc in hits:
                with st.expander(doc["prompt"][:80] + "…"):
                    st.json(doc["structured"])


# ─── Helper sub-functions (clarification & input form logic) ───────────────
def _handle_clarifications(selected_date: _dt.date) -> None:
    """UI for resolving relationship / schedule conflicts."""
    pending = st.session_state["pending_structured"]
    prompt_txt = st.session_state["pending_prompt"]
    rel_conflicts = st.session_state["rel_conflicts"]
    sched_conflicts = st.session_state["sched_conflicts"]
    missing_sched = st.session_state["missing_sched"]

    st.markdown("#### Resolve ambiguities")
    with st.form("clarify_form"):
        decisions_rel: dict[int, str] = {}
        decisions_sched: dict[int, str] = {}
        fixed_sched: dict[int, dict] = {}

        # Relationship conflicts
        for idx, info in enumerate(rel_conflicts):
            new_rel, ex_rel = info["new"], info["existing"]
            label = f"Info about **{new_rel['name']}** conflicts with existing data."
            opts = {
                f"Update existing profile ({_rel_label(ex_rel)})": "update",
                "Keep as separate person": "separate",
                "Discard the new information": "discard",
            }
            choice = st.radio(label, list(opts.keys()), key=f"rel_choice_{idx}")
            decisions_rel[info["new_index"]] = opts[choice]
            st.markdown("---")

        # Schedule conflicts
        for idx, info in enumerate(sched_conflicts):
            new_ev, ex_ev = info["new"], info["existing"]
            label = f"Task **{new_ev['task']}** already exists at {ex_ev['time']}."
            opts = {
                f"Replace existing time/date with {new_ev['time']}": "update",
                "Keep both": "both",
                "Discard the new information": "discard",
            }
            choice = st.radio(label, list(opts.keys()), key=f"sched_choice_{idx}")
            decisions_sched[info["new_index"]] = opts[choice]
            st.markdown("---")

        # Missing schedule details
        for idx in missing_sched:
            ev = pending["Schedule"][idx]
            st.markdown(
                f"Provide missing info for **{ev['task']}** "
                f"(leave blank to cancel this item)"
            )
            date_in = st.date_input(
                "Event date", selected_date, key=f"miss_date_{idx}", format="YYYY-MM-DD"
            )
            time_in = st.time_input("Time", _dt.time(hour=9), key=f"miss_time_{idx}")
            fixed_sched[idx] = {
                "event_date": date_in.isoformat(),
                "time": time_in.strftime("%H:%M"),
            }
            st.markdown("---")

        confirmed = st.form_submit_button("Confirm")

    if not confirmed:
        return

    # Finalise relationships
    final_rels: List[dict] = []
    for idx, rel in enumerate(pending["Relationships"]):
        decision = decisions_rel.get(idx)
        if decision == "discard":
            continue
        if decision == "update":
            final_rels.append(_merge_additive(rel_conflicts[0]["existing"], rel))
        else:
            final_rels.append(rel)

    # Finalise schedule
    final_sched: List[dict] = []
    for idx, ev in enumerate(pending["Schedule"]):
        if idx in fixed_sched:
            ev.update(fixed_sched[idx])
            if not ev["event_date"] or not ev["time"]:
                continue

        decision = decisions_sched.get(idx)
        if decision == "discard":
            continue
        if decision == "update":
            purge_schedule_task(_schedule_key(ev))
        final_sched.append(ev)

    pending["Relationships"] = final_rels
    pending["Schedule"] = final_sched

    jd = _determine_journal_date(pending, selected_date)
    for ev in pending["Schedule"]:
        purge_schedule_task(_schedule_key(ev))
    add_entry(prompt_txt, pending, jd)

    # Clear state & refresh
    for k in (
        "await_clarify",
        "pending_structured",
        "pending_prompt",
        "rel_conflicts",
        "sched_conflicts",
        "missing_sched",
    ):
        st.session_state.pop(k, None)
    st.success("Saved!")
    st.rerun()


def _input_form(selected_date: _dt.date, rels_all: list[dict], schedule_all: list[dict]) -> None:
    """Prompt input / scheduling form and its logic."""
    st.markdown("### Thought Input / Scheduling")
    with st.form("prompt_form"):
        cols = st.columns([8, 2])
        prompt = cols[0].text_input(
            label="Thought prompt",
            placeholder="Reflect on today…  |  “At 3 pm call Alice”",
            label_visibility="hidden",
        )
        cols[1].markdown("<br>", unsafe_allow_html=True)
        submitted = cols[1].form_submit_button("Submit →", use_container_width=True)

    if not submitted:
        return

    if not prompt.strip():
        st.warning("Please enter some text first.")
        st.stop()

    with st.spinner("Processing…"):
        try:
            structured = _call_agent(prompt)
        except Exception as exc:
            st.error(str(exc))
            st.stop()

    # Relationship conflict detection & merge
    rel_conflicts: list[dict] = []
    merged_rels: list[dict] = []
    rel_map = {_relationship_key(r): r for r in rels_all}
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
            rel_conflicts.append(
                {"new_index": idx, "new": new_rel, "existing": existing}
            )
            merged_rels.append(new_rel)

    # Schedule conflict detection
    sched_conflicts: list[dict] = []
    missing_sched: list[int] = []
    sched_map = {_schedule_key(e): e for e in schedule_all}
    for idx, ev in enumerate(structured["Schedule"]):
        if ev.get("date") and not ev.get("event_date"):
            ev["event_date"] = _parse_date(ev["date"]).isoformat() if ev["date"] else None
        if not ev.get("event_date") or not ev.get("time"):
            missing_sched.append(idx)
        elif _schedule_key(ev) in sched_map:
            existing = sched_map[_schedule_key(ev)]
            if existing["time"] != ev["time"] or existing.get("event_date") != ev.get("event_date"):
                sched_conflicts.append(
                    {"new_index": idx, "new": ev, "existing": existing}
                )

    needs_clarification = rel_conflicts or sched_conflicts or missing_sched
    if needs_clarification:
        st.session_state.update(
            await_clarify=True,
            pending_structured=structured,
            pending_prompt=prompt,
            rel_conflicts=rel_conflicts,
            sched_conflicts=sched_conflicts,
            missing_sched=missing_sched,
        )
        st.rerun()
        return

    structured["Relationships"] = merged_rels
    jd = _determine_journal_date(structured, selected_date)
    for ev in structured["Schedule"]:
        purge_schedule_task(_schedule_key(ev))
    add_entry(prompt, structured, jd)
    st.success("Saved!")
    st.rerun()


# ─── Helper: pick journal date from schedule or fallback ───────────────────
def _determine_journal_date(structured: dict, fallback: _dt.date) -> _dt.date:
    dates = {ev.get("event_date") for ev in structured.get("Schedule", []) if ev.get("event_date")}
    if len(dates) == 1:
        d = _parse_date(dates.pop())
        if d:
            return d
    return fallback


# ─── Run ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()