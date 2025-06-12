#  Fuel Optimizer API – Django Backend

This project is a **Django RESTful API** that calculates the most **cost-efficient fuel stops** along a trucking route between two locations in the **USA**. It uses a pre-supplied CSV of fuel stations and prices, simulates a 500-mile driving range (10 MPG fuel efficiency), and returns optimal stops for refueling.

---

##  What It Does

- Accepts a **start and end coordinate** (longitude, latitude).
- Calculates the total route using **OpenRouteService**.
- Simulates fuel stops every **500 miles**.
- For each stop, finds the **cheapest nearby fuel station** (within 50 miles) from a pre-loaded CSV file.
- Returns the **total fuel cost** and a list of stops with location and price info.

---

##  Project Structure

```plaintext
fuel_optimizer/
├── core/
│   ├── views.py               # API view for fuel optimization
│   ├── urls.py                # URL routing for the API
│   ├── utils/
│   │   ├── fuel_utils.py      # Route analysis and fuel cost logic
│   │   └── geocode_csv.py     # Geocodes fuel station data from CSV
│   ├── fuel-price-geocoded.csv  # CSV with fuel stations and lat/lon
├── manage.py
├── requirements.txt
├── README.md


## Getting Started
1. Clone the Repository
bash
Copy
Edit
git clone https://github.com/YOUR_USERNAME/fuel-optimizer-api.git
cd fuel-optimizer-api
2. Set Up Your Environment
bash
Copy
Edit
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
3. Get Your OpenRouteService API Key
Go to OpenRouteService and sign up.

Copy your API key.

Add it to your environment or directly into the code in fuel_utils.py.

## Geocode Fuel Prices CSV (IMPORTANT ⚠️)
Before running the API, you must geocode the fuel-prices-for-be-assessment.csv file to include Latitude and Longitude.

Run This Script:
bash
Copy
Edit
python core/utils/geocode_csv.py
What It Does:
Reads each city and state from the input CSV.

Uses OpenStreetMap’s Nominatim API to get coordinates.

Writes a new file: fuel-price-geocoded.csv.

Note: Nominatim allows only 1 request per second. The script automatically handles this.

## How the Code Works (Step-by-Step)
geocode_csv.py
Purpose: Add Latitude and Longitude to fuel stations using city/state.

Libraries: csv, requests, time

Key Function: geocode_address() uses Nominatim to fetch coordinates.

Output: A new CSV (fuel-price-geocoded.csv) with all original data + coordinates.

utils.py
Purpose: Core logic for calculating route and fuel stops.

Libraries: requests, geopy.distance, csv

Steps:

Calls OpenRouteService API to get the full driving path from start to end.

Splits the route into points every 500 miles.

For each point, checks all fuel stations within 50 miles using haversine distance.

Selects the cheapest fuel station nearby.

Calculates how many gallons are needed (assumes 10 MPG, so 50 gallons per stop).

Returns fuel stops and total cost.

views.py
Contains FuelOptimizerAPIView, a Django REST Framework APIView.

Accepts JSON POST body:

json
Copy
Edit
{
  "start": [-122.4194, 37.7749],
  "end": [-74.0060, 40.7128]
}
Calls the optimizer and returns JSON with:

Total miles

Total fuel cost

List of fuel stops with coordinates and price

## Testing the API in Postman
Run the Django Server
bash
Copy
Edit
python manage.py runserver
Server will be available at http://127.0.0.1:8000/

Test Endpoint
http
Copy
Edit
POST /api/fuel-optimizer/
JSON Body
json
Copy
Edit
{
  "start": [-118.2437, 34.0522],
  "end": [-87.6298, 41.8781]
}
Sample Response
json
Copy
Edit
{
  "total_miles": 2024.12,
  "total_cost": 948.31,
  "fuel_stops": [
    {
      "mile_marker": 500,
      "location": {
        "lat": 35.4676,
        "lon": -97.5164
      },
      "price_per_gallon": 4.28,
      "gallons_needed": 50.0,
      "cost": 214.0
    },
    ...
  ]
}


## Configuration Assumptions
Truck range: 500 miles

Fuel efficiency: 10 MPG

Tank capacity: 50 gallons

Distance units: miles

Fuel station radius: 50 miles

##Future Ideas
Add authentication & user tracking

Replace static CSV with a dynamic fuel price API

Add Google Maps/Leaflet-based frontend

Dockerize the app for production

## License
MIT License – free to use and modify.

## Author
Mcebo Mnguni

GitHub: mcebomnguni

LinkedIn: linkedin.com/in/mcebo-mnguni-2a5187233
