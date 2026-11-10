import html
import io
import re
from urllib.parse import quote

import pandas as pd
import requests
import streamlit as st


# ==============================================================
# SETTINGS
# ==============================================================

SHEET_ID = "158EXs5cgEn3PPnQ-RnYYkysy17AnAgzCRaOAMkynNcU"

SHEET_TABS = [
    "MGKVP 1",
    "MGKVP 3",
    "MGKVP 5",
    "VBSPU 1",
    "VBSPU 3",
    "VBSPU 5",
]

PASS_MARKS = {
    "MGKVP": 8.5,
    "VBSPU": 10.5,
}

# Existing GIDs. Blank GIDs will be discovered automatically.
SHEET_GIDS = {
    "MGKVP 1": "655838173",
    "MGKVP 3": "640255053",
    "MGKVP 5": "0",
    "VBSPU 1": "748415436",
    "VBSPU 3": "1513077383",
    "VBSPU 5": "2057130896",
}

# Either-or subjects
EITHER_OR_SUBJECTS = {
    "MGKVP 5": ["SPM", "NM"]
}

ABSENT_WORDS = ["ABS", "AB", "ABSENT"]
MEDICAL_WORDS = ["ML"]
JOB_WORDS = ["JOB"]

COLORS = {
    "marks": ("#d1e7dd", "#0f5132", "#badbcc"),
    "absent": ("#f8d7da", "#842029", "#f1aeb5"),
    "medical": ("#fff3cd", "#664d03", "#ffe69c"),
    "job": ("#cfe2ff", "#084298", "#9ec5fe"),
    "upcoming": ("#e2e3e5", "#41464b", "#c4c8cb"),
}

st.set_page_config(
    page_title="Sessional Marks Odd 2026",
    page_icon="🎓",
    layout="centered"
)


# ==============================================================
# GOOGLE SHEET FUNCTIONS
# ==============================================================

@st.cache_data(ttl=3600)
def discover_gids():
    """Automatically discover Google Sheet tab names and GIDs."""

    page_url = (
        "https://docs.google.com/spreadsheets/d/"
        + SHEET_ID
        + "/htmlview"
    )

    found = {}

    try:
        response = requests.get(
            page_url,
            timeout=20,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        response.raise_for_status()
        page = response.text

    except Exception:
        return found

    pattern = r'id="sheet-button-(\d+)"[^>]*>(.*?)</li>'

    for gid, inner in re.findall(pattern, page, re.DOTALL):
        name = html.unescape(
            re.sub(r"<[^>]+>", "", inner)
        ).strip()

        found[name] = gid

    return found


def get_gid(tab_name):
    """Get configured GID or discover it automatically."""

    typed_gid = SHEET_GIDS.get(tab_name, "")

    if typed_gid:
        return typed_gid

    return discover_gids().get(tab_name, "")


def build_csv_url(tab_name):

    gid = get_gid(tab_name)

    if gid:
        return (
            f"https://docs.google.com/spreadsheets/d/"
            f"{SHEET_ID}/export?format=csv&gid={gid}"
        )

    return (
        f"https://docs.google.com/spreadsheets/d/"
        f"{SHEET_ID}/gviz/tq?tqx=out:csv&headers=1"
        f"&sheet={quote(tab_name)}"
    )


# ==============================================================
# DATA CLEANING
# ==============================================================

def clean_dataframe(df):

    df = df.copy()

    df.columns = [
        str(col).strip()
        for col in df.columns
    ]

    # IMPORTANT:
    # Do not remove completely empty subject columns.
    # They must remain visible as Upcoming.

    if "Name" not in df.columns:
        raise ValueError(
            "Column 'Name' not found. Columns found: "
            + ", ".join(df.columns)
        )

    df["Name"] = (
        df["Name"]
        .astype(str)
        .str.strip()
    )

    df = df[
        (df["Name"] != "")
        & (~df["Name"].str.lower().isin(["nan", "none", "null"]))
    ].copy()

    df = df.reset_index(drop=True)

    # Handle duplicate student names
    is_duplicate = df.duplicated(
        "Name",
        keep=False
    )

    counter = df.groupby("Name").cumcount() + 1

    df["Label"] = df["Name"]

    df.loc[is_duplicate, "Label"] = (
        df["Name"]
        + " (#"
        + counter.astype(str)
        + ")"
    )

    return df


@st.cache_data(ttl=60)
def load_tab(tab_name):

    response = requests.get(
        build_csv_url(tab_name),
        timeout=20
    )

    response.raise_for_status()

    text = response.content.decode("utf-8-sig")

    df = pd.read_csv(
        io.StringIO(text),
        dtype=str,
        keep_default_na=False
    )

    return clean_dataframe(df)


# ==============================================================
# RESULT PROCESSING
# ==============================================================

def get_result(raw_value):
    """Returns (display text, result type)."""

    value = str(raw_value).strip()

    # Blank values
    if value == "" or value.lower() in [
        "nan", "none", "null"
    ]:
        return "Upcoming", "upcoming"

    # Absent
    if value.upper() in ABSENT_WORDS:
        return "Absent", "absent"

    # Medical
    if value.upper() in MEDICAL_WORDS:
        return "Medical", "medical"

    # Job
    if value.upper() in JOB_WORDS:
        return "JOB", "job"

    return value, "marks"


def get_pass_icon(value, kind, university):

    if kind != "marks":
        return ""

    try:
        marks = float(value)
    except (ValueError, TypeError):
        return ""

    if marks >= PASS_MARKS[university]:
        return "👍"

    return "👎"


# ==============================================================
# RESULT CARD
# ==============================================================

def build_card(subject, value, kind, icon):

    background, text_color, border = COLORS[kind]

    icon_html = ""

    if icon:
        icon_html = (
            '<div style="font-size:1.4rem;margin-top:2px;">'
            + icon
            + "</div>"
        )

    return (
        '<div style="background:'
        + background
        + ";color:"
        + text_color
        + ";border:1px solid "
        + border
        + ';border-radius:10px;padding:14px 8px;'
        + 'text-align:center;min-height:100px;">'

        + '<div style="font-size:0.85rem;font-weight:600;">'
        + html.escape(subject)
        + "</div>"

        + '<div style="font-size:1.4rem;font-weight:700;'
        + 'margin-top:4px;">'
        + html.escape(value)
        + "</div>"

        + icon_html
        + "</div>"
    )


# ==============================================================
# SUBJECT HANDLING
# ==============================================================

def is_blank(raw_value):

    value = str(raw_value).strip()

    return value == "" or value.lower() in [
        "nan", "none", "null"
    ]


def get_subject_items(student, subjects, tab_name):

    either_or = EITHER_OR_SUBJECTS.get(
        tab_name,
        []
    )

    pair = [
        subject
        for subject in either_or
        if subject in subjects
    ]

    filled = [
        subject
        for subject in pair
        if not is_blank(student[subject])
    ]

    combined_label = "/".join(pair)

    combined_added = False

    items = []

    for subject in subjects:

        if subject not in pair:

            items.append(
                (subject, student[subject])
            )

        elif len(filled) == 0:

            if not combined_added:

                items.append(
                    (combined_label, "")
                )

                combined_added = True

        elif subject in filled:

            items.append(
                (subject, student[subject])
            )

    return items


def split_tab_name(tab_name):

    parts = tab_name.split(" ")

    return parts[0], parts[-1]


# ==============================================================
# STREAMLIT PAGE
# ==============================================================

st.title("🎓 Sessional Marks Odd 2026")

st.caption(
    "Check your sessional examination marks."
)


# --------------------------------------------------------------
# REFRESH DATA
# --------------------------------------------------------------

if st.button(
    "🔄 Refresh data",
    use_container_width=True
):

    st.cache_data.clear()
    st.rerun()


# --------------------------------------------------------------
# STEP 1: UNIVERSITY
# --------------------------------------------------------------

universities = []

for tab in SHEET_TABS:

    university, semester = split_tab_name(tab)

    if university not in universities:
        universities.append(university)


selected_university = st.selectbox(
    "University",
    universities,
    index=None,
    placeholder="Select University"
)

if selected_university is None:
    st.stop()


# --------------------------------------------------------------
# STEP 2: SEMESTER
# --------------------------------------------------------------

semesters = []

for tab in SHEET_TABS:

    university, semester = split_tab_name(tab)

    if university == selected_university:
        semesters.append(semester)


selected_semester = st.selectbox(
    "Semester",
    semesters,
    index=None,
    placeholder="Select Semester",
    key="semester_" + selected_university
)

if selected_semester is None:
    st.stop()


tab_name = (
    selected_university
    + " "
    + selected_semester
)


# --------------------------------------------------------------
# STEP 3: LOAD STUDENT DATA
# --------------------------------------------------------------

try:

    data = load_tab(tab_name)

except Exception as error:

    st.error(
        "Could not load the sheet tab: "
        + tab_name
    )

    st.info(
        "Make sure the Google Sheet is shared as "
        "'Anyone with the link can view'."
    )

    st.code(
        type(error).__name__
        + ": "
        + str(error)
    )

    st.stop()


# GID warning
if get_gid(tab_name) == "":

    st.warning(
        "Could not find the GID for "
        + tab_name
        + ". Please verify the tab name and GID."
    )


# --------------------------------------------------------------
# STEP 4: STUDENT NAME
# --------------------------------------------------------------

selected_label = st.selectbox(
    "Student name",
    data["Label"].tolist(),
    index=None,
    placeholder="Select Name",
    key="name_" + tab_name
)

if selected_label is None:
    st.stop()


# ==============================================================
# DISPLAY RESULT
# ==============================================================

student = data[
    data["Label"] == selected_label
].iloc[0]

subjects = [
    col
    for col in data.columns
    if col not in ["Name", "Label"]
]


st.divider()

st.subheader(student["Name"])

st.caption(
    selected_university
    + " • Semester "
    + selected_semester
    + " • Pass marks: "
    + str(PASS_MARKS[selected_university])
)


# --------------------------------------------------------------
# SUBJECT RESULT ITEMS
# --------------------------------------------------------------

items = get_subject_items(
    student,
    subjects,
    tab_name
)


# --------------------------------------------------------------
# DISPLAY RESULT CARDS
# --------------------------------------------------------------

if items:

    columns = st.columns(3)

    for index, item in enumerate(items):

        label, raw_value = item

        value, kind = get_result(raw_value)

        icon = get_pass_icon(
            value,
            kind,
            selected_university
        )

        with columns[index % 3]:

            st.markdown(
                build_card(
                    label,
                    value,
                    kind,
                    icon
                ),
                unsafe_allow_html=True
            )

else:

    st.info("No subject records available.")


# ==============================================================
# FOOTER
# ==============================================================

st.divider()

st.caption(
    "Sessional Marks Odd 2026 | "
    "Made with ❤️ by Neelotpal Sir"
)
