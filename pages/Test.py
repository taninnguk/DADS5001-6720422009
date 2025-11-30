from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
from ollama import chat

try:
    from pypdf import PdfReader
except Exception:  # keeps UI working if dependency missing
    PdfReader = None

st.title("Multi-Modal Input Inspector")


def load_dataframe(raw_bytes: bytes, name: str, mime: str):
    """Convert structured uploads into a DataFrame when possible."""
    ext = Path(name or "").suffix.lower()

    try:
        if ext in {".csv"} or mime == "text/csv":
            return pd.read_csv(BytesIO(raw_bytes))
        if ext == ".tsv":
            return pd.read_csv(BytesIO(raw_bytes), sep="\t")
        if ext in {".xlsx", ".xls"} or mime in {
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }:
            return pd.read_excel(BytesIO(raw_bytes))
        if ext == ".json" or mime == "application/json":
            return pd.read_json(BytesIO(raw_bytes))
    except Exception as exc:  # keep UI friendly on malformed files
        st.error(f"Could not read structured data: {exc}")

    return None


def extract_pdf_text(raw_bytes: bytes):
    """Extract text from a PDF if pypdf is available."""
    if PdfReader is None:
        st.error("PDF support is unavailable (pypdf not installed).")
        return ""
    try:
        reader = PdfReader(BytesIO(raw_bytes))
        chunks = []
        for page in reader.pages:
            text = page.extract_text() or ""
            if text:
                chunks.append(text)
        extracted = "\n\n".join(chunks).strip()
        return extracted
    except Exception as exc:
        st.error(f"Could not read PDF: {exc}")
        return ""


text_input = st.text_area("Optional text input", height=120, placeholder="Paste or type text...")
uploaded = st.file_uploader("Upload any file", type=None)

file_text = ""
df = None
image_bytes = None

if uploaded is not None:
    raw_bytes = uploaded.getvalue()
    mime_type = uploaded.type or ""
    name = uploaded.name or "uploaded file"
    ext = Path(name).suffix.lower()

    is_image = mime_type.startswith("image/")
    is_text = mime_type.startswith("text/") or ext in {".txt", ".md", ".log"}
    is_pdf = ext == ".pdf" or mime_type == "application/pdf"

    st.caption(f"{name} · {mime_type or 'unknown type'} · {len(raw_bytes):,} bytes")

    if is_image:
        image_bytes = raw_bytes
        st.image(image_bytes, caption=name, use_container_width=True)
    else:
        df = load_dataframe(raw_bytes, name, mime_type)
        if df is not None:
            st.subheader("Detected Data Table")
            st.dataframe(df, use_container_width=True, height=300)
        elif is_pdf:
            file_text = extract_pdf_text(raw_bytes)
            if file_text:
                if len(file_text) > 5000:
                    st.info("Preview truncated to first 5,000 characters.")
                    file_text = file_text[:5000]
                st.subheader("Detected PDF Text")
                st.text_area("PDF contents", file_text, height=200)
        elif is_text:
            try:
                file_text = raw_bytes.decode("utf-8")
            except Exception:
                file_text = raw_bytes.decode(errors="replace")
            if len(file_text) > 5000:
                st.info("Preview truncated to first 5,000 characters.")
                file_text = file_text[:5000]
            st.subheader("Detected Text")
            st.text_area("File contents", file_text, height=200)
        else:
            st.info("File uploaded but not recognized as image, text, or structured data.")

# Combine text from manual input and file text
combined_text = "\n\n".join([part for part in [file_text.strip(), text_input.strip()] if part]).strip()

# Prepare AI analysis input based on what is available
table_preview = None
if df is not None:
    preview_rows = min(len(df), 50)
    table_preview = df.head(preview_rows).to_markdown(index=False)

analyze_ready = image_bytes is not None or table_preview is not None or bool(combined_text)

if st.button("Analyze", disabled=not analyze_ready):
    with st.spinner("Analyzing..."):
        try:
            prompt_parts = []
            if image_bytes is not None:
                prompt_parts.append("Analyze the attached image and describe it concisely.")
            if table_preview is not None:
                prompt_parts.append(
                    f"Here is tabular data (showing up to {preview_rows} rows). "
                    f"Summarize key columns and notable values.\n\n{table_preview}"
                )
            if combined_text:
                prompt_parts.append(f"Also consider this text:\n\n{combined_text}")

            message = {
                "role": "user",
                "content": "\n\n".join(prompt_parts),
            }
            if image_bytes is not None:
                message["images"] = [image_bytes]

            response = chat(model="gemma3", messages=[message])
            st.subheader("Analysis Result")
            st.write(response.message.content)
        except Exception as e:
            st.error(f"Error: {e}")
elif not analyze_ready:
    st.info("Upload an image, structured data, or text to enable analysis.")
