"""
Valora AI - Regulatory Intelligence
FAR/FSI, zoning rules, buffer requirements, and compliance checks.

Features:
- FAR/FSI calculation and compliance
- Zoning classification
- Setback and buffer requirements
- Land use restrictions
- Approval risk assessment
- Due diligence checklist generation
"""

import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ZoneType(Enum):
    """BBMP/BDA Zoning classifications."""
    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    MIXED_USE = "mixed_use"
    GREEN_BELT = "green_belt"
    AGRICULTURAL = "agricultural"
    INSTITUTIONAL = "institutional"
    TRANSPORT = "transport"
    SPECIAL = "special"


class RiskLevel(Enum):
    """Regulatory risk levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ZoningInfo:
    """Zoning information for a location."""
    zone_type: str
    zone_name: str
    permitted_uses: List[str]
    conditional_uses: List[str]
    prohibited_uses: List[str]
    max_far: float  # Floor Area Ratio
    max_height_m: float
    min_plot_size_sqm: float
    ground_coverage_pct: float
    source: str = "BBMP Master Plan 2015"


@dataclass
class SetbackRequirement:
    """Setback requirements for a plot."""
    front_m: float
    rear_m: float
    side_m: float
    road_width_m: float
    plot_area_sqm: float
    building_type: str


@dataclass
class BufferZone:
    """Buffer zone restriction."""
    buffer_type: str  # lake, highway, railway, airport, etc.
    distance_m: float
    restriction: str
    source: str


@dataclass
class RegulatoryReport:
    """Complete regulatory analysis for a property."""
    lat: float
    lng: float
    
    # Zoning
    zoning: Optional[ZoningInfo] = None
    
    # FAR Analysis
    current_far: float = 0
    max_far: float = 0
    far_utilization_pct: float = 0
    additional_buildable_sqm: float = 0
    
    # Setbacks
    setback: Optional[SetbackRequirement] = None
    setback_compliant: bool = True
    
    # Buffer Zones
    buffer_zones: List[BufferZone] = field(default_factory=list)
    in_restricted_zone: bool = False
    
    # Risk Assessment
    risk_level: str = "low"
    risk_factors: List[str] = field(default_factory=list)
    risk_score: float = 0  # 0-100, lower is better
    
    # Approvals
    approvals_required: List[str] = field(default_factory=list)
    estimated_approval_time_months: int = 0
    
    # Due Diligence Checklist
    due_diligence: List[Dict[str, Any]] = field(default_factory=list)
    
    # Summary
    summary: str = ""


class RegulatoryIntelligence:
    """
    Provides regulatory intelligence for real estate transactions.
    Based on Bangalore BBMP/BDA regulations and master plan.
    """
    
    # BBMP FAR limits by zone (simplified)
    FAR_LIMITS = {
        ZoneType.RESIDENTIAL.value: {
            'default': 2.0,
            'high_density': 3.25,
            'metro_corridor': 4.0,
        },
        ZoneType.COMMERCIAL.value: {
            'default': 3.0,
            'cbd': 4.0,
            'metro_corridor': 4.0,
        },
        ZoneType.MIXED_USE.value: {
            'default': 2.5,
            'metro_corridor': 3.5,
        },
        ZoneType.INDUSTRIAL.value: {
            'default': 1.5,
        },
    }
    
    # Setback requirements by plot size (meters)
    SETBACK_RULES = {
        'small': {  # < 240 sqm
            'front': 1.5, 'rear': 1.5, 'side': 1.0,
            'ground_coverage': 65
        },
        'medium': {  # 240-600 sqm
            'front': 3.0, 'rear': 2.0, 'side': 1.5,
            'ground_coverage': 55
        },
        'large': {  # > 600 sqm
            'front': 4.5, 'rear': 3.0, 'side': 2.5,
            'ground_coverage': 50
        },
    }
    
    # Buffer zone requirements
    BUFFER_ZONES = {
        'lake': {
            'distance_m': 75,
            'restriction': 'No construction within 75m of lake boundary',
            'source': 'BBMP Lake Protection Rules'
        },
        'railway': {
            'distance_m': 30,
            'restriction': 'No permanent structures within 30m of railway track',
            'source': 'Indian Railways Act'
        },
        'highway': {
            'distance_m': 50,
            'restriction': 'Building line setback of 50m from highway',
            'source': 'NHAI Guidelines'
        },
        'high_tension': {
            'distance_m': 18,
            'restriction': 'No construction within 18m of HT lines',
            'source': 'BESCOM Safety Rules'
        },
        'naala': {
            'distance_m': 15,
            'restriction': 'Storm water drain buffer of 15m',
            'source': 'BBMP SWD Rules'
        },
    }
    
    # Due diligence checklist items
    DUE_DILIGENCE_ITEMS = [
        {'id': 'title', 'name': 'Title Verification', 'category': 'legal', 'mandatory': True},
        {'id': 'encumbrance', 'name': 'Encumbrance Certificate (EC)', 'category': 'legal', 'mandatory': True},
        {'id': 'khata', 'name': 'Khata Certificate', 'category': 'legal', 'mandatory': True},
        {'id': 'tax', 'name': 'Property Tax Receipts', 'category': 'legal', 'mandatory': True},
        {'id': 'plan_sanction', 'name': 'Sanctioned Building Plan', 'category': 'regulatory', 'mandatory': True},
        {'id': 'oc', 'name': 'Occupancy Certificate (OC)', 'category': 'regulatory', 'mandatory': True},
        {'id': 'cc', 'name': 'Completion Certificate (CC)', 'category': 'regulatory', 'mandatory': True},
        {'id': 'rera', 'name': 'RERA Registration', 'category': 'regulatory', 'mandatory': True},
        {'id': 'bwssb', 'name': 'BWSSB Connection', 'category': 'utilities', 'mandatory': False},
        {'id': 'bescom', 'name': 'BESCOM Connection', 'category': 'utilities', 'mandatory': False},
        {'id': 'conversion', 'name': 'Land Conversion Certificate', 'category': 'land', 'mandatory': False},
        {'id': 'layout', 'name': 'BDA/BMRDA Layout Approval', 'category': 'regulatory', 'mandatory': False},
        {'id': 'noc_aai', 'name': 'Airport Authority NOC', 'category': 'special', 'mandatory': False},
        {'id': 'noc_env', 'name': 'Environmental Clearance', 'category': 'special', 'mandatory': False},
    ]
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / 'src' / 'data' / 'valora.db'
        self.db_path = str(db_path)
    
    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        import math
        R = 6371000
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lng2 - lng1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def get_zoning(self, lat: float, lng: float) -> ZoningInfo:
        """
        Get zoning information for a location.
        Uses heuristics based on nearby POIs and building types.
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            radius_deg = 500 / 111000  # 500m radius
            
            # Check nearby building types
            cursor.execute("""
                SELECT building_type, COUNT(*) as cnt
                FROM buildings
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
                GROUP BY building_type
                ORDER BY cnt DESC
                LIMIT 5
            """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
            
            building_types = {row['building_type']: row['cnt'] for row in cursor.fetchall()}
            
            # Check nearby POIs
            cursor.execute("""
                SELECT category, COUNT(*) as cnt
                FROM pois
                WHERE latitude BETWEEN ? AND ?
                AND longitude BETWEEN ? AND ?
                GROUP BY category
                ORDER BY cnt DESC
            """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
            
            poi_types = {row['category']: row['cnt'] for row in cursor.fetchall()}
            conn.close()
            
            # Determine zone type based on surroundings
            residential_count = building_types.get('residential', 0) + building_types.get('house', 0)
            commercial_count = building_types.get('commercial', 0) + building_types.get('retail', 0)
            industrial_count = building_types.get('industrial', 0) + building_types.get('warehouse', 0)
            
            total = max(1, residential_count + commercial_count + industrial_count)
            
            if commercial_count / total > 0.5:
                zone = ZoneType.COMMERCIAL.value
            elif industrial_count / total > 0.3:
                zone = ZoneType.INDUSTRIAL.value
            elif commercial_count / total > 0.2:
                zone = ZoneType.MIXED_USE.value
            else:
                zone = ZoneType.RESIDENTIAL.value
            
            # Check for metro corridor (higher FAR)
            has_metro = any('metro' in k.lower() for k in poi_types.keys())
            
            far_category = 'metro_corridor' if has_metro else 'default'
            max_far = self.FAR_LIMITS.get(zone, {}).get(far_category, 2.0)
            
            return ZoningInfo(
                zone_type=zone,
                zone_name=f"{zone.title()} Zone",
                permitted_uses=self._get_permitted_uses(zone),
                conditional_uses=self._get_conditional_uses(zone),
                prohibited_uses=self._get_prohibited_uses(zone),
                max_far=max_far,
                max_height_m=self._get_max_height(zone, has_metro),
                min_plot_size_sqm=self._get_min_plot_size(zone),
                ground_coverage_pct=self._get_ground_coverage(zone),
                source="BBMP Master Plan 2015 (Inferred)"
            )
            
        except Exception as e:
            print(f"[Regulatory] Error getting zoning: {e}")
            return ZoningInfo(
                zone_type=ZoneType.RESIDENTIAL.value,
                zone_name="Residential Zone",
                permitted_uses=['Residential'],
                conditional_uses=['Home Office'],
                prohibited_uses=['Industrial'],
                max_far=2.0,
                max_height_m=15.0,
                min_plot_size_sqm=100,
                ground_coverage_pct=55,
                source="Default"
            )
    
    def _get_permitted_uses(self, zone: str) -> List[str]:
        uses = {
            'residential': ['Residential', 'Home Office', 'Parks', 'Religious'],
            'commercial': ['Retail', 'Office', 'Restaurant', 'Hotel', 'Residential'],
            'mixed_use': ['Residential', 'Retail', 'Office', 'Restaurant'],
            'industrial': ['Manufacturing', 'Warehouse', 'Office'],
        }
        return uses.get(zone, ['Residential'])
    
    def _get_conditional_uses(self, zone: str) -> List[str]:
        uses = {
            'residential': ['Clinic', 'Daycare', 'Guest House'],
            'commercial': ['Hospital', 'School', 'Assembly Hall'],
            'mixed_use': ['Hospital', 'Educational', 'Warehouse'],
            'industrial': ['Retail Showroom', 'Training Center'],
        }
        return uses.get(zone, [])
    
    def _get_prohibited_uses(self, zone: str) -> List[str]:
        uses = {
            'residential': ['Industrial', 'Large Commercial', 'Hazardous Storage'],
            'commercial': ['Heavy Industrial', 'Hazardous Manufacturing'],
            'mixed_use': ['Heavy Industrial', 'Hazardous'],
            'industrial': ['Residential', 'Hospital', 'School'],
        }
        return uses.get(zone, [])
    
    def _get_max_height(self, zone: str, metro_corridor: bool) -> float:
        base = {'residential': 15, 'commercial': 24, 'mixed_use': 18, 'industrial': 12}
        height = base.get(zone, 15)
        if metro_corridor:
            height *= 1.5
        return height
    
    def _get_min_plot_size(self, zone: str) -> float:
        sizes = {'residential': 100, 'commercial': 200, 'mixed_use': 150, 'industrial': 500}
        return sizes.get(zone, 100)
    
    def _get_ground_coverage(self, zone: str) -> float:
        coverage = {'residential': 55, 'commercial': 65, 'mixed_use': 60, 'industrial': 60}
        return coverage.get(zone, 55)
    
    def get_setback_requirements(
        self,
        plot_area_sqm: float,
        road_width_m: float = 12,
        building_type: str = "residential"
    ) -> SetbackRequirement:
        """Get setback requirements for a plot."""
        if plot_area_sqm < 240:
            rules = self.SETBACK_RULES['small']
        elif plot_area_sqm < 600:
            rules = self.SETBACK_RULES['medium']
        else:
            rules = self.SETBACK_RULES['large']
        
        # Adjust front setback based on road width
        front = rules['front']
        if road_width_m >= 18:
            front = max(front, 4.5)
        elif road_width_m >= 12:
            front = max(front, 3.0)
        
        return SetbackRequirement(
            front_m=front,
            rear_m=rules['rear'],
            side_m=rules['side'],
            road_width_m=road_width_m,
            plot_area_sqm=plot_area_sqm,
            building_type=building_type
        )
    
    def check_buffer_zones(self, lat: float, lng: float) -> List[BufferZone]:
        """Check if location is in any buffer zones."""
        buffers = []
        
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Check for lakes
            cursor.execute("""
                SELECT name, latitude, longitude
                FROM pois
                WHERE category LIKE '%lake%' OR category LIKE '%water%'
                AND latitude IS NOT NULL
            """)
            
            for row in cursor.fetchall():
                dist = self._haversine_distance(lat, lng, row['latitude'], row['longitude'])
                if dist < self.BUFFER_ZONES['lake']['distance_m']:
                    buffers.append(BufferZone(
                        buffer_type='lake',
                        distance_m=round(dist),
                        restriction=self.BUFFER_ZONES['lake']['restriction'],
                        source=self.BUFFER_ZONES['lake']['source']
                    ))
                    break
            
            # Check for railway (simplified - check for railway stations)
            cursor.execute("""
                SELECT name, latitude, longitude
                FROM pois
                WHERE category LIKE '%railway%' OR category LIKE '%train%'
                AND latitude IS NOT NULL
            """)
            
            for row in cursor.fetchall():
                dist = self._haversine_distance(lat, lng, row['latitude'], row['longitude'])
                if dist < 500:  # Within 500m of station might be near tracks
                    buffers.append(BufferZone(
                        buffer_type='railway',
                        distance_m=round(dist),
                        restriction=self.BUFFER_ZONES['railway']['restriction'],
                        source=self.BUFFER_ZONES['railway']['source']
                    ))
                    break
            
            conn.close()
            
        except Exception as e:
            print(f"[Regulatory] Error checking buffer zones: {e}")
        
        return buffers
    
    def generate_due_diligence_checklist(
        self,
        property_type: str = "residential",
        is_new_construction: bool = False,
        is_resale: bool = True
    ) -> List[Dict[str, Any]]:
        """Generate due diligence checklist for a transaction."""
        checklist = []
        
        for item in self.DUE_DILIGENCE_ITEMS:
            include = True
            
            # Filter based on property type
            if item['id'] == 'rera' and property_type == 'plot':
                include = False
            if item['id'] == 'oc' and is_new_construction:
                include = False  # Not yet available
            if item['id'] == 'conversion' and property_type != 'plot':
                include = False
            
            if include:
                checklist.append({
                    **item,
                    'status': 'pending',
                    'verified': False,
                    'notes': ''
                })
        
        return checklist
    
    def get_regulatory_report(
        self,
        lat: float,
        lng: float,
        plot_area_sqm: float = 500,
        built_up_sqm: float = 0,
        property_type: str = "residential"
    ) -> RegulatoryReport:
        """
        Generate complete regulatory analysis for a property.
        
        Args:
            lat, lng: Property location
            plot_area_sqm: Plot area
            built_up_sqm: Current built-up area (0 for vacant)
            property_type: Property type
            
        Returns:
            RegulatoryReport with zoning, FAR, buffers, and risk assessment
        """
        report = RegulatoryReport(lat=lat, lng=lng)
        
        # Get zoning
        zoning = self.get_zoning(lat, lng)
        report.zoning = zoning
        
        # FAR analysis
        report.max_far = zoning.max_far
        if plot_area_sqm > 0:
            max_buildable = plot_area_sqm * zoning.max_far
            report.current_far = built_up_sqm / plot_area_sqm if built_up_sqm > 0 else 0
            report.far_utilization_pct = (report.current_far / zoning.max_far) * 100 if zoning.max_far > 0 else 0
            report.additional_buildable_sqm = max(0, max_buildable - built_up_sqm)
        
        # Setback requirements
        report.setback = self.get_setback_requirements(plot_area_sqm, building_type=property_type)
        
        # Buffer zones
        report.buffer_zones = self.check_buffer_zones(lat, lng)
        report.in_restricted_zone = len(report.buffer_zones) > 0
        
        # Risk assessment
        risk_score = 0
        
        if report.in_restricted_zone:
            risk_score += 30
            report.risk_factors.append(f"Within buffer zone: {report.buffer_zones[0].buffer_type}")
        
        if report.far_utilization_pct > 90:
            risk_score += 20
            report.risk_factors.append("FAR nearly exhausted")
        
        if zoning.zone_type == ZoneType.GREEN_BELT.value:
            risk_score += 40
            report.risk_factors.append("In Green Belt zone - development restricted")
        
        report.risk_score = risk_score
        if risk_score >= 50:
            report.risk_level = RiskLevel.HIGH.value
        elif risk_score >= 30:
            report.risk_level = RiskLevel.MEDIUM.value
        else:
            report.risk_level = RiskLevel.LOW.value
        
        # Approvals required
        report.approvals_required = ['BBMP Building Plan Sanction', 'Khata Transfer']
        if zoning.zone_type in [ZoneType.COMMERCIAL.value, ZoneType.MIXED_USE.value]:
            report.approvals_required.append('Commercial License')
        if plot_area_sqm > 2000:
            report.approvals_required.append('Environmental Clearance')
        
        report.estimated_approval_time_months = len(report.approvals_required) * 2
        
        # Due diligence
        report.due_diligence = self.generate_due_diligence_checklist(property_type)
        
        # Summary
        report.summary = self._generate_summary(report)
        
        return report
    
    def _generate_summary(self, report: RegulatoryReport) -> str:
        """Generate natural language summary."""
        parts = []
        
        if report.zoning:
            parts.append(f"Zone: {report.zoning.zone_name} (Max FAR: {report.zoning.max_far})")
        
        if report.additional_buildable_sqm > 0:
            parts.append(f"Additional buildable: {report.additional_buildable_sqm:,.0f} sqm")
        
        if report.risk_factors:
            parts.append(f"Risk: {report.risk_level.upper()} - {', '.join(report.risk_factors)}")
        else:
            parts.append("Risk: LOW - No regulatory issues detected")
        
        return ". ".join(parts)


# Singleton
_regulatory_intel = None


def get_regulatory_intelligence() -> RegulatoryIntelligence:
    """Get or create regulatory intelligence singleton."""
    global _regulatory_intel
    if _regulatory_intel is None:
        _regulatory_intel = RegulatoryIntelligence()
    return _regulatory_intel
