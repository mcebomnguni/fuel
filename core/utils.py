from django.conf import settings
import pandas as pd
import requests
from geopy.distance import geodesic
import time
import os

# Constants
GEOCODE_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "fuel-route-app/1.0"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

LOCATIONIQ_URL = "https://us1.locationiq.com/v1/search.php"
LOCATIONIQ_API_KEY = os.getenv("LOCATIONIQ_API_KEY", "your_locationiq_api_key_here")


def preprocess_address(addr):
    """
    Normalize and preprocess an address string.

    Args:
        addr (str): Raw address string.

    Returns:
        str: Normalized address string with common replacements.
             Returns empty string if input is None or empty.
    """
    if not addr:
        return ""
    addr = addr.replace('&', 'and').replace('EXIT', 'Exit').strip()
    return addr


def geocode_locationiq(address):
    """
    Geocode an address using LocationIQ as a fallback geocoder.

    Args:
        address (str): Address string to geocode.

    Returns:
        tuple or (None, None): Latitude and longitude if found,
                               otherwise (None, None).
    """
    params = {
        "key": LOCATIONIQ_API_KEY,
        "q": address,
        "format": "json",
        "limit": 1
    }
    try:
        response = requests.get(LOCATIONIQ_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            return lat, lon
    except Exception as e:
        print(f"LocationIQ geocoding failed for '{address}': {e}")
    return None, None


def geocode_address(address):
    """
    Geocode an address using Nominatim (OpenStreetMap) with fallback to LocationIQ.

    Retries up to MAX_RETRIES times on failure with delay between retries.

    Args:
        address (str): Address string to geocode.

    Returns:
        tuple or (None, None): Latitude and longitude if found,
                               otherwise (None, None).
    """
    params = {
        "q": address,
        "format": "json",
        "limit": 1,
        "countrycodes": "us"
    }
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(
                GEOCODE_URL, params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            if data:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                return lat, lon
            else:
                print(f"Nominatim: No results for '{address}', falling back.")
                return geocode_locationiq(address)
        except Exception as e:
            print(f"Attempt {attempt} - Nominatim geocoding failed for '{address}': {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                print(f"Max retries reached for '{address}', trying LocationIQ fallback.")
                return geocode_locationiq(address)
    return None, None


def load_fuel_prices():
    """
    Load fuel price data from a CSV file, ensuring latitude and longitude are present.

    If lat/lon are missing, attempts to geocode based on city/state fields.

    Returns:
        pandas.DataFrame: DataFrame with columns including latitude, longitude, and price.
    """
    csv_path = os.path.join(settings.BASE_DIR, "core", "fuel-price-geocoded.csv")
    df = pd.read_csv(csv_path)

    # Normalize column names to lowercase with underscores
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Rename 'retail_price' to 'price' if present
    if 'retail_price' in df.columns:
        df.rename(columns={'retail_price': 'price'}, inplace=True)

    # Check if latitude and longitude columns exist, else geocode addresses
    if 'latitude' not in df.columns or 'longitude' not in df.columns:
        print("Latitude/Longitude missing in CSV. Attempting to geocode...")
        latitudes = []
        longitudes = []

        for idx, row in df.iterrows():
            city, state = row.get('city'), row.get('state')
            if pd.notna(city) and pd.notna(state):
                full_address = f"{city}, {state}"
                lat, lon = geocode_address(full_address)
            else:
                print(f"Row {idx} missing city/state. Skipping.")
                lat, lon = None, None

            latitudes.append(lat)
            longitudes.append(lon)
            time.sleep(1)  # avoid overloading geocoding API

        df['latitude'] = latitudes
        df['longitude'] = longitudes

    # Remove rows with missing essential data
    df.dropna(subset=['latitude', 'longitude', 'price'], inplace=True)
    return df


def get_route(start, end, api_key):
    """
    Fetch the driving route between start and end points from OpenRouteService API.

    Args:
        start (tuple): (latitude, longitude) of start point.
        end (tuple): (latitude, longitude) of end point.
        api_key (str): API key for OpenRouteService.

    Returns:
        tuple: (list of (lat, lon) tuples representing route coordinates, total distance in miles).

    Raises:
        RuntimeError: If the API call fails or returns invalid data.
    """
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": api_key}
    params = {
        "start": f"{start[1]},{start[0]}",
        "end": f"{end[1]},{end[0]}"
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        raise RuntimeError(f"Route API call failed: {e}")

    coords = data['features'][0]['geometry']['coordinates']
    # Coordinates are [lon, lat], convert to [lat, lon]
    route_coords = [(lat, lon) for lon, lat in coords]
    distance_meters = data['features'][0]['properties']['segments'][0]['distance']
    distance_miles = distance_meters * 0.000621371  # meters to miles
    return route_coords, distance_miles


def find_nearby_stations(point, stations_df, radius=10):
    """
    Find fuel stations within a given radius (in miles) of a geographic point.

    Args:
        point (tuple): (latitude, longitude) of the reference point.
        stations_df (pandas.DataFrame): DataFrame with fuel stations including lat/lon and price.
        radius (float): Search radius in miles.

    Returns:
        list: Sorted list of tuples containing
              (station_point (lat, lon), price_per_gallon, station_name).
    """
    def compute_distance(row):
        return geodesic(point, (row.latitude, row.longitude)).miles

    stations_df = stations_df.copy()
    stations_df['distance'] = stations_df.apply(compute_distance, axis=1)
    nearby_df = stations_df[stations_df['distance'] <= radius].copy()
    nearby_df.sort_values('price', inplace=True)

    nearby = []
    for _, row in nearby_df.iterrows():
        station_point = (row['latitude'], row['longitude'])
        station_name = row.get('truckstop_name', 'Unknown')
        nearby.append((station_point, row['price'], station_name))
    return nearby


def plan_fuel_stops(start, end, api_key, mpg=10, range_miles=500, radius=10):
    """
    Calculate optimal fuel stops along a route based on vehicle mpg, range, and station prices.

    Args:
        start (tuple): (latitude, longitude) of the start point.
        end (tuple): (latitude, longitude) of the end point.
        api_key (str): OpenRouteService API key.
        mpg (float): Vehicle miles per gallon efficiency (default 10).
        range_miles (float): Maximum miles vehicle can travel on a full tank (default 500).
        radius (float): Search radius in miles for nearby fuel stations (default 10).

    Returns:
        dict: Dictionary containing total distance, total gallons needed,
              estimated fuel cost, list of fuel stops, and route coordinates.
    """
    stations_df = load_fuel_prices()
    route_coords, total_distance = get_route(start, end, api_key)
    fuel_needed = total_distance / mpg

    stops = []
    accumulated_distance = 0

    for i in range(1, len(route_coords)):
        segment_dist = geodesic(route_coords[i-1], route_coords[i]).miles
        accumulated_distance += segment_dist

        # Decide if a fuel stop is needed (range exceeded or last point)
        if accumulated_distance >= range_miles or i == len(route_coords) - 1:
            point = route_coords[i]
            nearby_stations = find_nearby_stations(point, stations_df, radius)
            if nearby_stations:
                best_station = nearby_stations[0]
                # Calculate gallons for final leg differently
                if i == len(route_coords) - 1:
                    gallons_needed = segment_dist / mpg
                else:
                    gallons_needed = range_miles / mpg
                cost = gallons_needed * best_station[1]
                stops.append({
                    "location": point,
                    "station_name": best_station[2],
                    "price_per_gallon": best_station[1],
                    "gallons": round(gallons_needed, 2),
                    "cost": round(cost, 2),
                })
            accumulated_distance = 0  # reset after stop

    total_cost = sum(stop["cost"] for stop in stops)
    return {
        "total_distance_miles": round(total_distance, 2),
        "fuel_needed_gallons": round(fuel_needed, 2),
        "estimated_cost": round(total_cost, 2),
        "fuel_stops": stops,
        "route_coords": route_coords
    }
