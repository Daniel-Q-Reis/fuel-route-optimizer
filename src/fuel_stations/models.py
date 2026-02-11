"""FuelStation model for storing fuel station data with geocoded coordinates."""

from django.db import models


class FuelStation(models.Model):
    """
    Model representing a fuel station with location and pricing data.

    Attributes:
        truckstop_name: Name of the truck stop/fuel station
        address: Street address
        city: City name
        state: Two-letter state code (indexed for filtering)
        retail_price: Current retail fuel price per gallon (indexed for optimization)
        latitude: Geocoded latitude coordinate (indexed for spatial queries)
        longitude: Geocoded longitude coordinate (indexed for spatial queries)
        created_at: Timestamp when the record was created
    """

    truckstop_name = models.CharField(max_length=255)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2, db_index=True)
    retail_price = models.DecimalField(max_digits=5, decimal_places=2, db_index=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, db_index=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            # Composite index for geospatial bounding box queries
            models.Index(fields=["latitude", "longitude"], name="idx_location"),
            # Index for finding cheapest stations
            models.Index(fields=["retail_price"], name="idx_price"),
        ]
        verbose_name = "Fuel Station"
        verbose_name_plural = "Fuel Stations"

    def __str__(self) -> str:
        """Return string representation of the fuel station."""
        return f"{self.truckstop_name} - {self.city}, {self.state}"
