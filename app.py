import pandas as pd
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

st.set_page_config(page_title="Student Marks", page_icon="🎓", layout="centered")


# ------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------
def build_csv_url(tab_name):
    return (
        "https://docs.google.com/spreadsheets/d/"
        + SHEET_ID
        + "/gviz/tq?tqx=out:csv&sheet="
        + quote(tab_name)
    )


def clean_dataframe(df):
    df = df.copy()
    df.columns = [str(col).strip() for col in df.columns]
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
    df = pd.read_csv(build_csv_url(tab_name), dtype=str, keep_default_na=False)
    return clean_dataframe(df)


def get_display_value(raw_value):
    text = str(raw_value).strip()

    if text == "" or text.lower() == "nan":
        return "Upcoming"

    if text.upper() in ABSENT_WORDS:
        return "Absent"

    return text


def split_tab_name(tab_name):
    parts = tab_name.split(" ")
    return parts[0], parts[-1]


# ------------------------------------------------------------------
# Page
# ------------------------------------------------------------------
st.title("🎓 Student Marks")

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
except Exception:
    st.error("Could not load the sheet tab: " + tab_name)
    st.info("Make sure the Google Sheet is shared as 'Anyone with the link can view'.")
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
    value = get_display_value(student[subject])
    column.metric(subject, value)
