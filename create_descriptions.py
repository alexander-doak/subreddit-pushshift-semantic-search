# create_descriptions.py

import pandas as pd
import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

# --- CONFIGURATION -----------------------------------------------------------
NUM_THREADS = 8
MAX_RETRIES = 3
BATCH_SIZE = 100
MODEL_NAME = "gpt-5.4-mini-2026-03-17"
MAX_TOKENS = 350

INPUT_PATH = r"F:\Emtherical\data\reddit\vector_search\subreddit_recon.csv"
OUTPUT_PATH = r"F:\Emtherical\data\reddit\vector_search\subreddit_descriptions.xlsx"

API_KEY = os.getenv("OPENAI_API_KEY", "")

SIGNAL_COLUMNS = [
    "signal_banned",
    "signal_private",
    "signal_quarantined",
    "signal_over18",
    "signal_not_found",
]

# --- CLIENT -------------------------------------------------------------------
client = OpenAI(api_key=API_KEY)


def build_prompt(subreddit_name: str, final_url: str) -> str:
    fixed_final_url = final_url.replace("https://old.", "https://www.")
    return (
        f"There is a subreddit named '{subreddit_name}' at {fixed_final_url}. "
        f"Based on what you already know, your task is to give a brief, 2-3 sentence "
        f"description of what this subreddit is all about, and the kinds of posts the "
        f"moderators allow or encourage. (Your description is going to be read by someone "
        f"who has never been to the subreddit before, and has no idea about any of the "
        f"specifics of the community so don't assume any prior knowledge about specifics.) "
        f"What is the subreddit '{subreddit_name}' all about (as though you're talking to "
        f"a 5 year old)?"
    )


def call_openai(subreddit_name: str, final_url: str) -> tuple:
    """Returns (response_code, description). Retries up to MAX_RETRIES times."""
    prompt = build_prompt(subreddit_name, final_url)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                max_completion_tokens=MAX_TOKENS,
                store=False,
                messages=[{"role": "user", "content": prompt}],
            )
            description = response.choices[0].message.content.strip()
            return (200, description)

        except Exception as e:
            status = getattr(e, "status_code", None) or 999
            print(
                f"  [attempt {attempt}/{MAX_RETRIES}] Error for r/{subreddit_name}: "
                f"{type(e).__name__}: {e}"
            )
            if attempt < MAX_RETRIES:
                time.sleep(2 * attempt)
            else:
                return (status, f"ERROR after {MAX_RETRIES} attempts: {e}")


def should_skip(row: pd.Series) -> bool:
    """Returns True if ANY signal column is True (meaning we should skip)."""
    for col in SIGNAL_COLUMNS:
        val = row.get(col)
        if val is True or str(val).strip().upper() == "TRUE":
            return True
    return False


def load_existing_output() -> dict:
    """Load the output XLSX if it exists. Returns a dict keyed by subreddit_name."""
    if not os.path.exists(OUTPUT_PATH):
        return {}
    try:
        df = pd.read_excel(OUTPUT_PATH, dtype=str)
        required = {"subreddit_name", "response_code", "description"}
        if not required.issubset(df.columns):
            print(f"Warning: output file missing columns {required - set(df.columns)}, starting fresh.")
            return {}

        lookup = {}
        for _, row in df.iterrows():
            name = str(row["subreddit_name"]).strip()
            rc = str(row["response_code"]).strip()
            desc = str(row["description"]).strip()
            if name and rc not in ("", "nan"):
                lookup[name] = {"response_code": rc, "description": desc}
        return lookup

    except Exception as e:
        print(f"Warning: could not read existing output file, starting fresh. ({e})")
        return {}


def save_output(results: list):
    """Write the results list to XLSX."""
    df = pd.DataFrame(results)[["subreddit_name", "response_code", "description"]]
    df.to_excel(OUTPUT_PATH, index=False, engine="openpyxl")


def process_single(idx: int, row: pd.Series) -> tuple:
    """Process a single row via API. Returns (original_index, result_dict)."""
    name = str(row["subreddit_name"]).strip()
    final_url = str(row.get("final_url", "")).strip()
    print(f"  Processing r/{name} ...")
    code, desc = call_openai(name, final_url)
    return (idx, {
        "subreddit_name": name,
        "response_code": str(code),
        "description": desc,
    })


def print_existing_report(existing: dict):
    """Print a diagnostic report about what was found in the destination file."""
    total = len(existing)
    if total == 0:
        print("\n--- DESTINATION FILE REPORT ---")
        print("  No completed rows found in destination file.")
        print("-------------------------------\n")
        return

    code_counts = {}
    for entry in existing.values():
        rc = entry["response_code"]
        code_counts[rc] = code_counts.get(rc, 0) + 1

    print("\n--- DESTINATION FILE REPORT ---")
    print(f"  File: {OUTPUT_PATH}")
    print(f"  Total rows with a response_code: {total}")
    print("")
    print("  Breakdown by response_code:")
    for code in sorted(code_counts.keys()):
        print(f"    {code}: {code_counts[code]}")

    desc_empty = sum(
        1 for entry in existing.values()
        if entry["description"] in ("", "nan")
    )
    desc_filled = total - desc_empty
    print("")
    print(f"  Rows with a description: {desc_filled}")
    print(f"  Rows with empty description: {desc_empty}")
    print("-------------------------------\n")


def main():
    print(f"Reading input: {INPUT_PATH}")
    df_in = pd.read_csv(INPUT_PATH)
    total = len(df_in)
    print(f"  Total rows in input: {total}")

    # Load previous progress keyed by subreddit_name
    existing = load_existing_output()
    print_existing_report(existing)

    # Build the full results array, pre-filled from existing data where available
    results = []
    already_done = 0
    for _, row in df_in.iterrows():
        name = str(row["subreddit_name"]).strip()
        if name in existing:
            results.append({
                "subreddit_name": name,
                "response_code": existing[name]["response_code"],
                "description": existing[name]["description"],
            })
            already_done += 1
        else:
            results.append({
                "subreddit_name": name,
                "response_code": "",
                "description": "",
            })

    if already_done > 0:
        print(f"  Resuming -- {already_done} rows matched by subreddit_name from previous output.")

    # Identify rows that still need processing
    needs_work = []
    for idx, row in df_in.iterrows():
        if results[idx]["response_code"] not in ("", "nan"):
            continue

        if should_skip(row):
            results[idx] = {
                "subreddit_name": str(row["subreddit_name"]).strip(),
                "response_code": "SKIP",
                "description": "SKIP",
            }
            continue

        needs_work.append((idx, row))

    skipped_count = sum(1 for r in results if r["response_code"] == "SKIP")
    print(f"  Skipped (signals): {skipped_count}")
    print(f"  Rows needing API calls: {len(needs_work)}")

    if not needs_work:
        save_output(results)
        print("Nothing to do. Output saved.")
        return

    # Prompt user before proceeding
    answer = input("\nReady to proceed? (yes/no): ").strip().lower()
    if answer not in ("yes", "y"):
        print("Aborted by user.")
        return

    # Save once with skips filled in before we start API calls
    save_output(results)
    print("  Initial save complete (skips written).")

    # Process in batches
    total_batches = (len(needs_work) + BATCH_SIZE - 1) // BATCH_SIZE

    for batch_num in range(total_batches):
        batch_start = batch_num * BATCH_SIZE
        batch_end = min(batch_start + BATCH_SIZE, len(needs_work))
        batch = needs_work[batch_start:batch_end]

        print(f"\n  Batch {batch_num + 1}/{total_batches} "
              f"(rows {batch_start + 1}-{batch_end} of {len(needs_work)})")

        with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
            futures = {
                executor.submit(process_single, idx, row): idx
                for idx, row in batch
            }

            for future in as_completed(futures):
                idx, result = future.result()
                results[idx] = result

        save_output(results)
        print(f"  Batch {batch_num + 1} saved to disk.")

    # Final summary
    print(f"\nDone. Output saved to: {OUTPUT_PATH}")
    succeeded = sum(1 for r in results if r["response_code"] == "200")
    skipped = sum(1 for r in results if r["response_code"] == "SKIP")
    failed = total - succeeded - skipped
    print(f"  Succeeded: {succeeded}  |  Skipped: {skipped}  |  Failed/Empty: {failed}")


if __name__ == "__main__":
    main()