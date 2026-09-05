import io
import json
import re
import hashlib
from pathlib import Path

import pymupdf as fitz
import streamlit as st
from PIL import Image

APP_DIR = Path(__file__).parent
BOOKS_DIR = APP_DIR / "books"
DATA_DIR = APP_DIR / "data"
BOOKS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

st.set_page_config(
    page_title="My Textbook Library",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background: #f4f6f8; }
    section[data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e6e8eb;
    }
    .book-title {
        font-size: 30px;
        font-weight: 700;
        line-height: 1.1;
        margin-bottom: 4px;
    }
    .book-subtitle {
        color: #7a7f87;
        font-size: 16px;
        margin-bottom: 20px;
    }
    .toc-header {
        font-weight: 700;
        font-size: 18px;
        margin-top: 8px;
        margin-bottom: 8px;
    }
    .page-badge {
        display: inline-block;
        padding: 5px 10px;
        border-radius: 999px;
        background: #eef1f4;
        font-size: 13px;
        color: #444;
    }
</style>
""", unsafe_allow_html=True)

def safe_name(name: str) -> str:
    stem = Path(name).stem
    stem = re.sub(r'[^A-Za-z0-9._ -]+', '_', stem).strip()
    return stem[:120] or "book"

def book_id_from_bytes(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()[:12]

def meta_path(book_id: str) -> Path:
    return DATA_DIR / f"{book_id}.json"

def save_meta(book_id: str, meta: dict):
    meta_path(book_id).write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

def load_meta(book_id: str) -> dict:
    p = meta_path(book_id)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}

def extract_pdf_metadata(pdf_path: Path) -> dict:
    doc = fitz.open(pdf_path)
    md = doc.metadata or {}
    toc = doc.get_toc(simple=True)
    return {
        "title": (md.get("title") or pdf_path.stem).strip(),
        "author": (md.get("author") or "").strip(),
        "pages": doc.page_count,
        "toc": toc,
    }

def auto_detect_toc(pdf_path: Path, max_scan_pages: int = 50):
    doc = fitz.open(pdf_path)
    results = []
    seen = set()
    patterns = [
        (1, re.compile(r'^\s*(chapter|ch\.)\s+(\d+|[ivxlcdm]+)\b[:.\-\s]*(.+)?$', re.I)),
        (2, re.compile(r'^\s*(\d+)\.(\d+)\s+(.+)$')),
        (2, re.compile(r'^\s*(appendix)\s+([A-Z])\b[:.\-\s]*(.+)?$', re.I)),
        (1, re.compile(r'^\s*(\d+)\s+[A-Z][A-Z0-9 ,\-–—:&()]+$')),
    ]

    for pno in range(min(doc.page_count, max_scan_pages)):
        text = doc[pno].get_text("text")
        for raw in text.splitlines():
            line = " ".join(raw.split()).strip()
            if not (3 <= len(line) <= 140):
                continue
            for level, pat in patterns:
                if pat.match(line):
                    key = line.lower()
                    if key not in seen:
                        seen.add(key)
                        results.append([level, line, pno + 1])
                    break
    return results[:150]

def list_books():
    books = []
    for p in sorted(BOOKS_DIR.glob("*.pdf")):
        book_id = p.stem.split("__", 1)[0]
        meta = load_meta(book_id)
        if not meta:
            meta = extract_pdf_metadata(p)
            if not meta.get("toc"):
                meta["toc"] = auto_detect_toc(p)
                meta["toc_source"] = "auto-detected"
            else:
                meta["toc_source"] = "pdf-bookmarks"
            meta["file"] = p.name
            save_meta(book_id, meta)
        books.append((book_id, p, meta))
    return books

def import_pdf(uploaded):
    data = uploaded.getvalue()
    book_id = book_id_from_bytes(data)
    existing = list(BOOKS_DIR.glob(f"{book_id}__*.pdf"))
    if existing:
        return book_id, existing[0], load_meta(book_id), False

    filename = safe_name(uploaded.name) + ".pdf"
    target = BOOKS_DIR / f"{book_id}__{filename}"
    target.write_bytes(data)

    meta = extract_pdf_metadata(target)
    if not meta["toc"]:
        meta["toc"] = auto_detect_toc(target)
        meta["toc_source"] = "auto-detected"
    else:
        meta["toc_source"] = "pdf-bookmarks"

    meta["file"] = target.name
    save_meta(book_id, meta)
    return book_id, target, meta, True

def render_page(doc, page_index: int, zoom=1.5):
    page = doc.load_page(page_index)
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    return Image.open(io.BytesIO(pix.tobytes("png")))

def search_pdf(doc, query: str, max_results=50):
    results = []
    q = query.strip().lower()
    if not q:
        return results
    for i in range(doc.page_count):
        text = doc[i].get_text("text")
        idx = text.lower().find(q)
        if idx >= 0:
            start = max(0, idx - 80)
            end = min(len(text), idx + len(q) + 140)
            snippet = " ".join(text[start:end].split())
            results.append((i + 1, snippet))
            if len(results) >= max_results:
                break
    return results

with st.sidebar:
    st.markdown("## 📚 My Library")

    uploaded = st.file_uploader("Import textbook PDF", type=["pdf"], accept_multiple_files=False)

    if uploaded is not None:
        try:
            bid, path, meta, created = import_pdf(uploaded)
            st.session_state["selected_book"] = bid
            if created:
                st.success("PDF imported.")
            else:
                st.info("This PDF is already in your library.")
        except Exception as e:
            st.error(f"Could not import PDF: {e}")

    books = list_books()

    if not books:
        st.caption("Import your first textbook PDF to start.")
        st.stop()

    ids = [b[0] for b in books]
    labels = [(b[2].get("title") or b[1].stem) for b in books]

    current = st.session_state.get("selected_book", ids[0])
    if current not in ids:
        current = ids[0]

    chosen_title = st.selectbox(
        "Textbook",
        labels,
        index=ids.index(current),
        label_visibility="collapsed"
    )

    selected_index = labels.index(chosen_title)
    book_id, pdf_path, meta = books[selected_index]
    st.session_state["selected_book"] = book_id

    st.divider()
    st.markdown(f"**{meta.get('title', pdf_path.stem)}**")
    if meta.get("author"):
        st.caption(meta["author"])
    st.caption(f"{meta.get('pages', '?')} pages")

    if st.button("🗑️ Remove from library", use_container_width=True):
        pdf_path.unlink(missing_ok=True)
        meta_path(book_id).unlink(missing_ok=True)
        st.session_state.pop("selected_book", None)
        st.rerun()

doc = fitz.open(pdf_path)

page_key = f"page_{book_id}"
if page_key not in st.session_state:
    st.session_state[page_key] = 1

top1, top2 = st.columns([5, 2])

with top1:
    st.markdown(
        f'<div class="book-title">{meta.get("title", pdf_path.stem)}</div>',
        unsafe_allow_html=True
    )
    subtitle = meta.get("author") or "PDF Textbook"
    st.markdown(
        f'<div class="book-subtitle">{subtitle}</div>',
        unsafe_allow_html=True
    )

with top2:
    st.markdown(
        f'<span class="page-badge">Page {st.session_state[page_key]} / {doc.page_count}</span>',
        unsafe_allow_html=True
    )

tab_read, tab_search, tab_info = st.tabs(["📖 Read", "🔎 Search", "⚙️ Book info"])

with tab_read:
    left, center = st.columns([1.45, 3.55], gap="large")

    with left:
        st.markdown('<div class="toc-header">Table of Contents</div>', unsafe_allow_html=True)

        toc = meta.get("toc") or []
        if toc:
            for idx, item in enumerate(toc):
                try:
                    level, title, page = item[:3]
                    level = max(1, int(level))
                    page = int(page)

                    prefix = "▾" if level == 1 else "•"
                    indent = "　" * min(level - 1, 4)
                    label = f"{indent}{prefix} {title}  ·  {page}"

                    if st.button(label, key=f"toc_{book_id}_{idx}", use_container_width=True):
                        st.session_state[page_key] = max(1, min(page, doc.page_count))
                        st.rerun()
                except Exception:
                    pass
        else:
            st.info("No table of contents detected.")

        st.divider()

        page_jump = st.number_input(
            "Jump to PDF page",
            min_value=1,
            max_value=doc.page_count,
            value=int(st.session_state[page_key]),
            step=1
        )

        if st.button("Go", use_container_width=True):
            st.session_state[page_key] = int(page_jump)
            st.rerun()

    with center:
        b1, b2, b3 = st.columns([1, 1, 5])

        with b1:
            if st.button("← Prev", use_container_width=True, disabled=st.session_state[page_key] <= 1):
                st.session_state[page_key] -= 1
                st.rerun()

        with b2:
            if st.button("Next →", use_container_width=True, disabled=st.session_state[page_key] >= doc.page_count):
                st.session_state[page_key] += 1
                st.rerun()

        with b3:
            zoom = st.slider("Zoom", 1.0, 2.4, 1.5, 0.1, label_visibility="collapsed")

        page_num = int(st.session_state[page_key])
        img = render_page(doc, page_num - 1, zoom=zoom)
        st.image(img, use_container_width=True)

with tab_search:
    q = st.text_input(
        "Search inside textbook",
        placeholder="Example: live load, Atterberg limits, moment distribution..."
    )

    if q:
        with st.spinner("Searching textbook..."):
            results = search_pdf(doc, q)

        st.caption(f"{len(results)} result(s)")

        for result_index, (page, snippet) in enumerate(results):
            c1, c2 = st.columns([1, 8])

            with c1:
                if st.button(f"Page {page}", key=f"search_{book_id}_{page}_{result_index}"):
                    st.session_state[page_key] = page
                    st.rerun()

            with c2:
                st.write(snippet)

with tab_info:
    st.write("**Title:**", meta.get("title") or "—")
    st.write("**Author:**", meta.get("author") or "—")
    st.write("**Pages:**", doc.page_count)
    st.write("**TOC source:**", meta.get("toc_source", "unknown"))
    st.caption(
        "Navigation currently uses PDF page numbers. Printed page numbers may differ because "
        "covers, prefaces, and front matter also count as PDF pages."
    )
