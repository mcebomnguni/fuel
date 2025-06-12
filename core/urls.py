from django.urls import path
from .views import FuelOptimizerAPIView

"""
URL configuration for fuel optimization API endpoints.

Defines route(s) for fuel optimizer functionality.
"""

urlpatterns = [
    # API endpoint for fuel optimization calculations.
    # Access via: /fuel-optimizer/
    path('fuel-optimizer/', FuelOptimizerAPIView.as_view(), name='fuel-optimizer'),
]
