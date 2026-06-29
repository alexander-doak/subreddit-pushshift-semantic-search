"""Read search input from Google Sheet, run vector search, write results back."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))

import config
import embeddings
import search
import sheets


# Column names that must exist in row 1 of the Results sheet
RESULT_COLUMNS = [
    "subreddit_name",
    "subreddit_url",
    "comments_size_mb",
    "submissions_size_mb",
    "banned",
    "adult",
    "valid",
    "description",
    "semantic_strength",
]


def run_search(ws):
    """Run a single search cycle: read query, encode, search, write results."""

    # Step 1: Read the input string from Google Sheets
    print("Reading query from Google Sheets ...")
    input_string = sheets.read_input_string(ws)

    if not input_string:
        print("ERROR: No input string found.")
        print(f"Please enter a search query in the cell to the right of "
              f"'{config.INPUT_MARKER}' on the '{config.RESULTS_SHEET_NAME}' sheet.")
        return

    print(f"Input string: \"{input_string}\"")
    print()

    # Step 2: Encode the query (model stays loaded between runs)
    print("Encoding query ...")
    start = time.time()
    query_vector = embeddings.encode_query(input_string)
    print(f"Query encoded in {time.time() - start:.1f}s")
    print()

    # Step 3: Two-stage search
    print("Running search ...")
    start = time.time()
    results = search.search(query_vector)
    print(f"Search completed in {time.time() - start:.1f}s")
    print()

    if not results:
        print("No results found. Are there embeddings in the database?")
        return

    # Show a quick preview
    print(f"Top 5 results:")
    for i, r in enumerate(results[:5]):
        print(f"  {i+1}. [{r['semantic_strength']:.4f}] r/{r['subreddit_name']}")
        desc = r['description'][:80] + "..." if len(r['description']) > 80 else r['description']
        print(f"     {desc}")
    print()

    # Step 4: Clear old results and write new ones
    print("Writing results to Google Sheets ...")
    start = time.time()

    header_row = ws.row_values(1)
    sheets.clear_results(ws, header_row)
    sheets.write_results(ws, results, RESULT_COLUMNS)
    sheets.write_output_marker(ws, input_string)

    print(f"{len(results)} results written in {time.time() - start:.1f}s")
    print()
    print(f"Currently showing results for: \"{input_string}\"")


def main():
    print("=" * 60)
    print("SEMANTIC SEARCH")
    print("=" * 60)
    print()

    # Connect to Google Sheets once
    print("Connecting to Google Sheets ...")
    ws = sheets.get_results_worksheet()
    print()

    # Pre-load the embedding model so the first search isn't slower than the rest
    print("Pre-loading embedding model ...")
    embeddings.get_model()
    print()

    # Run loop
    while True:
        run_search(ws)
        print()

        try:
            answer = input("Run again? [Y/n]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if answer in ("n", "no"):
            break

        print()
        print("-" * 60)
        print()

    print("Done.")


if __name__ == "__main__":
    main()