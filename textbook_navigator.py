import streamlit as st
import pymupdf  # PyMuPDF
import re
from io import BytesIO
from PIL import Image
import json
from pathlib import Path

st.set_page_config(
    page_title="Textbook Navigator",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📚 Textbook Navigator")
st.caption("Navigate textbooks with chapters, prerequisites, and on-demand hints (no solutions)")

# Session state
if "pdf_doc" not in st.session_state:
    st.session_state.pdf_doc = None
if "toc" not in st.session_state:
    st.session_state.toc = []
if "current_page" not in st.session_state:
    st.session_state.current_page = 0
if "notes" not in st.session_state:
    st.session_state.notes = {}
if "progress" not in st.session_state:
    st.session_state.progress = set()
if "concepts" not in st.session_state:
    st.session_state.concepts = {}

uploaded_file = st.sidebar.file_uploader("Upload Textbook PDF", type=["pdf"])

def extract_toc(doc):
    """Extract table of contents from PDF"""
    toc = doc.get_toc()
    if toc:
        return toc
    # Fallback: try to detect chapters from text
    chapters = []
    for page_num in range(min(50, doc.page_count)):  # Check first 50 pages
        page = doc.load_page(page_num)
        text = page.get_text()
        # Simple chapter detection
        matches = re.findall(r'^(Chapter\s+\d+|CHAPTER\s+\d+|[0-9]+\.[0-9]+\s+[A-Z].{5,50})', text, re.MULTILINE | re.IGNORECASE)
        for m in matches[:3]:
            chapters.append([1, m.strip(), page_num + 1])
    return chapters

def get_page_text(doc, page_num):
    if page_num < 0 or page_num >= doc.page_count:
        return ""
    page = doc.load_page(page_num)
    return page.get_text()

def render_page_image(doc, page_num, zoom=1.5):
    page = doc.load_page(page_num)
    mat = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat)
    img_data = pix.tobytes("png")
    return Image.open(BytesIO(img_data))

def extract_problems(text):
    """Find problem/exercise sections"""
    problems = []
    # Patterns for problems
    patterns = [
        r'(?:Problem|Exercise|Question)\s*(\d+(?:\.\d+)?)\s*[:\.]?\s*(.{20,500})',
        r'(\d+(?:\.\d+)?)\s*\.\s*(.{30,400}?)(?:\n\n|\Z)',
    ]
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
        for m in matches:
            problems.append({
                "id": m.group(1) if len(m.groups()) > 1 else "?",
                "text": m.group(2 if len(m.groups()) > 1 else 1).strip()[:800]
            })
    return problems[:20]  # Limit

def generate_hint(problem_text):
    """Generate a hint without giving the solution"""
    # Rule-based hints that guide thinking
    hints = []
    
    # Check for common problem types
    text_lower = problem_text.lower()
    
    if any(w in text_lower for w in ["prove", "show that", "demonstrate"]):
        hints.append("💡 Start by identifying what is given and what needs to be shown. What definitions or theorems apply here?")
    if any(w in text_lower for w in ["find", "calculate", "compute", "determine"]):
        hints.append("💡 What formula or relationship connects the given quantities to what you need to find?")
    if any(w in text_lower for w in ["derive", "obtain"]):
        hints.append("💡 Begin from first principles or the relevant governing equation. What assumptions can you make?")
    if "graph" in text_lower or "plot" in text_lower:
        hints.append("💡 Identify the key features: intercepts, asymptotes, critical points. What does the derivative tell you?")
    if any(w in text_lower for w in ["optimize", "maximum", "minimum"]):
        hints.append("💡 Consider the derivative and critical points. What constraints exist?")
    
    # General hints
    if not hints:
        hints.append("💡 Break the problem into smaller parts. What is the first step you would take?")
        hints.append("💡 What relevant concepts or theorems from earlier sections apply here?")
    
    hints.append("⚠️ This is only a hint — work through the reasoning yourself. No solution is provided.")
    return "\n\n".join(hints)

def find_related_concepts(text, all_sections):
    """Simple concept linking based on keywords"""
    # Extract potential concept keywords (capitalized phrases, math terms)
    words = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
    keywords = list(set(words))[:10]
    return keywords

if uploaded_file is not None:
    # Load PDF
    pdf_bytes = uploaded_file.read()
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    st.session_state.pdf_doc = doc
    
    if not st.session_state.toc:
        st.session_state.toc = extract_toc(doc)
    
    # Sidebar navigation
    st.sidebar.header("Navigation")
    st.sidebar.metric("Total Pages", doc.page_count)
    
    # TOC display
    if st.session_state.toc:
        st.sidebar.subheader("Table of Contents")
        for item in st.session_state.toc[:50]:  # Limit display
            level, title, page = item[0], item[1], item[2]
            indent = "　" * (level - 1)
            if st.sidebar.button(f"{indent}{title}", key=f"toc_{page}_{title[:20]}"):
                st.session_state.current_page = max(0, page - 1)
    
    # Page selector
    page_input = st.sidebar.number_input(
        "Go to page",
        min_value=1,
        max_value=doc.page_count,
        value=st.session_state.current_page + 1,
        step=1
    )
    st.session_state.current_page = page_input - 1
    
    # Progress
    if st.sidebar.button("Mark current as read"):
        st.session_state.progress.add(st.session_state.current_page)
    st.sidebar.caption(f"Progress: {len(st.session_state.progress)} pages marked")
    
    # Main content
    col1, col2 = st.columns([3, 1])
    
    with col1:
        tab1, tab2, tab3, tab4 = st.tabs(["📖 Read", "🔍 Search", "💡 Hints", "📝 Notes"])
        
        with tab1:
            st.subheader(f"Page {st.session_state.current_page + 1}")
            
            # Toggle between text and image
            view_mode = st.radio("View mode", ["Text", "Page Image"], horizontal=True)
            
            if view_mode == "Text":
                text = get_page_text(doc, st.session_state.current_page)
                st.text_area("Content", text, height=500, label_visibility="collapsed")
            else:
                try:
                    img = render_page_image(doc, st.session_state.current_page)
                    st.image(img, use_container_width=True)
                except Exception as e:
                    st.error(f"Could not render page: {e}")
                    st.text(get_page_text(doc, st.session_state.current_page))
            
            # Prev/Next
            c1, c2, c3 = st.columns(3)
            if c1.button("← Previous") and st.session_state.current_page > 0:
                st.session_state.current_page -= 1
                st.rerun()
            c2.write(f"**{st.session_state.current_page + 1}** / {doc.page_count}")
            if c3.button("Next →") and st.session_state.current_page < doc.page_count - 1:
                st.session_state.current_page += 1
                st.rerun()
        
        with tab2:
            query = st.text_input("Search in textbook")
            if query:
                results = []
                for p in range(doc.page_count):
                    text = get_page_text(doc, p)
                    if query.lower() in text.lower():
                        # Get snippet
                        idx = text.lower().find(query.lower())
                        snippet = text[max(0, idx-100):idx+200]
                        results.append((p + 1, snippet))
                        if len(results) >= 15:
                            break
                for page, snippet in results:
                    if st.button(f"Page {page}: ...{snippet}...", key=f"search_{page}"):
                        st.session_state.current_page = page - 1
                        st.rerun()
        
        with tab3:
            st.subheader("On-Demand Hints")
            st.info("Hints guide your thinking. Solutions are never provided.")
            
            current_text = get_page_text(doc, st.session_state.current_page)
            problems = extract_problems(current_text)
            
            if problems:
                for i, prob in enumerate(problems):
                    with st.expander(f"Problem {prob['id']}"):
                        st.write(prob['text'][:600] + ("..." if len(prob['text']) > 600 else ""))
                        if st.button(f"Get Hint", key=f"hint_{i}_{st.session_state.current_page}"):
                            hint = generate_hint(prob['text'])
                            st.success(hint)
            else:
                st.write("No clear problems detected on this page. Try searching for 'Exercise' or 'Problem'.")
                # Manual hint
                custom = st.text_area("Or paste a problem for a hint:")
                if custom and st.button("Generate Hint"):
                    st.success(generate_hint(custom))
        
        with tab4:
            st.subheader("Notes for this page")
            page_key = str(st.session_state.current_page)
            note = st.text_area("Your notes", value=st.session_state.notes.get(page_key, ""), height=200)
            if st.button("Save Notes"):
                st.session_state.notes[page_key] = note
                st.success("Notes saved")
            
            # Show all notes
            if st.session_state.notes:
                st.divider()
                st.write("**All notes:**")
                for p, n in sorted(st.session_state.notes.items(), key=lambda x: int(x[0])):
                    if n:
                        st.write(f"**Page {int(p)+1}:** {n[:100]}...")
    
    with col2:
        st.subheader("Prerequisites & Links")
        
        # Simple concept extraction
        current_text = get_page_text(doc, st.session_state.current_page)
        concepts = find_related_concepts(current_text, st.session_state.toc)
        
        if concepts:
            st.write("**Key concepts on this page:**")
            for c in concepts[:8]:
                st.write(f"• {c}")
        
        st.divider()
        st.write("**Backlinks / Related**")
        st.caption("Sections that mention similar topics (basic matching)")
        
        # Find pages that share keywords
        if concepts:
            related = []
            for p in range(max(0, st.session_state.current_page - 30), st.session_state.current_page):
                text = get_page_text(doc, p)
                shared = sum(1 for c in concepts if c.lower() in text.lower())
                if shared >= 2:
                    related.append((p + 1, shared))
            related.sort(key=lambda x: -x[1])
            for page, score in related[:5]:
                if st.button(f"Page {page} ({score} shared)", key=f"rel_{page}"):
                    st.session_state.current_page = page - 1
                    st.rerun()
        
        st.divider()
        st.write("**Suggested additions:**")
        st.markdown("""
        - Concept graph visualization
        - Spaced repetition for definitions
        - Formula extractor + KaTeX
        - Cross-book linking
        - AI-powered prerequisite detection
        """)

else:
    st.info("👈 Upload a textbook PDF to begin navigating")
    st.markdown("""
    ### Features
    - **Chapter navigation** via extracted Table of Contents
    - **Page-by-page reading** (text or rendered image)
    - **Full-text search**
    - **On-demand hints** for problems (never solutions)
    - **Notes** per page
    - **Prerequisite / backlink suggestions** based on concept matching
    - Progress tracking
    
    ### Ideas for enhancement
    - Knowledge graph of concepts
    - Better section parsing
    - Integration with LLM for smarter hints and prerequisite detection
    - Annotation highlighting
    """)

# Footer
st.sidebar.divider()
st.sidebar.caption("Hints only — no solutions provided")
