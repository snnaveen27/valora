"""
Advanced Spatial Analysis for Valora AI

Features:
1. Isochrone analysis - "Show areas within X minutes of point"
2. Heatmap generation - Price/safety/infrastructure density overlays
3. Neighborhood similarity - "Find areas similar to X but cheaper"
4. Future infrastructure impact - Predict value changes from planned developments
"""

import math
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict


class TransportMode(Enum):
    """Transport modes for isochrone calculation."""
    WALK = "walk"
    DRIVE = "drive"
    TRANSIT = "transit"
    CYCLE = "cycle"


class HeatmapType(Enum):
    """Types of heatmaps."""
    PRICE = "price"
    PRICE_GROWTH = "price_growth"
    SAFETY = "safety"
    INFRASTRUCTURE = "infrastructure"
    WALKABILITY = "walkability"
    INVESTMENT_SCORE = "investment_score"


@dataclass
class IsochroneResult:
    """Result of isochrone analysis."""
    center: Tuple[float, float]  # (lat, lng)
    mode: TransportMode
    duration_minutes: int
    polygon: List[Tuple[float, float]]  # Boundary points
    area_sqkm: float
    locations_inside: List[Dict[str, Any]]
    properties_inside: int
    pois_inside: Dict[str, int]


@dataclass
class HeatmapData:
    """Heatmap data for visualization."""
    type: HeatmapType
    bounds: Dict[str, float]  # {north, south, east, west}
    grid_size: Tuple[int, int]  # (rows, cols)
    values: List[List[float]]  # 2D grid of values
    min_value: float
    max_value: float
    unit: str
    legend: List[Dict[str, Any]]


@dataclass
class SimilarityMatch:
    """A neighborhood similarity match."""
    location_name: str
    lat: float
    lng: float
    similarity_score: float  # 0-1
    price_difference_pct: float  # Negative = cheaper
    matching_features: List[str]
    differing_features: List[str]
    metrics: Dict[str, float]


@dataclass
class InfrastructureImpact:
    """Predicted impact of future infrastructure."""
    infrastructure_type: str
    location: Tuple[float, float]
    completion_year: int
    affected_radius_km: float
    predicted_price_impact_pct: float
    affected_localities: List[str]
    confidence: float


class IsochroneCalculator:
    """
    Calculate isochrones (travel time polygons) from a point.
    
    Uses simplified distance-based calculation for offline operation.
    For production, can integrate with OSRM or similar routing engine.
    """
    
    # Average speeds in km/h by mode
    SPEEDS = {
        TransportMode.WALK: 5.0,
        TransportMode.CYCLE: 15.0,
        TransportMode.DRIVE: 30.0,  # Urban average with traffic
        TransportMode.TRANSIT: 20.0,  # Including wait times
    }
    
    # Penalty factors for non-straight-line travel
    DETOUR_FACTORS = {
        TransportMode.WALK: 1.3,
        TransportMode.CYCLE: 1.2,
        TransportMode.DRIVE: 1.4,
        TransportMode.TRANSIT: 1.5,
    }
    
    def __init__(self, db_service=None):
        self.db = db_service
    
    def calculate(
        self,
        center: Tuple[float, float],
        duration_minutes: int,
        mode: TransportMode = TransportMode.WALK,
        resolution: int = 36  # Points on polygon
    ) -> IsochroneResult:
        """
        Calculate isochrone polygon for given center and duration.
        
        Args:
            center: (lat, lng) center point
            duration_minutes: Travel time in minutes
            mode: Transport mode
            resolution: Number of points on boundary polygon
        
        Returns:
            IsochroneResult with boundary polygon and statistics
        """
        speed_kmh = self.SPEEDS[mode]
        detour = self.DETOUR_FACTORS[mode]
        
        # Max distance in km (accounting for detour)
        max_distance_km = (speed_kmh * duration_minutes / 60) / detour
        
        # Generate polygon points
        polygon = self._generate_polygon(center, max_distance_km, resolution)
        
        # Calculate area
        area_sqkm = self._polygon_area(polygon)
        
        # Find locations inside (if DB available)
        locations_inside = []
        properties_inside = 0
        pois_inside = {}
        
        if self.db:
            locations_inside, properties_inside, pois_inside = self._find_inside(
                center, max_distance_km
            )
        
        return IsochroneResult(
            center=center,
            mode=mode,
            duration_minutes=duration_minutes,
            polygon=polygon,
            area_sqkm=area_sqkm,
            locations_inside=locations_inside,
            properties_inside=properties_inside,
            pois_inside=pois_inside
        )
    
    def _generate_polygon(
        self,
        center: Tuple[float, float],
        radius_km: float,
        resolution: int
    ) -> List[Tuple[float, float]]:
        """Generate circular polygon approximation."""
        lat, lng = center
        points = []
        
        for i in range(resolution):
            angle = 2 * math.pi * i / resolution
            
            # Convert km to degrees (approximate)
            dlat = radius_km / 111.0  # 1 degree lat ≈ 111 km
            dlng = radius_km / (111.0 * math.cos(math.radians(lat)))
            
            point_lat = lat + dlat * math.cos(angle)
            point_lng = lng + dlng * math.sin(angle)
            points.append((point_lat, point_lng))
        
        # Close polygon
        points.append(points[0])
        return points
    
    def _polygon_area(self, polygon: List[Tuple[float, float]]) -> float:
        """Calculate polygon area using shoelace formula."""
        n = len(polygon)
        if n < 3:
            return 0.0
        
        area = 0.0
        for i in range(n - 1):
            lat1, lng1 = polygon[i]
            lat2, lng2 = polygon[i + 1]
            area += lng1 * lat2 - lng2 * lat1
        
        # Convert to sq km (approximate)
        area_deg = abs(area) / 2.0
        area_sqkm = area_deg * 111.0 * 111.0 * math.cos(math.radians(polygon[0][0]))
        return area_sqkm
    
    def _find_inside(
        self,
        center: Tuple[float, float],
        radius_km: float
    ) -> Tuple[List[Dict], int, Dict[str, int]]:
        """Find locations, properties, POIs inside the isochrone."""
        locations = []
        properties = 0
        pois = defaultdict(int)
        
        try:
            # Get nearby properties
            props = self._get_properties_near(
                lat=center[0], lng=center[1], radius_km=radius_km
            )
            properties = len(props) if props else 0
            
            # Get nearby POIs
            nearby_pois = self._get_pois_in_radius(
                lat=center[0], lng=center[1], radius_km=radius_km
            )
            if nearby_pois:
                for poi in nearby_pois:
                    category = poi.get('category', 'other')
                    pois[category] += 1
            
            # Get localities
            places = self._search_places(center)
            if places:
                for place in places[:10]:
                    locations.append({
                        "name": place.get('name'),
                        "type": place.get('type'),
                        "distance_km": self._haversine(center, (place.get('lat'), place.get('lng')))
                    })
        except Exception as e:
            print(f"[WARNING] Isochrone DB lookup failed: {e}")
        
        return locations, properties, dict(pois)

    def _get_properties_near(self, lat: float, lng: float, radius_km: float) -> List[Dict[str, Any]]:
        """Fetch nearby properties with compatibility across DB services."""
        if not self.db:
            return []
        if hasattr(self.db, "search_properties_near"):
            return self.db.search_properties_near(lat=lat, lng=lng, radius_km=radius_km)
        if hasattr(self.db, "search_properties"):
            return self.db.search_properties(lat=lat, lng=lng, radius_m=int(radius_km * 1000), limit=500)
        if hasattr(self.db, "search"):
            return self.db.search(lat=lat, lng=lng, radius_m=int(radius_km * 1000), limit=500)
        if hasattr(self.db, "get_all_properties"):
            props = self.db.get_all_properties(limit=2000) or []
            return [p for p in props if self._haversine((lat, lng), (p.get('latitude'), p.get('longitude'))) <= radius_km]
        return []

    def _get_pois_in_radius(self, lat: float, lng: float, radius_km: float) -> List[Dict[str, Any]]:
        """Fetch nearby POIs with compatibility across DB services."""
        if not self.db:
            return []
        if hasattr(self.db, "get_pois_in_radius"):
            return self.db.get_pois_in_radius(lat=lat, lng=lng, radius_km=radius_km)
        if hasattr(self.db, "get_pois"):
            return self.db.get_pois(lat=lat, lng=lng, radius_m=int(radius_km * 1000), limit=1000)
        if hasattr(self.db, "get_all_pois"):
            pois = self.db.get_all_pois(limit=5000) or []
            return [p for p in pois if self._haversine((lat, lng), (p.get('lat') or p.get('latitude'), p.get('lng') or p.get('longitude'))) <= radius_km]
        return []

    def _search_places(self, center: Tuple[float, float], limit: int = 10) -> List[Dict[str, Any]]:
        """Find nearby places with compatibility across DB services."""
        if not self.db:
            return []
        if hasattr(self.db, "search_places"):
            return self.db.search_places(f"{center[0]},{center[1]}") or []
        if hasattr(self.db, "get_all_places"):
            places = self.db.get_all_places() or []
            scored = []
            for place in places:
                lat = place.get('lat') or place.get('latitude')
                lng = place.get('lng') or place.get('longitude')
                if lat is None or lng is None:
                    continue
                distance = self._haversine(center, (lat, lng))
                scored.append({**place, "distance_km": distance})
            scored.sort(key=lambda p: p.get("distance_km", float("inf")))
            return scored[:limit]
        return []
    
    def _haversine(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate distance between two points in km."""
        lat1, lng1 = math.radians(p1[0]), math.radians(p1[1])
        lat2, lng2 = math.radians(p2[0]), math.radians(p2[1])
        
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return 6371 * c  # Earth radius in km


class HeatmapGenerator:
    """
    Generate heatmaps for various metrics.
    
    Creates grid-based overlays for visualization on maps.
    """
    
    # Color schemes for different heatmap types
    COLOR_SCHEMES = {
        HeatmapType.PRICE: ["#00ff00", "#ffff00", "#ff0000"],  # Green to red
        HeatmapType.PRICE_GROWTH: ["#ff0000", "#ffffff", "#00ff00"],  # Red to green
        HeatmapType.SAFETY: ["#ff0000", "#ffff00", "#00ff00"],  # Red to green
        HeatmapType.INFRASTRUCTURE: ["#ffffff", "#0066ff", "#000066"],
        HeatmapType.WALKABILITY: ["#ff6600", "#ffff00", "#00cc00"],
        HeatmapType.INVESTMENT_SCORE: ["#cccccc", "#6699ff", "#0000ff"],
    }
    
    def __init__(self, db_service=None):
        self.db = db_service
    
    def generate(
        self,
        heatmap_type: HeatmapType,
        bounds: Dict[str, float],
        grid_size: int = 50
    ) -> HeatmapData:
        """
        Generate heatmap data for the specified bounds.
        
        Args:
            heatmap_type: Type of heatmap to generate
            bounds: {north, south, east, west} bounding box
            grid_size: Number of cells per dimension
        
        Returns:
            HeatmapData with grid values for visualization
        """
        north, south = bounds['north'], bounds['south']
        east, west = bounds['east'], bounds['west']
        
        lat_step = (north - south) / grid_size
        lng_step = (east - west) / grid_size
        
        # Initialize grid
        values = [[0.0 for _ in range(grid_size)] for _ in range(grid_size)]
        
        # Fill grid based on type
        if heatmap_type == HeatmapType.PRICE:
            values = self._generate_price_heatmap(bounds, grid_size, lat_step, lng_step)
        elif heatmap_type == HeatmapType.INFRASTRUCTURE:
            values = self._generate_infrastructure_heatmap(bounds, grid_size, lat_step, lng_step)
        elif heatmap_type == HeatmapType.SAFETY:
            values = self._generate_safety_heatmap(bounds, grid_size, lat_step, lng_step)
        elif heatmap_type == HeatmapType.WALKABILITY:
            values = self._generate_walkability_heatmap(bounds, grid_size, lat_step, lng_step)
        else:
            values = self._generate_generic_heatmap(bounds, grid_size, heatmap_type)
        
        # Calculate statistics
        flat_values = [v for row in values for v in row if v > 0]
        min_val = min(flat_values) if flat_values else 0
        max_val = max(flat_values) if flat_values else 100
        
        # Generate legend
        legend = self._generate_legend(heatmap_type, min_val, max_val)
        
        unit = self._get_unit(heatmap_type)
        
        return HeatmapData(
            type=heatmap_type,
            bounds=bounds,
            grid_size=(grid_size, grid_size),
            values=values,
            min_value=min_val,
            max_value=max_val,
            unit=unit,
            legend=legend
        )
    
    def _generate_price_heatmap(
        self,
        bounds: Dict[str, float],
        grid_size: int,
        lat_step: float,
        lng_step: float
    ) -> List[List[float]]:
        """Generate price per sqft heatmap."""
        values = [[0.0 for _ in range(grid_size)] for _ in range(grid_size)]
        
        if not self.db:
            # Generate synthetic data for demo
            return self._synthetic_price_heatmap(bounds, grid_size)
        
        try:
            # Get properties in bounds (avoid full-table scans when possible)
            center_lat = (bounds['north'] + bounds['south']) / 2
            center_lng = (bounds['east'] + bounds['west']) / 2
            radius_km = max(
                (bounds['north'] - bounds['south']) * 111,
                (bounds['east'] - bounds['west']) * 111 * math.cos(math.radians(center_lat))
            ) / 2
            properties = None
            if hasattr(self.db, "search_properties"):
                properties = self.db.search_properties(
                    lat=center_lat,
                    lng=center_lng,
                    radius_m=int(radius_km * 1000),
                    limit=5000
                )
            elif hasattr(self.db, "search"):
                properties = self.db.search(
                    lat=center_lat,
                    lng=center_lng,
                    radius_m=int(radius_km * 1000),
                    limit=5000
                )
            elif hasattr(self.db, "get_all_properties"):
                properties = self.db.get_all_properties()
            properties = properties or []
            if not properties:
                return values
            
            cell_prices = defaultdict(list)
            
            for prop in properties:
                lat, lng = prop.get('latitude'), prop.get('longitude')
                price_sqft = prop.get('price_per_sqft', 0)
                
                if not lat or not lng or not price_sqft:
                    continue
                
                # Calculate cell
                row = int((bounds['north'] - lat) / lat_step)
                col = int((lng - bounds['west']) / lng_step)
                
                if 0 <= row < grid_size and 0 <= col < grid_size:
                    cell_prices[(row, col)].append(price_sqft)
            
            # Average prices per cell
            for (row, col), prices in cell_prices.items():
                values[row][col] = sum(prices) / len(prices)
            
            # Interpolate empty cells
            values = self._interpolate_grid(values)
            
        except Exception as e:
            print(f"[WARNING] Price heatmap generation failed: {e}")
        
        return values
    
    def _generate_infrastructure_heatmap(
        self,
        bounds: Dict[str, float],
        grid_size: int,
        lat_step: float,
        lng_step: float
    ) -> List[List[float]]:
        """Generate infrastructure density heatmap."""
        values = [[0.0 for _ in range(grid_size)] for _ in range(grid_size)]
        
        if not self.db:
            return self._synthetic_infrastructure_heatmap(bounds, grid_size)
        
        try:
            # Get POIs in bounds
            center_lat = (bounds['north'] + bounds['south']) / 2
            center_lng = (bounds['east'] + bounds['west']) / 2
            radius = max(
                (bounds['north'] - bounds['south']) * 111,
                (bounds['east'] - bounds['west']) * 111 * math.cos(math.radians(center_lat))
            ) / 2
            
            pois = self._get_pois_in_radius(center_lat, center_lng, radius)
            if not pois:
                return values
            
            # Count POIs per cell
            for poi in pois:
                lat, lng = poi.get('latitude'), poi.get('longitude')
                if not lat or not lng:
                    continue
                
                row = int((bounds['north'] - lat) / lat_step)
                col = int((lng - bounds['west']) / lng_step)
                
                if 0 <= row < grid_size and 0 <= col < grid_size:
                    values[row][col] += 1
            
        except Exception as e:
            print(f"[WARNING] Infrastructure heatmap generation failed: {e}")
        
        return values

    def _get_pois_in_radius(self, lat: float, lng: float, radius_km: float) -> List[Dict[str, Any]]:
        """Fetch nearby POIs with compatibility across DB services."""
        if not self.db:
            return []
        if hasattr(self.db, "get_pois_in_radius"):
            return self.db.get_pois_in_radius(lat=lat, lng=lng, radius_km=radius_km)
        if hasattr(self.db, "get_pois"):
            return self.db.get_pois(lat=lat, lng=lng, radius_m=int(radius_km * 1000), limit=2000)
        if hasattr(self.db, "get_all_pois"):
            pois = self.db.get_all_pois(limit=5000) or []
            center = (lat, lng)
            filtered = []
            for poi in pois:
                poi_lat = poi.get('lat') or poi.get('latitude')
                poi_lng = poi.get('lng') or poi.get('longitude')
                if poi_lat is None or poi_lng is None:
                    continue
                if self._haversine(center, (poi_lat, poi_lng)) <= radius_km:
                    filtered.append(poi)
            return filtered
        return []

    def _haversine(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate distance between two points in km."""
        lat1, lng1 = math.radians(p1[0]), math.radians(p1[1])
        lat2, lng2 = math.radians(p2[0]), math.radians(p2[1])
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        return 6371 * c
    
    def _generate_safety_heatmap(
        self,
        bounds: Dict[str, float],
        grid_size: int,
        lat_step: float,
        lng_step: float
    ) -> List[List[float]]:
        """Generate safety index heatmap."""
        # Safety scores would come from crime data, lighting, etc.
        # For now, use synthetic based on infrastructure
        infra = self._generate_infrastructure_heatmap(bounds, grid_size, lat_step, lng_step)
        
        # More infrastructure = safer (simplified model)
        values = [[0.0 for _ in range(grid_size)] for _ in range(grid_size)]
        max_infra = max(v for row in infra for v in row) or 1
        
        for i in range(grid_size):
            for j in range(grid_size):
                values[i][j] = 50 + (infra[i][j] / max_infra) * 50  # 50-100 scale
        
        return values
    
    def _generate_walkability_heatmap(
        self,
        bounds: Dict[str, float],
        grid_size: int,
        lat_step: float,
        lng_step: float
    ) -> List[List[float]]:
        """Generate walkability score heatmap."""
        infra = self._generate_infrastructure_heatmap(bounds, grid_size, lat_step, lng_step)
        
        # Walkability based on POI density (simplified)
        values = [[0.0 for _ in range(grid_size)] for _ in range(grid_size)]
        max_infra = max(v for row in infra for v in row) or 1
        
        for i in range(grid_size):
            for j in range(grid_size):
                values[i][j] = min(100, (infra[i][j] / max_infra) * 100)
        
        return values
    
    def _generate_generic_heatmap(
        self,
        bounds: Dict[str, float],
        grid_size: int,
        heatmap_type: HeatmapType
    ) -> List[List[float]]:
        """Generate a generic heatmap for unsupported types."""
        return self._synthetic_price_heatmap(bounds, grid_size)
    
    def _synthetic_price_heatmap(
        self,
        bounds: Dict[str, float],
        grid_size: int
    ) -> List[List[float]]:
        """Generate synthetic price data for demo."""
        values = [[0.0 for _ in range(grid_size)] for _ in range(grid_size)]
        
        # Create gradient with some variation
        center_row, center_col = grid_size // 2, grid_size // 2
        
        for i in range(grid_size):
            for j in range(grid_size):
                dist = math.sqrt((i - center_row)**2 + (j - center_col)**2)
                base_price = 8000 + 4000 * (1 - dist / (grid_size / 2))
                noise = np.random.normal(0, 500)
                values[i][j] = max(4000, base_price + noise)
        
        return values
    
    def _synthetic_infrastructure_heatmap(
        self,
        bounds: Dict[str, float],
        grid_size: int
    ) -> List[List[float]]:
        """Generate synthetic infrastructure density."""
        values = [[0.0 for _ in range(grid_size)] for _ in range(grid_size)]
        
        # Create clustered pattern
        for _ in range(5):
            cx, cy = np.random.randint(0, grid_size, 2)
            for i in range(grid_size):
                for j in range(grid_size):
                    dist = math.sqrt((i - cx)**2 + (j - cy)**2)
                    values[i][j] += max(0, 10 - dist)
        
        return values
    
    def _interpolate_grid(self, values: List[List[float]]) -> List[List[float]]:
        """Interpolate empty cells using neighbors."""
        grid_size = len(values)
        result = [row[:] for row in values]
        
        for i in range(grid_size):
            for j in range(grid_size):
                if values[i][j] == 0:
                    # Average of non-zero neighbors
                    neighbors = []
                    for di in [-1, 0, 1]:
                        for dj in [-1, 0, 1]:
                            ni, nj = i + di, j + dj
                            if 0 <= ni < grid_size and 0 <= nj < grid_size:
                                if values[ni][nj] > 0:
                                    neighbors.append(values[ni][nj])
                    if neighbors:
                        result[i][j] = sum(neighbors) / len(neighbors)
        
        return result
    
    def _generate_legend(
        self,
        heatmap_type: HeatmapType,
        min_val: float,
        max_val: float
    ) -> List[Dict[str, Any]]:
        """Generate legend entries for the heatmap."""
        colors = self.COLOR_SCHEMES.get(heatmap_type, ["#ffffff", "#0000ff"])
        steps = 5
        
        legend = []
        for i in range(steps):
            frac = i / (steps - 1)
            value = min_val + frac * (max_val - min_val)
            
            # Interpolate color
            if frac < 0.5:
                color = colors[0] if len(colors) < 2 else self._interpolate_color(
                    colors[0], colors[1] if len(colors) > 1 else colors[0], frac * 2
                )
            else:
                color = colors[-1] if len(colors) < 3 else self._interpolate_color(
                    colors[1] if len(colors) > 1 else colors[0],
                    colors[2] if len(colors) > 2 else colors[-1],
                    (frac - 0.5) * 2
                )
            
            legend.append({
                "value": value,
                "color": color,
                "label": f"{value:,.0f}"
            })
        
        return legend
    
    def _interpolate_color(self, c1: str, c2: str, t: float) -> str:
        """Interpolate between two hex colors."""
        r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
        r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
        
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def _get_unit(self, heatmap_type: HeatmapType) -> str:
        """Get unit label for heatmap type."""
        units = {
            HeatmapType.PRICE: "₹/sqft",
            HeatmapType.PRICE_GROWTH: "% annual",
            HeatmapType.SAFETY: "score",
            HeatmapType.INFRASTRUCTURE: "POIs",
            HeatmapType.WALKABILITY: "score",
            HeatmapType.INVESTMENT_SCORE: "score",
        }
        return units.get(heatmap_type, "")


class NeighborhoodSimilarity:
    """
    Find neighborhoods similar to a reference area.
    
    Uses multi-dimensional feature matching.
    """
    
    # Features and their weights for similarity calculation
    FEATURES = {
        "price_per_sqft": 0.2,
        "infrastructure_score": 0.15,
        "walkability_score": 0.1,
        "transport_connectivity": 0.15,
        "green_space_ratio": 0.1,
        "school_density": 0.1,
        "hospital_density": 0.05,
        "commercial_density": 0.1,
        "safety_index": 0.05,
    }
    
    def __init__(self, db_service=None):
        self.db = db_service
        self._locality_features: Dict[str, Dict[str, float]] = {}
    
    def find_similar(
        self,
        reference_location: str,
        max_results: int = 10,
        price_filter: Optional[str] = None  # "cheaper", "similar", "any"
    ) -> List[SimilarityMatch]:
        """
        Find neighborhoods similar to the reference.
        
        Args:
            reference_location: Name of reference locality
            max_results: Maximum matches to return
            price_filter: Filter by price ("cheaper", "similar", "any")
        
        Returns:
            List of similar neighborhoods ranked by similarity
        """
        # Get reference features
        ref_features = self._get_locality_features(reference_location)
        if not ref_features:
            return []
        
        # Get all localities
        all_localities = self._get_all_localities()
        
        matches = []
        for locality in all_localities:
            if locality.lower() == reference_location.lower():
                continue
            
            features = self._get_locality_features(locality)
            if not features:
                continue
            
            # Calculate similarity
            similarity = self._calculate_similarity(ref_features, features)
            
            # Price difference
            ref_price = ref_features.get("price_per_sqft", 0)
            loc_price = features.get("price_per_sqft", 0)
            price_diff_pct = ((loc_price - ref_price) / ref_price * 100) if ref_price else 0
            
            # Apply price filter
            if price_filter == "cheaper" and price_diff_pct >= 0:
                continue
            elif price_filter == "similar" and abs(price_diff_pct) > 20:
                continue
            
            # Identify matching and differing features
            matching, differing = self._compare_features(ref_features, features)
            
            matches.append(SimilarityMatch(
                location_name=locality,
                lat=features.get("lat", 0),
                lng=features.get("lng", 0),
                similarity_score=similarity,
                price_difference_pct=price_diff_pct,
                matching_features=matching,
                differing_features=differing,
                metrics=features
            ))
        
        # Sort by similarity (descending)
        matches.sort(key=lambda m: -m.similarity_score)
        
        return matches[:max_results]
    
    def _get_locality_features(self, locality: str) -> Dict[str, float]:
        """Get feature vector for a locality."""
        if locality in self._locality_features:
            return self._locality_features[locality]
        
        features = {}
        
        if self.db:
            try:
                # Get area analysis
                analysis = self._get_area_analysis(locality)
                if analysis:
                    features["price_per_sqft"] = analysis.get("avg_price_per_sqft", 0)
                    features["infrastructure_score"] = analysis.get("infrastructure_score", 50)
                    features["walkability_score"] = analysis.get("walkability_score", 50)
                    features["transport_connectivity"] = analysis.get("transport_score", 50)
                    features["safety_index"] = analysis.get("safety_index", 50)
                    features["lat"] = analysis.get("lat", 12.97)
                    features["lng"] = analysis.get("lng", 77.59)
                
                # Get POI counts
                pois = self._get_poi_counts_by_category(locality)
                if pois:
                    features["school_density"] = pois.get("school", 0)
                    features["hospital_density"] = pois.get("hospital", 0)
                    features["commercial_density"] = pois.get("commercial", 0)
                    features["green_space_ratio"] = pois.get("park", 0)
                
            except Exception as e:
                print(f"[WARNING] Failed to get features for {locality}: {e}")
        
        # Use defaults for missing features
        for feature in self.FEATURES:
            if feature not in features:
                features[feature] = 50.0  # Default score
        
        self._locality_features[locality] = features
        return features

    def _get_area_analysis(self, locality: str) -> Dict[str, Any]:
        """Fetch area analysis with compatibility across DB services."""
        if not self.db:
            return {}
        if hasattr(self.db, "get_area_analysis"):
            return self.db.get_area_analysis(locality) or {}
        # Fallback: compute from nearby properties
        center = self._get_locality_center(locality)
        if center[0] is None or center[1] is None:
            return {}
        if hasattr(self.db, "search_properties"):
            props = self.db.search_properties(lat=center[0], lng=center[1], radius_m=2000, limit=500) or []
        elif hasattr(self.db, "search"):
            props = self.db.search(lat=center[0], lng=center[1], radius_m=2000, limit=500) or []
        else:
            props = []
        prices = [p.get('price_per_sqft') or p.get('price_per_sq_ft') for p in props if (p.get('price_per_sqft') or p.get('price_per_sq_ft'))]
        avg_price = sum(prices) / len(prices) if prices else 0
        return {
            "avg_price_per_sqft": avg_price,
            "property_count": len(props),
            "lat": center[0],
            "lng": center[1],
        }

    def _get_poi_counts_by_category(self, locality: str) -> Dict[str, int]:
        """Fetch POI counts with compatibility across DB services."""
        if not self.db:
            return {}
        if hasattr(self.db, "get_poi_counts_by_category"):
            return self.db.get_poi_counts_by_category(locality) or {}
        center = self._get_locality_center(locality)
        if center[0] is None or center[1] is None:
            return {}
        pois = []
        if hasattr(self.db, "get_pois"):
            pois = self.db.get_pois(lat=center[0], lng=center[1], radius_m=1500, limit=2000) or []
        elif hasattr(self.db, "get_all_pois"):
            pois = self.db.get_all_pois(limit=5000) or []
        counts: Dict[str, int] = {}
        for poi in pois:
            category = (poi.get('category') or 'other').lower()
            counts[category] = counts.get(category, 0) + 1
        return counts
    
    def _get_all_localities(self) -> List[str]:
        """Get list of all localities."""
        if self.db:
            try:
                places = self.db.get_all_places()
                if places:
                    return [p.get("name") for p in places if p.get("name")]
            except:
                pass
        
        # Default Bangalore localities
        return [
            "Koramangala", "Indiranagar", "Whitefield", "HSR Layout",
            "Jayanagar", "JP Nagar", "BTM Layout", "Electronic City",
            "Marathahalli", "Sarjapur", "Bellandur", "Hebbal",
            "Yelahanka", "Bannerghatta", "Rajajinagar", "Malleswaram"
        ]
    
    def _calculate_similarity(
        self,
        ref: Dict[str, float],
        other: Dict[str, float]
    ) -> float:
        """Calculate weighted similarity score (0-1)."""
        total_weight = 0
        weighted_similarity = 0
        
        for feature, weight in self.FEATURES.items():
            ref_val = ref.get(feature, 0)
            other_val = other.get(feature, 0)
            
            if ref_val == 0 and other_val == 0:
                continue
            
            # Normalize difference
            max_val = max(abs(ref_val), abs(other_val), 1)
            diff_ratio = abs(ref_val - other_val) / max_val
            
            # Convert to similarity (1 = identical)
            feature_similarity = 1 - min(diff_ratio, 1)
            
            weighted_similarity += weight * feature_similarity
            total_weight += weight
        
        return weighted_similarity / total_weight if total_weight > 0 else 0
    
    def _compare_features(
        self,
        ref: Dict[str, float],
        other: Dict[str, float]
    ) -> Tuple[List[str], List[str]]:
        """Identify matching and differing features."""
        matching = []
        differing = []
        
        feature_names = {
            "price_per_sqft": "Price",
            "infrastructure_score": "Infrastructure",
            "walkability_score": "Walkability",
            "transport_connectivity": "Transport",
            "green_space_ratio": "Green spaces",
            "school_density": "Schools",
            "hospital_density": "Healthcare",
            "commercial_density": "Commercial",
            "safety_index": "Safety",
        }
        
        for feature in self.FEATURES:
            ref_val = ref.get(feature, 0)
            other_val = other.get(feature, 0)
            
            name = feature_names.get(feature, feature)
            
            if ref_val == 0 and other_val == 0:
                continue
            
            diff_pct = abs(ref_val - other_val) / max(ref_val, other_val, 1) * 100
            
            if diff_pct < 20:
                matching.append(name)
            else:
                direction = "higher" if other_val > ref_val else "lower"
                differing.append(f"{name} ({direction})")
        
        return matching, differing


class InfrastructureImpactPredictor:
    """
    Predict property value changes from planned infrastructure.
    
    Uses historical patterns and distance-based decay models.
    """
    
    # Impact factors by infrastructure type (% increase at distance 0)
    IMPACT_FACTORS = {
        "metro_station": {"max_impact": 25, "decay_km": 2.0},
        "metro_line": {"max_impact": 15, "decay_km": 1.5},
        "highway": {"max_impact": 10, "decay_km": 3.0},
        "airport": {"max_impact": 20, "decay_km": 10.0},
        "it_park": {"max_impact": 18, "decay_km": 3.0},
        "shopping_mall": {"max_impact": 8, "decay_km": 1.0},
        "hospital": {"max_impact": 5, "decay_km": 1.5},
        "school": {"max_impact": 3, "decay_km": 0.5},
        "park": {"max_impact": 4, "decay_km": 0.8},
    }
    
    # Planned infrastructure in Bangalore (sample data)
    PLANNED_INFRASTRUCTURE = [
        {
            "type": "metro_station",
            "name": "Sarjapur Road Metro",
            "lat": 12.9106,
            "lng": 77.6872,
            "completion_year": 2026,
        },
        {
            "type": "metro_line",
            "name": "Yellow Line Extension",
            "lat": 12.9352,
            "lng": 77.6245,
            "completion_year": 2027,
        },
        {
            "type": "it_park",
            "name": "Tech Park Devanahalli",
            "lat": 13.2356,
            "lng": 77.7128,
            "completion_year": 2025,
        },
    ]
    
    def __init__(self, db_service=None):
        self.db = db_service
    
    def predict_impact(
        self,
        location: Tuple[float, float],
        years_ahead: int = 5
    ) -> List[InfrastructureImpact]:
        """
        Predict infrastructure impact on a location.
        
        Args:
            location: (lat, lng) of the property/area
            years_ahead: How far to look into the future
        
        Returns:
            List of predicted impacts
        """
        current_year = 2026  # Assuming current year
        impacts = []
        
        for infra in self.PLANNED_INFRASTRUCTURE:
            if infra["completion_year"] > current_year + years_ahead:
                continue
            
            infra_location = (infra["lat"], infra["lng"])
            distance_km = self._haversine(location, infra_location)
            
            factors = self.IMPACT_FACTORS.get(infra["type"], {})
            max_impact = factors.get("max_impact", 5)
            decay_km = factors.get("decay_km", 2.0)
            
            # Calculate impact with distance decay
            impact_pct = max_impact * math.exp(-distance_km / decay_km)
            
            if impact_pct < 1:  # Less than 1% impact, skip
                continue
            
            # Find affected localities
            affected = self._find_affected_localities(
                infra_location, decay_km * 2
            )
            
            # Confidence based on completion timeline
            years_to_completion = infra["completion_year"] - current_year
            confidence = max(0.5, 1 - years_to_completion * 0.1)
            
            impacts.append(InfrastructureImpact(
                infrastructure_type=infra["type"],
                location=infra_location,
                completion_year=infra["completion_year"],
                affected_radius_km=decay_km * 2,
                predicted_price_impact_pct=round(impact_pct, 1),
                affected_localities=affected,
                confidence=confidence
            ))
        
        # Sort by impact (descending)
        impacts.sort(key=lambda x: -x.predicted_price_impact_pct)
        
        return impacts
    
    def get_area_future_value(
        self,
        locality: str,
        years_ahead: int = 5
    ) -> Dict[str, Any]:
        """
        Estimate future value change for an area.
        
        Returns aggregated impact from all planned infrastructure.
        """
        # Get locality center
        lat, lng = self._get_locality_center(locality)
        if lat is None:
            return {"error": f"Unknown locality: {locality}"}
        
        impacts = self.predict_impact((lat, lng), years_ahead)
        
        # Aggregate impacts (with diminishing returns)
        total_impact = 0
        for i, impact in enumerate(impacts):
            # Each additional factor has diminishing effect
            factor = 1 / (1 + i * 0.3)
            total_impact += impact.predicted_price_impact_pct * factor
        
        # Cap at reasonable maximum
        total_impact = min(total_impact, 50)
        
        return {
            "locality": locality,
            "current_analysis": "pending",
            "infrastructure_impacts": [
                {
                    "type": i.infrastructure_type,
                    "impact_pct": i.predicted_price_impact_pct,
                    "year": i.completion_year,
                    "confidence": i.confidence,
                }
                for i in impacts[:5]
            ],
            "total_predicted_appreciation_pct": round(total_impact, 1),
            "confidence": sum(i.confidence for i in impacts) / len(impacts) if impacts else 0,
            "years_ahead": years_ahead,
        }
    
    def _haversine(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate distance between two points in km."""
        lat1, lng1 = math.radians(p1[0]), math.radians(p1[1])
        lat2, lng2 = math.radians(p2[0]), math.radians(p2[1])
        
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return 6371 * c
    
    def _find_affected_localities(
        self,
        center: Tuple[float, float],
        radius_km: float
    ) -> List[str]:
        """Find localities within radius of infrastructure."""
        affected = []
        
        # Sample locality coordinates
        localities = {
            "Koramangala": (12.9352, 77.6245),
            "Indiranagar": (12.9784, 77.6408),
            "Whitefield": (12.9698, 77.7500),
            "HSR Layout": (12.9116, 77.6389),
            "Sarjapur": (12.8587, 77.7861),
            "Bellandur": (12.9260, 77.6762),
            "Marathahalli": (12.9591, 77.6974),
        }
        
        for name, coords in localities.items():
            if self._haversine(center, coords) <= radius_km:
                affected.append(name)
        
        return affected
    
    def _get_locality_center(self, locality: str) -> Tuple[Optional[float], Optional[float]]:
        """Get center coordinates for a locality."""
        # Sample coordinates
        coords = {
            "koramangala": (12.9352, 77.6245),
            "indiranagar": (12.9784, 77.6408),
            "whitefield": (12.9698, 77.7500),
            "hsr layout": (12.9116, 77.6389),
            "sarjapur": (12.8587, 77.7861),
            "bellandur": (12.9260, 77.6762),
            "marathahalli": (12.9591, 77.6974),
            "electronic city": (12.8399, 77.6770),
            "hebbal": (13.0358, 77.5970),
            "jayanagar": (12.9308, 77.5838),
        }
        
        return coords.get(locality.lower(), (None, None))


# Convenience functions
def get_isochrone_calculator(db_service=None) -> IsochroneCalculator:
    return IsochroneCalculator(db_service)


def get_heatmap_generator(db_service=None) -> HeatmapGenerator:
    return HeatmapGenerator(db_service)


def get_neighborhood_similarity(db_service=None) -> NeighborhoodSimilarity:
    return NeighborhoodSimilarity(db_service)


def get_infrastructure_predictor(db_service=None) -> InfrastructureImpactPredictor:
    return InfrastructureImpactPredictor(db_service)
