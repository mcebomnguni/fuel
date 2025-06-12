from django.conf import settings
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .utils import plan_fuel_stops
import logging

api_key = settings.OPENROUTESERVICE_API_KEY
logger = logging.getLogger(__name__)


def is_valid_coord(coord):
    """
    Validate if the provided coordinate dictionary contains valid latitude and longitude.

    Args:
        coord (dict): Dictionary with keys 'lat' and 'lon'.

    Returns:
        bool: True if latitude and longitude are valid floats within
              acceptable geographic ranges, False otherwise.
    """
    try:
        lat = float(coord.get("lat"))
        lon = float(coord.get("lon"))
        return -90 <= lat <= 90 and -180 <= lon <= 180
    except (TypeError, ValueError):
        return False


class FuelOptimizerAPIView(APIView):
    """
    API View to calculate optimal fuel stops along a route.

    Expects POST data with:
        - start: dict with 'lat' and 'lon' for start coordinates (required)
        - end: dict with 'lat' and 'lon' for end coordinates (required)
        - mpg: float, vehicle miles per gallon (optional, default=10)
        - range: float, vehicle max range per tank in miles (optional, default=500)
        - radius: float, search radius for fuel stops in miles (optional, default=10)

    Returns:
        JSON response with optimized fuel stops and route details,
        or error messages with appropriate HTTP status codes.
    """

    def post(self, request):
        """
        Handle POST request to calculate fuel stops.

        Validates input data, checks API key, calls the core planner utility,
        and returns the result or error response.

        Args:
            request (Request): DRF Request object containing POST data.

        Returns:
            Response: DRF Response object with JSON data and HTTP status.
        """
        try:
            start = request.data.get("start")
            end = request.data.get("end")
            mpg = float(request.data.get("mpg", 10))  # default 10 mpg
            range_miles = float(request.data.get("range", 500))  # default 500 miles
            radius = float(request.data.get("radius", 10))  # default 10 miles

            # Validate required coordinates
            if not start or not is_valid_coord(start):
                return Response(
                    {"error": "Missing or invalid 'start' coordinates (lat/lon required)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not end or not is_valid_coord(end):
                return Response(
                    {"error": "Missing or invalid 'end' coordinates (lat/lon required)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Validate API key presence
            if not settings.OPENROUTESERVICE_API_KEY:
                return Response(
                    {"error": "OpenRouteService API key not configured."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            start_coords = (float(start["lat"]), float(start["lon"]))
            end_coords = (float(end["lat"]), float(end["lon"]))

            # Call the utility function that plans fuel stops
            result = plan_fuel_stops(
                start=start_coords,
                end=end_coords,
                api_key=settings.OPENROUTESERVICE_API_KEY,
                mpg=mpg,
                range_miles=range_miles,
                radius=radius,
            )

            return Response(result, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Error in FuelOptimizerAPIView")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
