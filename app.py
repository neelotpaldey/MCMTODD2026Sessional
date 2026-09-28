import html
import io

import pandas as pd
import requests
import streamlit as st
from urllib.parse import quote

# ------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------
SHEET_ID = "158EXs5cgEn3PPnQ-RnYYkysy17AnAgzCRaOAMkynNcU"

# Each tab is named "<University> <Semester>", for example "MGKVP 5".
# Add new tabs here and they will appear in the dropdowns automatically.
SHEET_TABS = ["MGKVP 5", "MGKVP 3", "VBSPU 5", "VBSPU 3"]

ABSENT_WORDS = ["ABS", "AB", "ABSENT"]
MEDICAL_WORDS = ["ML"]

# Card colours for each kind of result: (background, text, border)
COLORS = {
    "marks": ("#d1e7dd", "#0f5132", "#badbcc"),
    "absent": ("#f8d7da", "#842029", "#f1aeb5"),
    "medical": ("#fff3cd", "#664d03", "#ffe69c"),
    "upcoming": ("#e2e3e5", "#41464b", "#c4c8cb"),
}

st.set_page_config(page_title="Sessional Marks Odd 2026", page_icon="🎓", layout="centered")


# ------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------
def build_csv_url(tab_name):
    return (
        "https://docs.google.com/spreadsheets/d/"
        + SHEET_ID
        + "/gviz/tq?tqx=out:csv&headers=1&sheet="
        + quote(tab_name)
    )


def clean_dataframe(df):
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]

    if "Name" not in df.columns:
        raise ValueError("Column 'Name' not found. Columns found: " + ", ".join(df.columns))
    df["Name"] = df["Name"].astype(str).str.strip()
    df = df[df["Name"] != ""]
    df = df.reset_index(drop=True)

    # Two students can share a name, so number them to keep the dropdown unique
    is_duplicate = df.duplicated("Name", keep=False)
    counter = df.groupby("Name").cumcount() + 1
    df["Label"] = df["Name"]
    df.loc[is_duplicate, "Label"] = df["Name"] + " (#" + counter.astype(str) + ")"
    return df


@st.cache_data(ttl=60)
def load_tab(tab_name):
    response = requests.get(build_csv_url(tab_name), timeout=20)
    response.raise_for_status()
    text = response.content.decode("utf-8")
    df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
    return clean_dataframe(df)


def get_result(raw_value):
    """Returns (text to show, kind of result)."""
    text = str(raw_value).strip()

    if text == "" or text.lower() == "nan":
        return "Upcoming", "upcoming"

    if text.upper() in ABSENT_WORDS:
        return "Absent", "absent"

    if text.upper() in MEDICAL_WORDS:
        return "Medical", "medical"

    return text, "marks"


def build_card(subject, value, kind):
    background, text_color, border = COLORS[kind]
    return (
        '<div style="background:' + background
        + ";color:" + text_color
        + ";border:1px solid " + border
        + ';border-radius:10px;padding:14px 8px;text-align:center;">'
        + '<div style="font-size:0.85rem;font-weight:600;">'
        + html.escape(subject)
        + "</div>"
        + '<div style="font-size:1.4rem;font-weight:700;margin-top:4px;">'
        + html.escape(value)
        + "</div></div>"
    )


def split_tab_name(tab_name):
    parts = tab_name.split(" ")
    return parts[0], parts[-1]


# ------------------------------------------------------------------
# Page
# ------------------------------------------------------------------
st.title("🎓 Sessional Marks Odd 2026")

if st.button("🔄 Refresh data"):
    st.cache_data.clear()

# Step 1: university
universities = []
for tab in SHEET_TABS:
    university, semester = split_tab_name(tab)
    if university not in universities:
        universities.append(university)

selected_university = st.selectbox("University", universities)

# Step 2: semester (only those that exist for the chosen university)
semesters = []
for tab in SHEET_TABS:
    university, semester = split_tab_name(tab)
    if university == selected_university:
        semesters.append(semester)

selected_semester = st.selectbox("Semester", semesters)

tab_name = selected_university + " " + selected_semester

# Step 3: student name
try:
    data = load_tab(tab_name)
except Exception as error:
    st.error("Could not load the sheet tab: " + tab_name)
    st.info("Make sure the Google Sheet is shared as 'Anyone with the link can view'.")
    st.code(type(error).__name__ + ": " + str(error))
    st.stop()

selected_label = st.selectbox("Student name", data["Label"].tolist())

# ------------------------------------------------------------------
# Result
# ------------------------------------------------------------------
student = data[data["Label"] == selected_label].iloc[0]
subjects = [col for col in data.columns if col not in ["Name", "Label"]]

st.divider()
st.subheader(student["Name"])
st.caption(selected_university + " • Semester " + selected_semester)

columns = st.columns(len(subjects))
for column, subject in zip(columns, subjects):
    value, kind = get_result(student[subject])
    column.markdown(build_card(subject, value, kind), unsafe_allow_html=True)
