# src/frontend/app.py
'''Streamlit frontend for iiRDS RAG Agent.'''
import os
import requests
import streamlit as st

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8001")

st.set_page_config(page_title="TechDoc RAG Agent", page_icon="📦", layout="wide")
st.title("TechDoc RAG Agent")

# ---------- Sidebar: Ingestion ----------
st.sidebar.header("Ingest iiRDS package")
zip_file = st.sidebar.file_uploader("Upload .zip (iiRDS)", type=["zip", "iirds"], accept_multiple_files=False)

if st.sidebar.button("Ingest", type="primary", disabled=(zip_file is None)):
    if zip_file is None:
        st.sidebar.warning("Choose a file first.")
    else:
        with st.spinner("Ingesting…"):
            files = {"file": (zip_file.name, zip_file.getvalue(), "application/zip")}
            try:
                r = requests.post(f"{BACKEND}/ingest", files=files, timeout=120)
                r.raise_for_status()
                st.sidebar.success(f"Ingested: {r.json()}")
            except Exception as e:
                st.sidebar.error(f"Ingestion failed: {e}")
show_debug = st.sidebar.checkbox("Show retrieval debug", value=False)



st.sidebar.markdown("---")

# ---------- Sidebar: Filters ----------
variant = st.sidebar.text_input("Filter: product variant (IRI or code)", value="")
st.sidebar.caption("Leave empty for no filter.")

st.sidebar.markdown("---")

# ---------- Sidebar: Model selection ----------
st.sidebar.subheader("Model selection")
use_remote = st.sidebar.checkbox("Use remote (OpenRouter)", value=False)
mode = "remote" if use_remote else "local"
model_override = st.sidebar.text_input("Model override (optional)", value="")
temperature = st.sidebar.slider("Temperature", min_value=0.0, max_value=1.0, value=0.2, step=0.05)

# ---------- Chat state ----------
if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

prompt = st.chat_input("Ask a question about your technical docs…")

def ask_backend(question: str, variant_filter: str = "", mode: str = "local",
                model_override: str = "", temperature: float = 0.2):
    payload = {
        "question": question,
        "filters": {},
        "mode": mode,                 # <-- important: tells backend local vs remote
        "temperature": temperature,
        "debug": show_debug, 
    }
    if model_override.strip():
        payload["model"] = model_override.strip()
    if variant_filter.strip():
        payload["filters"]["product_variants"] = variant_filter.strip()

    r = requests.post(f"{BACKEND}/query", json=payload, timeout=1200)
    r.raise_for_status()
    return r.json()

if prompt:
    # user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # assistant reply
    with st.chat_message("assistant"):
        placeholder = st.empty()
        try:
            resp = ask_backend(
                question=prompt,
                variant_filter=variant,
                mode=mode,
                model_override=model_override,
                temperature=temperature,
            )
            answer = resp.get("answer", "")
            placeholder.markdown(answer)

            # metadata + citations
            meta_bits = []
            if resp.get("used_mode"):
                meta_bits.append(f"**Mode:** {resp['used_mode']}")
            if resp.get("used_model"):
                meta_bits.append(f"**Model:** `{resp['used_model']}`")
            if meta_bits:
                st.caption(" · ".join(meta_bits))

            cits = resp.get("citations", [])
            if cits:
                with st.expander("Citations"):
                    for c in cits:
                        st.markdown(f"- `{c.get('parent_iri','')}` · `{c.get('path','')}`")
            
            # debugging info
            if resp.get("debug"):
                with st.expander("Retrieval debug"):
                    st.json(resp["debug"])
        
        except Exception as e:
            placeholder.error(f"Query failed: {e}")
            answer = f"_Error: {e}_"

    st.session_state.messages.append({"role": "assistant", "content": answer})
