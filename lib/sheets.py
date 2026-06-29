"""Google Sheets read/write utilities."""

import gspread
from google.oauth2.service_account import Credentials
import config


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_sheets_client():
    """Authenticate and return a gspread client."""
    creds = Credentials.from_service_account_file(
        str(config.SERVICE_ACCOUNT_JSON),
        scopes=SCOPES,
    )
    return gspread.authorize(creds)


def get_results_worksheet():
    """Open the Results worksheet."""
    client = get_sheets_client()
    spreadsheet = client.open_by_key(config.GOOGLE_SHEET_ID)
    return spreadsheet.worksheet(config.RESULTS_SHEET_NAME)


def find_marker_column(header_row, marker_text):
    """Find the column index of a marker string in the header row.

    Returns the index of the cell NEXT TO the marker (the value cell).
    Indices are 1-based (gspread convention).

    Raises ValueError if the marker is not found.
    """
    for i, cell_value in enumerate(header_row):
        if cell_value and str(cell_value).strip() == marker_text:
            return i + 2  # 1-based, and we want the cell to the RIGHT
    raise ValueError(
        f"Could not find marker '{marker_text}' in row 1. "
        f"Row 1 values: {header_row}"
    )


def read_input_string(ws=None):
    """Read the search input string from the Results sheet.

    Finds the cell to the right of 'Input String:' in row 1.

    Returns:
        The input string, or None if the cell is empty.
    """
    if ws is None:
        ws = get_results_worksheet()

    header_row = ws.row_values(1)
    col_idx = find_marker_column(header_row, config.INPUT_MARKER)
    value = ws.cell(1, col_idx).value

    if value is None or str(value).strip() == "":
        return None
    return str(value).strip()


def write_output_marker(ws, input_string):
    """Write the search string to the cell next to 'Currently Showing:' in row 1."""
    header_row = ws.row_values(1)
    col_idx = find_marker_column(header_row, config.OUTPUT_MARKER)
    ws.update_cell(1, col_idx, input_string)


def clear_results(ws, header_row_values):
    """Clear all data rows below the header, preserving row 1.

    Args:
        ws: The worksheet object.
        header_row_values: List of header values in row 1 (to determine width).
    """
    # Find the rightmost populated column in row 1
    last_col = len(header_row_values)
    if last_col == 0:
        return

    # Get total rows in the sheet
    total_rows = ws.row_count
    if total_rows <= 1:
        return

    # Build a range from row 2 to the last row, full width
    from gspread.utils import rowcol_to_a1
    start = rowcol_to_a1(2, 1)
    end = rowcol_to_a1(total_rows, last_col)
    cell_range = f"{start}:{end}"

    # Clear by writing empty values
    ws.batch_clear([cell_range])


def write_results(ws, results, column_order):
    """Write search results to the sheet starting at row 2.

    Args:
        ws: The worksheet object.
        results: List of dicts with result data.
        column_order: List of column header strings defining the order.
            Must match the headers already in row 1 of the sheet.
    """
    if not results:
        return

    # Map column headers in row 1 to their 1-based column index
    header_row = ws.row_values(1)
    col_map = {}
    for col_name in column_order:
        for i, header in enumerate(header_row):
            if header and str(header).strip().lower() == col_name.lower():
                col_map[col_name] = i  # 0-based for list indexing
                break

    missing = [c for c in column_order if c not in col_map]
    if missing:
        raise ValueError(
            f"Could not find these columns in row 1: {missing}. "
            f"Row 1 headers: {header_row}"
        )

    # Build rows as a 2D list aligned to the full sheet width
    width = len(header_row)
    rows_to_write = []
    for result in results:
        row = [""] * width
        for col_name in column_order:
            value = result.get(col_name, "")
            if value is None:
                value = ""
            row[col_map[col_name]] = value
        rows_to_write.append(row)

    # Write all rows in one batch starting at row 2
    from gspread.utils import rowcol_to_a1
    start = rowcol_to_a1(2, 1)
    end = rowcol_to_a1(2 + len(rows_to_write) - 1, width)
    cell_range = f"{start}:{end}"

    ws.update(cell_range, rows_to_write, value_input_option="RAW")