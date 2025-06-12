import csv
import time
import requests
import os

# Input and output CSV file paths
INPUT_CSV = '/Users/twofa/Desktop/fuel_optimizer/core/fuel-prices-for-be-assessment.csv'
OUTPUT_CSV = 'fuel-price-geocoded.csv'

# Nominatim API endpoint and headers for user agent identification
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {'User-Agent': 'FuelOptimizer/1.0'}


def geocode_address(city, state):
    """
    Geocode a city and state into latitude and longitude using Nominatim API.

    Args:
        city (str): City name.
        state (str): State name.

    Returns:
        tuple: (latitude, longitude) as floats if successful, otherwise (None, None).
    """
    try:
        query = f"{city}, {state}, USA"
        params = {
            'q': query,
            'format': 'json',
            'limit': 1
        }
        response = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            return lat, lon
    except requests.RequestException as e:
        print(f"Network error while geocoding '{city}, {state}': {e}")
    except Exception as e:
        print(f"Failed to geocode '{city}, {state}': {e}")
    return None, None


def get_processed_rows_count(output_csv):
    """
    Determine how many rows have already been processed in the output CSV.

    Args:
        output_csv (str): Path to the output CSV file.

    Returns:
        int: Number of data rows processed (excluding header).
    """
    if not os.path.exists(output_csv):
        return 0
    with open(output_csv, newline='', encoding='utf-8') as f:
        # Count lines and subtract 1 for header
        count = sum(1 for _ in f) - 1
        return max(count, 0)


def geocode_csv():
    """
    Read the input CSV, geocode city/state pairs, and append lat/lon to the output CSV.

    Resumes from where it left off if the output CSV exists.
    """
    processed_rows = get_processed_rows_count(OUTPUT_CSV)
    print(f"Rows already processed: {processed_rows}")

    with open(INPUT_CSV, newline='', encoding='utf-8') as infile, \
         open(OUTPUT_CSV, 'a', newline='', encoding='utf-8') as outfile:

        reader = csv.DictReader(infile)
        # Append Latitude and Longitude fields to existing CSV headers
        fieldnames = reader.fieldnames + ['Latitude', 'Longitude']
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)

        # Write header if output CSV is empty
        if processed_rows == 0:
            writer.writeheader()

        for i, row in enumerate(reader):
            # Skip rows already processed
            if i < processed_rows:
                continue

            city = row.get('City')
            state = row.get('State')

            lat, lon = geocode_address(city, state)
            row['Latitude'] = lat
            row['Longitude'] = lon

            writer.writerow(row)

            print(f"[{i}] Geocoded: {city}, {state} => {lat}, {lon}")

            # Respect Nominatim usage policy: max 1 request per second
            time.sleep(1)


if __name__ == "__main__":
    geocode_csv()
