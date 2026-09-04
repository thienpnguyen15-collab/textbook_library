
# My Textbook Library

A local textbook reader for PDFs.

## Features
- Import textbook PDFs
- Store PDFs in a local library
- Read directly in the browser
- Extract the PDF bookmark/table-of-contents automatically
- Fallback chapter detection when bookmarks are missing
- Click a chapter to jump to its PDF page
- Search text inside the whole book
- Previous / next page navigation
- Zoom
- Remove books from the library

## Run

1. Install Python 3.10+.
2. Open Terminal / Command Prompt in this folder.
3. Install packages:

```bash
pip install -r requirements.txt
```

4. Start the website:

```bash
streamlit run app.py
```

5. Your browser should open automatically.
6. Click **Import textbook PDF** in the sidebar.

## Notes
This first version uses PDF page numbers. Printed page numbers in the textbook can differ because covers and front matter count as PDF pages.
