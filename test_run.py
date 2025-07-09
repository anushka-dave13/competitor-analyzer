# test_run.py
import os
from extractor.crawl.core import crawl_website
from analyzer.analyze import analyze_text

# === PARAMETERS ===
url = "https://www.kpoint.com"  # Replace with a real URL
output_folder = "test_output"

# === Step 1: Crawl the Website ===
print("\n[STEP 1] Crawling website...\n")
extracted = crawl_website(
    base_url=url,
    output_dir=output_folder,
    max_pages=5,
    save_text=True,
    show_progress=True,
    save_screenshot_on_fail=True
)

# Save merged text for analysis
merged_text = "\n\n".join(extracted.values())
text_path = os.path.join(output_folder, "merged.txt")
os.makedirs(output_folder, exist_ok=True)
with open(text_path, "w", encoding="utf-8") as f:
    f.write(merged_text)
print(f"\n[SAVED] Merged text saved at: {text_path}\n")

# === Step 2: Analyze Extracted Text ===
print("\n[STEP 2] Running analysis...\n")
analysis_result = analyze_text(identifier=url, text=merged_text)

print("=== ANALYSIS RESULT ===")
for key, val in analysis_result.items():
    print(f"{key}: {val}")
