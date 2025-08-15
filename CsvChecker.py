import csv
import os
import re

RESULTS_CSV = 'results.csv'

def _norm(s: str) -> str:
    """Lowercase, strip spaces, and remove all whitespace for consistent matching."""
    return re.sub(r'\s+', '', (s or '').strip().lower())

def find_car_in_csv(car_string):
    """
    Search results.csv for a matching car string like '2020 honda odyssey 3.5l v6'.
    After normalization this becomes '2020hondaodyssey3.5lv6'.
    If found, returns dict of the remaining columns.
    If not found, returns False.
    """
    if not os.path.isfile(RESULTS_CSV):
        return False  # CSV doesn't exist yet

    car_search = _norm(car_string)

    with open(RESULTS_CSV, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if _norm(row.get('Car', '')) == car_search:
                return {k: v for k, v in row.items() if k != 'Car'}

    return False

def append_car_to_csv(car_string, oil_filters, oil_types, oil_capacity):
    """
    Append a new car entry to results.csv if it doesn't already exist.
    'car_string' should be raw like '2020 honda odyssey 3.5l v6'.
    Creates the file with headers if it doesn't exist.
    Returns True if appended, False if duplicate.
    """
    fieldnames = ['Car', 'Oil Filters', 'Oil Types', 'Oil Capacity']
    normalized_car = _norm(car_string)

    # Avoid duplicate before appending
    if find_car_in_csv(car_string):
        return False  # Already exists

    file_exists = os.path.isfile(RESULTS_CSV)
    with open(RESULTS_CSV, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            'Car': normalized_car,
            'Oil Filters': oil_filters,
            'Oil Types': oil_types,
            'Oil Capacity': oil_capacity
        })

    return True
