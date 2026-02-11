"""API views for fuel route optimization."""

from typing import Optional

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from fuel_stations.clients.openrouteservice import RouteNotFoundError
from fuel_stations.serializers import (
    RouteOptimizationRequestSerializer,
    RouteOptimizationResponseSerializer,
)
from fuel_stations.services.route_optimizer import (
    InsufficientStationsError,
    RouteOptimizationService,
)


class OptimizeRouteView(APIView):  # type: ignore[misc]
    """API view for route optimization with fuel stops."""

    # NOTE: AllowAny is appropriate for this assessment (public calculation API)
    # Production should add: TokenAuthentication, throttling, and API keys
    permission_classes = [AllowAny]

    @extend_schema(
        request=RouteOptimizationRequestSerializer,
        responses={200: RouteOptimizationResponseSerializer},
        description="Calculate optimal fuel stops for a given route to minimize total fuel cost",
        tags=["Route Optimization"],
    )
    def post(self, request: Request, format: Optional[str] = None) -> Response:
        """
        Optimize route with fuel stops.

        Accepts start/end coordinates and returns optimal fuel stops,
        total cost, and route information.
        """
        # Validate request
        serializer = RouteOptimizationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Extract validated data
        validated_data = serializer.validated_data
        start_lat: float = validated_data["start_lat"]
        start_lon: float = validated_data["start_lon"]
        end_lat: float = validated_data["end_lat"]
        end_lon: float = validated_data["end_lon"]

        # Call optimization service
        try:
            service = RouteOptimizationService()
            result = service.optimize_route(start_lat, start_lon, end_lat, end_lon)

            # Return result directly (already in correct format)
            return Response(result, status=status.HTTP_200_OK)

        except RouteNotFoundError as e:
            return Response(
                {"error": f"Route not found: {str(e)}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        except InsufficientStationsError as e:
            return Response(
                {"error": f"Insufficient fuel stations: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        except Exception as e:
            return Response(
                {"error": f"Internal server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
