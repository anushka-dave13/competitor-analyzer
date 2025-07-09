import sys
import os

# Ensure the root project directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
from extractor.crawl.core import crawl_website
from analyzer.analyze import analyze_text

import pandas as pd
import re
import tempfile
import os

def is_valid_url(url):
    # Simple regex for URL validation
    pattern = re.compile(
        r'^(https?://)'  # http:// or https://
        r'(([A-Za-z0-9-]+\.)+[A-Za-z]{2,6})'  # domain
        r'(:\d+)?'  # optional port
        r'(/.*)?$'  # optional path
    )
    return bool(pattern.match(url.strip()))

def sanitize_filename(filename):
    # Remove problematic characters for most OS
    return re.sub(r'[^A-Za-z0-9_.-]', '_', filename)

# Optional: Log errors to a temp file for debugging
def log_error(msg):
    with tempfile.NamedTemporaryFile(delete=False, mode='a', suffix='.log', prefix='streamlit_app_', dir=tempfile.gettempdir()) as f:
        f.write(msg + '\n')

st.set_page_config(page_title="Competitor Analyzer", layout="wide")
st.title("Competitor Analysis Tool")

# --- Sidebar ---
st.sidebar.header("Navigation")
section = st.sidebar.radio("Choose Section:", ["Extractor", "Analyzer","Config Editor"])

# --- Extraction Section ---
if section == "Extractor":
    st.subheader(" Website Text Extractor")

    url = st.text_input("Enter website URL:")
    if st.button("Extract Text"):
        if not url or not is_valid_url(url):
            st.warning(" Please enter a valid URL (starting with http:// or https://).")
        else:
            with st.spinner("Extracting content..."):
                try:
                    results = crawl_website(url, max_pages=20, save_text=False, show_progress=False)
                    extracted_text = "\n\n".join(results.values()) if results else ""

                    if extracted_text and extracted_text.strip():
                        filename = sanitize_filename(url.replace('https://', '').replace('http://', '').replace('/', '_')) + ".txt"
                        st.success(f" Extraction complete. Filename: `{filename}`")
                        st.download_button("Download Extracted Text", data=extracted_text, file_name=filename)
                    else:
                        st.error(" Extraction returned no text. The website may be protected, empty, or not supported.")
                except Exception as e:
                    log_error(f"[Extractor] URL: {url} | Error: {str(e)}")
                    st.error(f" Failed to extract text from the URL. Error: {e}")

# --- Analyzer Section ---
elif section == "Analyzer":
    st.subheader(" Content Analyzer")

    uploaded_file = st.file_uploader("Upload a .txt file for analysis", type=["txt"])

    if uploaded_file:
        try:
            # Check file size (Streamlit default is 200MB, but you can set a lower limit)
            uploaded_file.seek(0, os.SEEK_END)
            file_size = uploaded_file.tell()
            uploaded_file.seek(0)
            if file_size > 5 * 1024 * 1024:  # 5 MB limit for safety
                st.error(" File too large. Please upload a text file smaller than 5MB.")
            else:
                # Try to decode as UTF-8, fallback to latin-1 if needed
                try:
                    text = uploaded_file.read().decode("utf-8")
                except UnicodeDecodeError:
                    uploaded_file.seek(0)
                    try:
                        text = uploaded_file.read().decode("latin-1")
                        st.info("File decoded with latin-1 encoding.")
                    except Exception:
                        st.error(" Unable to decode file. Please upload a valid UTF-8 or latin-1 encoded text file.")
                        text = None

                if text:
                    base_url = sanitize_filename(uploaded_file.name.replace(".txt", ""))
                    with st.spinner("Analyzing..."):
                        try:
                            results = analyze_text(base_url, text)
                        except Exception as e:
                            log_error(f"[Analyzer] File: {uploaded_file.name} | Error: {str(e)}")
                            st.error(f" Analysis failed due to an internal error: {e}")
                            results = None

                    if results and isinstance(results, dict) and any(results.values()):
                        st.success(" Analysis complete.")
                        try:
                            df = pd.DataFrame([results])
                            st.dataframe(df)

                            # Excel-style export
                            csv = df.to_csv(index=False).encode("utf-8")
                            st.download_button("Download Results as CSV", data=csv, file_name="analysis_result.csv")
                        except Exception as e:
                            log_error(f"[Analyzer] DataFrame/Export error: {str(e)}")
                            st.error(" Error displaying or exporting results.")
                    else:
                        st.error(" Analysis returned no results. Please check the uploaded file content.")
        except Exception as e:
            log_error(f"[Analyzer] File upload error: {str(e)}")
            st.error(" Unexpected error during file upload or analysis.")
elif section == "Config Editor":
    import pandas as pd
    from analyzer.utils.config_utils import load_config, save_config

    st.subheader("Keyword Buckets and Scoring Configuration")

    config = load_config()
    buckets = {k: v for k, v in config.items() if not k.startswith("_")}

    # --- Convert config to editable DataFrame ---
    table_data = []
    for bucket, info in buckets.items():
        table_data.append({
            "Bucket": bucket,
            "Keywords": ", ".join(info.get("keywords", [])),
            "Weight": info.get("weight", 1.0),
            "Include": "+"  # default sign
        })

    df = pd.DataFrame(table_data)

    # --- Display editable table ---
    edited_df = st.data_editor(
        df,
        column_config={
            "Include": st.column_config.SelectboxColumn("Include", options=["+", "-", "Exclude"]),
        },
        num_rows="dynamic",
        use_container_width=True
    )

    st.markdown("### Scoring Formula")

    # --- Auto-generate formula from included buckets ---
    formula_parts = [
        f"{row['Include']}{{{row['Bucket']}}}"
        for _, row in edited_df.iterrows()
        if row["Include"] in ["+", "-"]
    ]
    auto_formula = " ".join(formula_parts)

    formula_input = st.text_input("Edit formula manually if needed", value=auto_formula)

    # --- Custom Variables ---
    st.markdown("### Custom Variables")
    custom_vars = config.get("_custom_variables", {})
    updated_vars = {}

    for var, val in custom_vars.items():
        updated_vars[var] = st.number_input(f"{var}", value=val, step=0.1)

    new_var_name = st.text_input("New Variable Name")
    new_var_val = st.number_input("New Variable Value", step=0.1)
    if new_var_name:
        updated_vars[new_var_name] = new_var_val

    # --- Save Everything ---
    if st.button("Save Configuration"):
        new_config = {}

        for _, row in edited_df.iterrows():
            bucket = row["Bucket"]
            keywords = [k.strip() for k in row["Keywords"].split(",") if k.strip()]
            weight = row["Weight"]
            new_config[bucket] = {
                "keywords": keywords,
                "weight": weight
            }

        new_config["_formula"] = formula_input
        new_config["_custom_variables"] = updated_vars

        save_config(new_config)
        st.success("Configuration saved successfully.")

st.markdown("---")
st.caption("Robust Streamlit Competitor Analyzer © 2025")
