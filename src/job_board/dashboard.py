import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

SUMMARY_COLUMNS = [
    'id',
    "job_title",
    "company",
    "location",
    "salary_min",
    "salary_max",
    "resume_score",
]

ENGINE = create_engine("sqlite:///jobs.db")

st.set_page_config(
    page_title="Job Dashboard",
    layout="wide"
)

@st.cache_data
def load_data():
    return pd.read_sql("SELECT * FROM jobs", ENGINE)

df = load_data()

assert "id" in df.columns

left, right = st.columns([4,3])

with left:
    st.subheader("Jobs")

    summary_df = df[SUMMARY_COLUMNS]\
        .sort_values('resume_score', ascending=False)\
        .copy()

    selected_id = st.selectbox(
        "Select a job",
        options=summary_df["id"],
        format_func=lambda i: (
            summary_df.loc[summary_df["id"] == i, "job_title"].iloc[0]
            + " @ "
            + summary_df.loc[summary_df["id"] == i, "company"].iloc[0]
        ),
    )

    st.dataframe(
        summary_df.drop(columns=["id"]),
        use_container_width=True,
        hide_index=True,
        column_config={
            "url": st.column_config.LinkColumn("Link"),
        },
    )

with right:
    st.subheader("Job Details")

    job = df[df["id"] == selected_id].iloc[0]

    st.markdown(f"### {job['job_title']}")
    st.markdown(f"**Company:** {job['company']}")
    st.markdown(f"**Location:** {job['location']}")
    st.markdown(f"**Fit score:** {job['resume_score']}")
    st.markdown(f"[Open job posting]({job['url']})")

    st.divider()

    if "description" in job:
        st.markdown("#### Description")
        st.write(job["description"])

    if "requirements" in job:
        st.markdown("#### Requirements")
        st.write(job["requirements"])

    if "notes" in job:
        st.markdown("#### Notes")
        st.write(job["notes"])

    # notes = st.text_area("Notes", job.get("notes", ""))

    # if st.button("Save notes"):
    #     with ENGINE.connect() as conn:
    #         conn.execute(
    #             text(
    #                 f"UPDATE jobs SET notes = '{notes}' "
    #                 f"WHERE id = {selected_id}"
    #             )
    #         )
    

    #     st.success("Notes saved!")
    #     st.write("Saved notes:", notes)
