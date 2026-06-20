"""Streamlit dashboard for remote/global English-primary job hunting."""

from __future__ import annotations

import csv
import io

import streamlit as st

from job_search import DATE_WINDOWS, default_search_phrase, search_jobs


st.set_page_config(page_title="Jobseeker Dashboard", layout="wide")

st.title("Jobseeker Dashboard")

with st.sidebar:
    st.header("Search")
    date_window = st.selectbox("Posted within", list(DATE_WINDOWS.keys()))
    max_per_source = st.slider("Listings per source", 25, 200, 80, step=25)
    min_match_score = st.slider("Minimum match score", 1, 10, 5)
    fuzzy_mode = st.selectbox("Fuzzy word match", ["Balanced", "Strict", "Loose"])
    strict_remote = st.checkbox("Remote and global only", value=True, disabled=True)
    strict_english = st.checkbox("English-primary evidence only", value=True, disabled=True)

job_description = st.text_area(
    "Job description",
    height=210,
    placeholder="Paste the target job description, role summary, or search profile here.",
)

suggested_phrase = default_search_phrase(job_description) if job_description.strip() else ""
search_phrase = st.text_input("Search phrase", value=suggested_phrase)

run_search = st.button("Hunt for jobs", type="primary", disabled=not job_description.strip())

if run_search:
    fuzzy_threshold = {
        "Strict": 0.9,
        "Balanced": 0.84,
        "Loose": 0.78,
    }[fuzzy_mode]

    with st.spinner("Searching remote/global English-primary listings..."):
        try:
            listings = search_jobs(
                job_description=job_description,
                date_window_label=date_window,
                search_phrase=search_phrase,
                max_per_source=max_per_source,
                min_match_score=min_match_score,
                fuzzy_threshold=fuzzy_threshold,
            )
        except Exception as exc:
            st.error(f"Search failed: {exc}")
            st.stop()

    st.session_state["job_results"] = listings
    st.session_state["last_search"] = {
        "date_window": date_window,
        "search_phrase": search_phrase,
        "count": len(listings),
    }
    from governance_logger import log_success
    log_success("jobseeker", "Agent completed successfully", {
        "count": len(listings),
        "search_phrase": search_phrase,
        "result": {"matches": len(listings)}
    })

listings = st.session_state.get("job_results", [])
last_search = st.session_state.get("last_search")

if last_search:
    c1, c2, c3 = st.columns(3)
    c1.metric("Matches", last_search["count"])
    c2.metric("Window", last_search["date_window"])
    c3.metric("Query", last_search["search_phrase"] or "auto")

if listings:
    rows = [listing.to_row() for listing in listings]
    st.dataframe(
        rows,
        use_container_width=True,
        column_config={
            "url": st.column_config.LinkColumn("Apply"),
            "description": st.column_config.TextColumn("Description", width="large"),
        },
        hide_index=True,
    )

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    st.download_button(
        "Download CSV",
        data=buffer.getvalue(),
        file_name="remote_global_english_jobs.csv",
        mime="text/csv",
    )

    st.subheader("Review Cards")
    for listing in listings:
        with st.container(border=True):
            top = st.columns([3, 1])
            with top[0]:
                st.markdown(f"### [{listing.title}]({listing.url})")
                st.caption(f"{listing.company} | {listing.source} | {listing.location}")
            with top[1]:
                st.metric("Match score", listing.match_score)
            st.write(listing.description[:900])
            st.caption("Matched keywords: " + (", ".join(listing.keyword_matches) or "none"))
            st.caption("English evidence: " + " | ".join(listing.english_evidence))
elif last_search:
    st.warning("No jobs matched all strict filters for this search window.")
else:
    st.info("Paste a job description to start.")
