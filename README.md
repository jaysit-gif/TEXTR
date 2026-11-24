# Textbook Navigator

A Streamlit app for navigating PDF textbooks with better structure than a raw PDF reader.

## Features

- Upload any textbook PDF
- Automatic Table of Contents extraction (with fallback chapter detection)
- Page navigation + prev/next
- Dual view: clean text extraction or rendered page image
- Full-text search with jump-to-page
- **On-demand hints** for detected problems (rule-based guidance, never solutions)
- Per-page notes (session-based)
- Progress tracking
- Basic concept extraction and backlink suggestions (pages sharing key terms)

## Run

```bash
pip install pymupdf streamlit pillow
streamlit run textbook_navigator.py
```

## Possible Extensions

- Knowledge graph visualization (networkx + pyvis)
- Better structure parsing (section hierarchy)
- Persistent notes (save to JSON)
- LLM integration for smarter prerequisite detection and contextual hints
- Formula extraction and rendering
- Highlighting / annotation overlay
- Multi-book linking
