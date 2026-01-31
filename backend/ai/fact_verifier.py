"""
Valora AI - Fact Verifier Service
Verifies LLM claims against deterministic agents and data sources.

The Fact Verifier is the "truth firewall" that ensures LLM outputs are grounded in data.

Claim Types:
- price: Price per sqft, property values, price ranges
- distance: Distances to landmarks, metros, POIs
- count: POI counts, property counts, listing counts
- percentage: Growth rates, trends, scores
- spatial: View quality, shadow impact, sunlight hours
- simulation: Scenario impacts, projections
- zoning: FAR limits, zone types, regulatory info

Flow:
1. LLM generates narrative with embedded claims
2. Claims are extracted and sent to verifier
3. Verifier checks each claim against deterministic agents
4. Returns verified/unverified status with evidence
5. Frontend shows verified badge or warning
"""

import re
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

# Import deterministic agents for verification
try:
    from utils.geo import haversine_distance
except ImportError:
    from utils.geo import haversine_distance


class ClaimType(Enum):
    """Types of verifiable claims."""
    PRICE = "price"
    DISTANCE = "distance"
    COUNT = "count"
    PERCENTAGE = "percentage"
    SPATIAL = "spatial"
    SUNLIGHT = "sunlight"
    VIEW = "view"
    SIMULATION = "simulation"
    ZONING = "zoning"
    GENERAL = "general"


class VerificationStatus(Enum):
    """Verification result status."""
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    PARTIALLY_VERIFIED = "partially_verified"
    UNABLE_TO_VERIFY = "unable_to_verify"
    ERROR = "error"


@dataclass
class Claim:
    """A single claim to be verified."""
    claim_id: str
    claim_text: str
    claim_type: str
    value: Optional[Any] = None  # Extracted numeric/string value
    unit: Optional[str] = None  # e.g., "sqft", "meters", "%"
    location: Optional[Dict[str, float]] = None  # lat, lng
    property_id: Optional[str] = None
    locality: Optional[str] = None
    context: Optional[Dict[str, Any]] = None  # Additional context


@dataclass
class Evidence:
    """Evidence supporting or contradicting a claim."""
    source: str  # "database", "spatial_engine", "solar_engine", etc.
    query_type: str  # What was queried
    actual_value: Any
    expected_value: Any
    tolerance: float = 0.1  # 10% tolerance by default
    match: bool = False
    details: Optional[Dict[str, Any]] = None


@dataclass
class VerificationResult:
    """Result of verifying a single claim."""
    claim_id: str
    claim_text: str
    status: str
    confidence: float  # 0-100
    evidence: List[Evidence] = field(default_factory=list)
    rewrite_suggestion: Optional[str] = None
    verified_at: str = ""
    
    def __post_init__(self):
        if not self.verified_at:
            self.verified_at = datetime.now().isoformat()


@dataclass
class VerifierResponse:
    """Complete response from the verifier."""
    request_id: str
    overall_status: str
    total_claims: int
    verified_count: int
    unverified_count: int
    results: List[VerificationResult] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    @property
    def verification_rate(self) -> float:
        if self.total_claims == 0:
            return 0
        return (self.verified_count / self.total_claims) * 100


class FactVerifier:
    """
    Verifies LLM claims against deterministic data sources.
    
    This is the core "truth firewall" for Valora AI.
    """
    
    # Tolerance levels by claim type
    TOLERANCES = {
        ClaimType.PRICE.value: 0.15,       # 15% tolerance for prices
        ClaimType.DISTANCE.value: 0.20,    # 20% tolerance for distances
        ClaimType.COUNT.value: 0.10,       # 10% tolerance for counts
        ClaimType.PERCENTAGE.value: 0.25,  # 25% tolerance for percentages
        ClaimType.SPATIAL.value: 0.20,     # 20% tolerance for spatial
        ClaimType.SUNLIGHT.value: 0.15,    # 15% tolerance for sunlight
        ClaimType.VIEW.value: 0.30,        # 30% tolerance for subjective view
    }
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / 'src' / 'data' / 'valora.db'
        self.db_path = str(db_path)
        
        # Lazy-load agents
        self._property_service = None
        self._spatial_3d = None
        self._occlusion = None
        self._solar = None
        self._regulatory = None
        self._transaction = None
    
    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _get_property_service(self):
        if self._property_service is None:
            try:
                from property_service import PropertyService
                self._property_service = PropertyService()
            except ImportError:
                pass
        return self._property_service
    
    def _get_spatial_3d(self):
        if self._spatial_3d is None:
            try:
                from spatial_3d_reasoning import get_spatial_3d_reasoning
                self._spatial_3d = get_spatial_3d_reasoning()
            except ImportError:
                pass
        return self._spatial_3d
    
    def _get_occlusion(self):
        if self._occlusion is None:
            try:
                from occlusion_engine import get_occlusion_engine
                self._occlusion = get_occlusion_engine()
            except ImportError:
                pass
        return self._occlusion
    
    def _get_solar(self):
        if self._solar is None:
            try:
                from solar_engine import get_solar_engine
                self._solar = get_solar_engine()
            except ImportError:
                pass
        return self._solar
    
    def _get_regulatory(self):
        if self._regulatory is None:
            try:
                from regulatory_intelligence import get_regulatory_intelligence
                self._regulatory = get_regulatory_intelligence()
            except ImportError:
                pass
        return self._regulatory
    
    def _get_transaction(self):
        if self._transaction is None:
            try:
                from transaction_intelligence import get_transaction_intelligence
                self._transaction = get_transaction_intelligence()
            except ImportError:
                pass
        return self._transaction
    
    def _within_tolerance(self, actual: float, expected: float, tolerance: float) -> bool:
        """Check if actual value is within tolerance of expected."""
        if expected == 0:
            return actual == 0
        diff_pct = abs(actual - expected) / abs(expected)
        return diff_pct <= tolerance
    
    def _verify_price_claim(self, claim: Claim) -> VerificationResult:
        """Verify price-related claims."""
        result = VerificationResult(
            claim_id=claim.claim_id,
            claim_text=claim.claim_text,
            status=VerificationStatus.UNABLE_TO_VERIFY.value,
            confidence=0
        )
        
        if not claim.location:
            result.rewrite_suggestion = "Specify location for price verification"
            return result
        
        lat = claim.location.get('lat')
        lng = claim.location.get('lng')
        
        if not lat or not lng:
            return result
        
        # Get actual price data from database
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            radius_deg = 2000 / 111000  # 2km radius
            
            cursor.execute("""
                SELECT AVG(price / NULLIF(total_area_sqft, 0)) as avg_ppsf,
                       COUNT(*) as count
                FROM properties
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
                AND price > 0 AND total_area_sqft > 0
            """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
            
            row = cursor.fetchone()
            conn.close()
            
            if row and row['avg_ppsf'] and row['count'] > 3:
                actual_ppsf = row['avg_ppsf']
                expected = claim.value
                
                if expected:
                    tolerance = self.TOLERANCES[ClaimType.PRICE.value]
                    match = self._within_tolerance(actual_ppsf, expected, tolerance)
                    
                    evidence = Evidence(
                        source="database",
                        query_type="avg_price_per_sqft",
                        actual_value=round(actual_ppsf, 0),
                        expected_value=expected,
                        tolerance=tolerance,
                        match=match,
                        details={"sample_size": row['count']}
                    )
                    result.evidence.append(evidence)
                    
                    if match:
                        result.status = VerificationStatus.VERIFIED.value
                        result.confidence = min(95, 60 + row['count'])
                    else:
                        result.status = VerificationStatus.UNVERIFIED.value
                        result.confidence = min(90, 50 + row['count'])
                        result.rewrite_suggestion = f"Actual avg price/sqft is ₹{actual_ppsf:,.0f}, not ₹{expected:,.0f}"
                        
        except Exception as e:
            result.status = VerificationStatus.ERROR.value
            result.warnings = [str(e)]
        
        return result
    
    def _verify_distance_claim(self, claim: Claim) -> VerificationResult:
        """Verify distance-related claims."""
        result = VerificationResult(
            claim_id=claim.claim_id,
            claim_text=claim.claim_text,
            status=VerificationStatus.UNABLE_TO_VERIFY.value,
            confidence=0
        )
        
        if not claim.location:
            result.rewrite_suggestion = "Specify location for distance verification"
            return result
        
        lat = claim.location.get('lat')
        lng = claim.location.get('lng')
        
        if not lat or not lng:
            return result
        
        # Extract target from claim context
        target_type = claim.context.get('target_type', 'metro') if claim.context else 'metro'
        
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Find nearest POI of target type
            cursor.execute("""
                SELECT name, latitude, longitude, category
                FROM pois
                WHERE category LIKE ?
                AND latitude IS NOT NULL
                ORDER BY ABS(latitude - ?) + ABS(longitude - ?)
                LIMIT 1
            """, (f"%{target_type}%", lat, lng))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                actual_distance = haversine_distance(lat, lng, row['latitude'], row['longitude'])
                expected = claim.value
                
                if expected:
                    tolerance = self.TOLERANCES[ClaimType.DISTANCE.value]
                    match = self._within_tolerance(actual_distance, expected, tolerance)
                    
                    evidence = Evidence(
                        source="database",
                        query_type=f"nearest_{target_type}_distance",
                        actual_value=round(actual_distance, 0),
                        expected_value=expected,
                        tolerance=tolerance,
                        match=match,
                        details={"nearest_name": row['name']}
                    )
                    result.evidence.append(evidence)
                    
                    if match:
                        result.status = VerificationStatus.VERIFIED.value
                        result.confidence = 85
                    else:
                        result.status = VerificationStatus.UNVERIFIED.value
                        result.confidence = 80
                        result.rewrite_suggestion = f"Actual distance to {row['name']} is {actual_distance:.0f}m, not {expected}m"
                        
        except Exception as e:
            result.status = VerificationStatus.ERROR.value
            result.warnings = [str(e)]
        
        return result
    
    def _verify_count_claim(self, claim: Claim) -> VerificationResult:
        """Verify count-related claims (POIs, properties, etc.)."""
        result = VerificationResult(
            claim_id=claim.claim_id,
            claim_text=claim.claim_text,
            status=VerificationStatus.UNABLE_TO_VERIFY.value,
            confidence=0
        )
        
        if not claim.location:
            return result
        
        lat = claim.location.get('lat')
        lng = claim.location.get('lng')
        
        if not lat or not lng:
            return result
        
        count_type = claim.context.get('count_type', 'pois') if claim.context else 'pois'
        radius = claim.context.get('radius_m', 1000) if claim.context else 1000
        
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            radius_deg = radius / 111000
            
            if count_type == 'pois':
                cursor.execute("""
                    SELECT COUNT(*) as cnt
                    FROM pois
                    WHERE latitude BETWEEN ? AND ?
                    AND longitude BETWEEN ? AND ?
                """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
            elif count_type == 'properties':
                cursor.execute("""
                    SELECT COUNT(*) as cnt
                    FROM properties
                    WHERE latitude BETWEEN ? AND ?
                    AND longitude BETWEEN ? AND ?
                """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
            else:
                cursor.execute("""
                    SELECT COUNT(*) as cnt
                    FROM buildings
                    WHERE latitude BETWEEN ? AND ?
                    AND longitude BETWEEN ? AND ?
                """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                actual_count = row['cnt']
                expected = claim.value
                
                if expected:
                    tolerance = self.TOLERANCES[ClaimType.COUNT.value]
                    match = self._within_tolerance(actual_count, expected, tolerance)
                    
                    evidence = Evidence(
                        source="database",
                        query_type=f"{count_type}_count",
                        actual_value=actual_count,
                        expected_value=expected,
                        tolerance=tolerance,
                        match=match,
                        details={"radius_m": radius}
                    )
                    result.evidence.append(evidence)
                    
                    if match:
                        result.status = VerificationStatus.VERIFIED.value
                        result.confidence = 90
                    else:
                        result.status = VerificationStatus.UNVERIFIED.value
                        result.confidence = 85
                        result.rewrite_suggestion = f"Actual {count_type} count is {actual_count}, not {expected}"
                        
        except Exception as e:
            result.status = VerificationStatus.ERROR.value
            result.warnings = [str(e)]
        
        return result
    
    def _verify_spatial_claim(self, claim: Claim) -> VerificationResult:
        """Verify spatial claims (view quality, sky view factor, etc.)."""
        result = VerificationResult(
            claim_id=claim.claim_id,
            claim_text=claim.claim_text,
            status=VerificationStatus.UNABLE_TO_VERIFY.value,
            confidence=0
        )
        
        if not claim.location:
            return result
        
        lat = claim.location.get('lat')
        lng = claim.location.get('lng')
        floor = claim.context.get('floor', 5) if claim.context else 5
        
        spatial_3d = self._get_spatial_3d()
        if not spatial_3d:
            result.rewrite_suggestion = "Spatial analysis service unavailable"
            return result
        
        try:
            analysis = spatial_3d.analyze_3d_context(lat, lng, floor * 3, radius_m=200)
            
            # Check view quality claim
            if 'view' in claim.claim_text.lower():
                actual_quality = analysis.view_quality
                expected_quality = claim.value if isinstance(claim.value, str) else None
                
                if expected_quality:
                    match = actual_quality.lower() == expected_quality.lower()
                    
                    evidence = Evidence(
                        source="spatial_3d_reasoning",
                        query_type="view_quality",
                        actual_value=actual_quality,
                        expected_value=expected_quality,
                        match=match,
                        details={"floor": floor, "sky_view_factor": analysis.sky_view_factor}
                    )
                    result.evidence.append(evidence)
                    
                    if match:
                        result.status = VerificationStatus.VERIFIED.value
                        result.confidence = 80
                    else:
                        result.status = VerificationStatus.UNVERIFIED.value
                        result.confidence = 75
                        result.rewrite_suggestion = f"Actual view quality is '{actual_quality}', not '{expected_quality}'"
                        
        except Exception as e:
            result.status = VerificationStatus.ERROR.value
            result.warnings = [str(e)]
        
        return result
    
    def _verify_sunlight_claim(self, claim: Claim) -> VerificationResult:
        """Verify sunlight-related claims."""
        result = VerificationResult(
            claim_id=claim.claim_id,
            claim_text=claim.claim_text,
            status=VerificationStatus.UNABLE_TO_VERIFY.value,
            confidence=0
        )
        
        if not claim.location:
            return result
        
        lat = claim.location.get('lat')
        lng = claim.location.get('lng')
        floor = claim.context.get('floor', 5) if claim.context else 5
        
        solar = self._get_solar()
        if not solar:
            result.rewrite_suggestion = "Solar analysis service unavailable"
            return result
        
        try:
            analysis = solar.analyze_sunlight(lat, lng, floor=floor)
            
            # Check daylight hours claim
            if 'hour' in claim.claim_text.lower() and claim.value:
                actual_hours = analysis.daylight_hours
                expected_hours = claim.value
                
                tolerance = self.TOLERANCES[ClaimType.SUNLIGHT.value]
                match = self._within_tolerance(actual_hours, expected_hours, tolerance)
                
                evidence = Evidence(
                    source="solar_engine",
                    query_type="daylight_hours",
                    actual_value=round(actual_hours, 1),
                    expected_value=expected_hours,
                    tolerance=tolerance,
                    match=match,
                    details={"floor": floor, "natural_light_score": analysis.natural_light_score}
                )
                result.evidence.append(evidence)
                
                if match:
                    result.status = VerificationStatus.VERIFIED.value
                    result.confidence = 85
                else:
                    result.status = VerificationStatus.UNVERIFIED.value
                    result.confidence = 80
                    result.rewrite_suggestion = f"Actual daylight hours is {actual_hours:.1f}h, not {expected_hours}h"
                    
        except Exception as e:
            result.status = VerificationStatus.ERROR.value
            result.warnings = [str(e)]
        
        return result
    
    def _verify_zoning_claim(self, claim: Claim) -> VerificationResult:
        """Verify zoning and regulatory claims."""
        result = VerificationResult(
            claim_id=claim.claim_id,
            claim_text=claim.claim_text,
            status=VerificationStatus.UNABLE_TO_VERIFY.value,
            confidence=0
        )
        
        if not claim.location:
            return result
        
        lat = claim.location.get('lat')
        lng = claim.location.get('lng')
        
        regulatory = self._get_regulatory()
        if not regulatory:
            result.rewrite_suggestion = "Regulatory service unavailable"
            return result
        
        try:
            zoning = regulatory.get_zoning(lat, lng)
            
            # Check FAR claim
            if 'far' in claim.claim_text.lower() and claim.value:
                actual_far = zoning.max_far
                expected_far = claim.value
                
                tolerance = 0.1  # 10% for FAR
                match = self._within_tolerance(actual_far, expected_far, tolerance)
                
                evidence = Evidence(
                    source="regulatory_intelligence",
                    query_type="max_far",
                    actual_value=actual_far,
                    expected_value=expected_far,
                    tolerance=tolerance,
                    match=match,
                    details={"zone_type": zoning.zone_type}
                )
                result.evidence.append(evidence)
                
                if match:
                    result.status = VerificationStatus.VERIFIED.value
                    result.confidence = 90
                else:
                    result.status = VerificationStatus.UNVERIFIED.value
                    result.confidence = 85
                    result.rewrite_suggestion = f"Actual max FAR is {actual_far}, not {expected_far}"
            
            # Check zone type claim
            elif 'zone' in claim.claim_text.lower() and claim.value:
                actual_zone = zoning.zone_type
                expected_zone = claim.value
                
                match = actual_zone.lower() == str(expected_zone).lower()
                
                evidence = Evidence(
                    source="regulatory_intelligence",
                    query_type="zone_type",
                    actual_value=actual_zone,
                    expected_value=expected_zone,
                    match=match
                )
                result.evidence.append(evidence)
                
                if match:
                    result.status = VerificationStatus.VERIFIED.value
                    result.confidence = 90
                else:
                    result.status = VerificationStatus.UNVERIFIED.value
                    result.confidence = 85
                    result.rewrite_suggestion = f"Actual zone type is '{actual_zone}', not '{expected_zone}'"
                    
        except Exception as e:
            result.status = VerificationStatus.ERROR.value
            result.warnings = [str(e)]
        
        return result
    
    def verify_claim(self, claim: Claim) -> VerificationResult:
        """
        Verify a single claim.
        
        Routes to appropriate verification method based on claim type.
        """
        claim_type = claim.claim_type
        
        if claim_type == ClaimType.PRICE.value:
            return self._verify_price_claim(claim)
        elif claim_type == ClaimType.DISTANCE.value:
            return self._verify_distance_claim(claim)
        elif claim_type == ClaimType.COUNT.value:
            return self._verify_count_claim(claim)
        elif claim_type == ClaimType.SPATIAL.value or claim_type == ClaimType.VIEW.value:
            return self._verify_spatial_claim(claim)
        elif claim_type == ClaimType.SUNLIGHT.value:
            return self._verify_sunlight_claim(claim)
        elif claim_type == ClaimType.ZONING.value:
            return self._verify_zoning_claim(claim)
        else:
            return VerificationResult(
                claim_id=claim.claim_id,
                claim_text=claim.claim_text,
                status=VerificationStatus.UNABLE_TO_VERIFY.value,
                confidence=0,
                rewrite_suggestion=f"Unknown claim type: {claim_type}"
            )
    
    def verify_claims(self, claims: List[Claim], request_id: str = None) -> VerifierResponse:
        """
        Verify multiple claims and return aggregated response.
        
        Args:
            claims: List of claims to verify
            request_id: Optional request ID for tracking
            
        Returns:
            VerifierResponse with all results
        """
        if request_id is None:
            request_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        results = []
        verified_count = 0
        unverified_count = 0
        warnings = []
        
        for claim in claims:
            result = self.verify_claim(claim)
            results.append(result)
            
            if result.status == VerificationStatus.VERIFIED.value:
                verified_count += 1
            elif result.status == VerificationStatus.UNVERIFIED.value:
                unverified_count += 1
            
            if hasattr(result, 'warnings') and result.warnings:
                warnings.extend(result.warnings)
        
        # Determine overall status
        total = len(claims)
        if verified_count == total:
            overall_status = VerificationStatus.VERIFIED.value
        elif unverified_count == total:
            overall_status = VerificationStatus.UNVERIFIED.value
        elif verified_count > 0 and unverified_count > 0:
            overall_status = VerificationStatus.PARTIALLY_VERIFIED.value
        else:
            overall_status = VerificationStatus.UNABLE_TO_VERIFY.value
        
        return VerifierResponse(
            request_id=request_id,
            overall_status=overall_status,
            total_claims=total,
            verified_count=verified_count,
            unverified_count=unverified_count,
            results=results,
            warnings=warnings
        )
    
    def extract_claims_from_text(self, text: str, location: Dict[str, float] = None) -> List[Claim]:
        """
        Extract verifiable claims from narrative text.
        
        This is a simple pattern-based extraction. In production, you might use
        an LLM to identify claims more accurately.
        
        Args:
            text: Narrative text containing claims
            location: Default location context
            
        Returns:
            List of extracted claims
        """
        claims = []
        claim_id = 0
        
        # Price patterns: ₹X,XXX per sqft, ₹X lakhs, etc.
        price_patterns = [
            (r'₹\s*([\d,]+)\s*(?:per|/)\s*sq\s*ft', 'price_per_sqft'),
            (r'₹\s*([\d,]+)\s*(?:per|/)\s*sqft', 'price_per_sqft'),
            (r'([\d,]+)\s*(?:per|/)\s*sq\s*ft', 'price_per_sqft'),
            (r'price.*?₹\s*([\d,]+)', 'price'),
        ]
        
        for pattern, ptype in price_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                value_str = match.group(1).replace(',', '')
                try:
                    value = float(value_str)
                    claims.append(Claim(
                        claim_id=f"c_{claim_id}",
                        claim_text=match.group(0),
                        claim_type=ClaimType.PRICE.value,
                        value=value,
                        unit="sqft" if "sqft" in ptype else "rupees",
                        location=location
                    ))
                    claim_id += 1
                except ValueError:
                    pass
        
        # Distance patterns: X meters, X km, Xm from
        distance_patterns = [
            (r'(\d+)\s*(?:m|meters?)\s*(?:from|to|away)', 'meters'),
            (r'(\d+(?:\.\d+)?)\s*km\s*(?:from|to|away)', 'km'),
            (r'within\s*(\d+)\s*(?:m|meters?)', 'meters'),
        ]
        
        for pattern, unit in distance_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    value = float(match.group(1))
                    if unit == 'km':
                        value *= 1000
                    claims.append(Claim(
                        claim_id=f"c_{claim_id}",
                        claim_text=match.group(0),
                        claim_type=ClaimType.DISTANCE.value,
                        value=value,
                        unit="meters",
                        location=location
                    ))
                    claim_id += 1
                except ValueError:
                    pass
        
        # Count patterns: X POIs, X properties, etc.
        count_patterns = [
            (r'(\d+)\s*(?:POIs?|amenities)', 'pois'),
            (r'(\d+)\s*properties', 'properties'),
            (r'(\d+)\s*buildings', 'buildings'),
        ]
        
        for pattern, count_type in count_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    value = int(match.group(1))
                    claims.append(Claim(
                        claim_id=f"c_{claim_id}",
                        claim_text=match.group(0),
                        claim_type=ClaimType.COUNT.value,
                        value=value,
                        location=location,
                        context={'count_type': count_type}
                    ))
                    claim_id += 1
                except ValueError:
                    pass
        
        # Percentage patterns: X% growth, X% increase
        pct_patterns = [
            (r'(\d+(?:\.\d+)?)\s*%\s*(?:growth|increase|appreciation)', 'growth'),
            (r'(\d+(?:\.\d+)?)\s*%\s*(?:drop|decrease|decline)', 'decline'),
        ]
        
        for pattern, ptype in pct_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    value = float(match.group(1))
                    if ptype == 'decline':
                        value = -value
                    claims.append(Claim(
                        claim_id=f"c_{claim_id}",
                        claim_text=match.group(0),
                        claim_type=ClaimType.PERCENTAGE.value,
                        value=value,
                        unit="%",
                        location=location
                    ))
                    claim_id += 1
                except ValueError:
                    pass
        
        # View quality patterns
        view_patterns = [
            (r'(excellent|good|moderate|poor)\s*view', 'view'),
            (r'view.*?(excellent|good|moderate|poor)', 'view'),
        ]
        
        for pattern, _ in view_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                claims.append(Claim(
                    claim_id=f"c_{claim_id}",
                    claim_text=match.group(0),
                    claim_type=ClaimType.VIEW.value,
                    value=match.group(1).lower(),
                    location=location
                ))
                claim_id += 1
        
        # Sunlight patterns: X hours of sunlight
        sun_patterns = [
            (r'(\d+(?:\.\d+)?)\s*hours?\s*(?:of\s*)?(?:sun|sunlight|daylight)', 'hours'),
        ]
        
        for pattern, _ in sun_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    value = float(match.group(1))
                    claims.append(Claim(
                        claim_id=f"c_{claim_id}",
                        claim_text=match.group(0),
                        claim_type=ClaimType.SUNLIGHT.value,
                        value=value,
                        unit="hours",
                        location=location
                    ))
                    claim_id += 1
                except ValueError:
                    pass
        
        return claims


# Singleton
_fact_verifier = None


def get_fact_verifier() -> FactVerifier:
    """Get or create fact verifier singleton."""
    global _fact_verifier
    if _fact_verifier is None:
        _fact_verifier = FactVerifier()
    return _fact_verifier
