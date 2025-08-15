import csv
import os
import re
import tempfile
from typing import Dict, Any, Optional

# Allow overriding via environment variable; default to 'results.csv'
RESULTS_CSV = os.environ.get('RESULTS_CSV', 'results.csv')

def _norm(s: str) -> str:
    """Lowercase, strip, and remove all whitespace for consistent matching."""
    return re.sub(r'\s+', '', (s or '').strip().lower())

def find_car_in_csv(car_string: str):
    """
    Look up a car like '2020 Honda Odyssey 3.5L V6'.
    Car is stored normalized in CSV under 'Car' (e.g., '2020hondaodyssey3.5lv6').
    Returns dict of ALL columns for that car (except 'Car') if found, else False.
    """
    if not os.path.isfile(RESULTS_CSV):
        return False

    target = _norm(car_string)

    with open(RESULTS_CSV, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if _norm(row.get('Car', '')) == target:
                return {k: v for k, v in row.items() if k != 'Car'}
    return False

def upsert_car_data(car_string: str, new_data: Optional[Dict[str, Any]] = None):
    """
    Merge `new_data` columns into the single row for this car (creating it if missing).
    - Adds new columns to the CSV header if needed.
    - Joins list values as '; ' strings for CSV storage.
    - Returns the merged row (minus 'Car').

    Example new_data:
      {
        'Oil Filters': 'WIX: 51334; Bosch: 3323',
        'Oil Types': '5w-20; 0w-20',
        'Oil Capacity': '5.4 quarts',
        'Engine Air Filters': 'WIX: 49079'
      }
    """
    new_data = new_data or {}
    car_key = _norm(car_string)

    # Normalize values for CSV (lists -> '; ' strings)
    cleaned: Dict[str, str] = {}
    for k, v in new_data.items():
        if k == 'Car':
            continue
        if isinstance(v, list):
            cleaned[k] = '; '.join(map(str, v))
        else:
            cleaned[k] = '' if v is None else str(v)

    rows = []
    existing_headers = set()

    if os.path.isfile(RESULTS_CSV):
        with open(RESULTS_CSV, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if reader.fieldnames:
                existing_headers.update(reader.fieldnames)

    # Ensure 'Car' header always exists
    existing_headers.add('Car')

    # Build final header set: old headers + new cleaned keys
    final_headers = existing_headers.union(cleaned.keys())

    # Track whether we found the car row
    found = False
    merged_row = None

    for r in rows:
        if _norm(r.get('Car', '')) == car_key:
            # Merge new values into the row
            r.update(cleaned)
            merged_row = r
            found = True
            break

    if not found:
        # Create a new row with all headers (blank by default)
        new_row = {h: '' for h in final_headers}
        new_row['Car'] = car_key
        new_row.update(cleaned)
        rows.append(new_row)
        merged_row = new_row

    # Rewrite CSV with union of headers (Car first)
    header_list = ['Car'] + [h for h in final_headers if h and h != 'Car']

    # Ensure all rows have all headers
    for r in rows:
        for h in header_list:
            if h not in r:
                r[h] = ''

    # Atomic rewrite
    fd, tmp_path = tempfile.mkstemp(prefix='results_', suffix='.csv')
    os.close(fd)
    try:
        with open(tmp_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=header_list)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
        os.replace(tmp_path, RESULTS_CSV)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    return {k: v for k, v in (merged_row or {}).items() if k != 'Car'}
