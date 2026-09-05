import base64
import hashlib
import streamlit as st

st.set_page_config(
    page_title="My Textbook Library",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.stApp { background: #f5f6f8; }
section[data-testid="stSidebar"] {
    background: white;
    border-right: 1px solid #e6e8eb;
}
.title { font-size: 30px; font-weight: 700; margin-bottom: 4px; }
.subtitle { color: #777; margin-bottom: 16px; }
</style>
""", unsafe_allow_html=True)

if "books" not in st.session_state:
    st.session_state.books = {}

def book_id(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()[:12]

def pdf_iframe(data: bytes, page: int = 1, height: int = 900):
    encoded = base64.b64encode(data).decode("utf-8")
    src = f"data:application/pdf;base64,{encoded}#page={page}&zoom=page-width"
    html = (
        '<iframe src="' + src + '" width="100%" height="' + str(height) +
        '" style="border:0; border-radius:12px; background:white;"></iframe>'
    )
    st.components.v1.html(html, height=height + 10, scrolling=False)

with st.sidebar:
    st.markdown("## 📚 My Library")

    uploads = st.file_uploader(
        "Import textbook PDF",
        type=["pdf"],
        accept_multiple_files=True
    )

    if uploads:
        for uploaded in uploads:
            data = uploaded.getvalue()
            bid = book_id(data)
            if bid not in st.session_state.books:
                st.session_state.books[bid] = {
                    "name": uploaded.name,
                    "data": data,
                }
        st.success(f"{len(uploads)} PDF(s) ready.")

    if not st.session_state.books:
        st.caption("Upload a PDF to start.")
        st.stop()

    ids = list(st.session_state.books.keys())
    names = [st.session_state.books[i]["name"] for i in ids]

    selected_name = st.selectbox("Choose textbook", names)
    selected_id = ids[names.index(selected_name)]
    book = st.session_state.books[selected_id]

    st.divider()
    st.caption("PDFs stay only during this active Streamlit session.")

    if st.button("🗑️ Remove selected book", use_container_width=True):
        del st.session_state.books[selected_id]
        st.rerun()

st.markdown(f'<div class="title">{book["name"]}</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Private PDF reader • no extra PDF package required</div>',
    unsafe_allow_html=True
)

tab_read, tab_help = st.tabs(["📖 Read", "ℹ️ How to use"])

with tab_read:
    c1, c2 = st.columns([1, 5])

    with c1:
        page = st.number_input("PDF page", min_value=1, value=1, step=1)

    with c2:
        st.write("")
        st.write("")
        st.caption(
            "Click inside the PDF and use Ctrl+F on Windows or Cmd+F on Mac to search."
        )

    pdf_iframe(book["data"], int(page), height=950)

with tab_help:
    st.markdown("""
### How to use

- Upload one or more PDF textbooks from the sidebar.
- Pick a textbook from the dropdown.
- Enter a PDF page number to jump to that page.
- Use the browser PDF controls for zoom, print, download, and search.
- Use **Ctrl+F** / **Cmd+F** inside the viewer to search text.

### Why this version works better on Streamlit Cloud

This version uses only Streamlit plus your browser's built-in PDF viewer.
It does not require PyMuPDF, fitz, pymupdf, or Pillow.
""")
