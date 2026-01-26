"""
Locality Personality Model for City Intelligence Engine
Each neighborhood is characterized by a "personality" profile capturing identity and dynamics.

Features:
1. Static attributes: land use mix, historical era, cultural factors
2. Dynamic signals: demographics, economic index, mobility patterns
3. Personality archetypes: tech-hub, residential, commercial, mixed
4. Growth trajectory: emerging, growing, mature, declining
5. Investment profile: high-growth, stable, value, speculative
"""

import sqlite3
import json
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime


class LocalityArchetype(Enum):
    """Primary personality archetype for a locality."""
    TECH_HUB = "tech_hub"               # IT parks, startups, tech companies
    COMMERCIAL_CENTER = "commercial"     # Malls, offices, retail
    RESIDENTIAL_FAMILY = "residential_family"  # Family-oriented housing
    RESIDENTIAL_PREMIUM = "residential_premium"  # Luxury apartments, villas
    MIXED_USE = "mixed_use"             # Balanced commercial + residential
    INDUSTRIAL = "industrial"           # Manufacturing, warehouses
    INSTITUTIONAL = "institutional"     # Universities, hospitals, govt
    HERITAGE = "heritage"               # Historical areas, old city
    EMERGING = "emerging"               # Newly developing areas
    TRANSIT_ORIENTED = "transit_oriented"  # Metro/bus hub areas


class GrowthStage(Enum):
    """Development stage of a locality."""
    NASCENT = "nascent"           # Early development, farmland converting
    EMERGING = "emerging"         # Rapid initial growth
    GROWING = "growing"           # Sustained growth
    MATURING = "maturing"         # Growth slowing, infrastructure catching up
    MATURE = "mature"             # Fully developed, stable
    DECLINING = "declining"       # Population/economic decline
    REGENERATING = "regenerating" # Urban renewal underway


class InvestmentProfile(Enum):
    """Investment characteristics."""
    HIGH_GROWTH = "high_growth"     # Rapid appreciation, high risk
    STABLE_INCOME = "stable_income" # Steady rental yields
    VALUE_PLAY = "value_play"       # Undervalued, potential upside
    SPECULATIVE = "speculative"     # High volatility, bubble risk
    DEFENSIVE = "defensive"         # Low risk, capital preservation
    TURNAROUND = "turnaround"       # Distressed but improving


@dataclass
class DemographicSignals:
    """Dynamic demographic indicators."""
    population_estimate: int = 0
    population_growth_rate: float = 0.0  # Annual %
    avg_household_income: float = 0.0    # INR lakhs/year
    income_growth_rate: float = 0.0
    median_age: float = 30.0
    family_ratio: float = 0.5            # % households with children
    professional_ratio: float = 0.3       # % IT/corporate workers
    student_ratio: float = 0.1
    retiree_ratio: float = 0.1


@dataclass
class EconomicSignals:
    """Economic activity indicators."""
    commercial_density: float = 0.0      # Businesses per sqkm
    job_density: float = 0.0             # Jobs per sqkm
    retail_index: float = 50.0           # 0-100
    office_space_sqft: float = 0.0       # Total office space
    avg_office_rent: float = 0.0         # INR/sqft/month
    startup_count: int = 0
    it_company_count: int = 0
    mall_count: int = 0


@dataclass
class MobilitySignals:
    """Transportation and connectivity indicators."""
    metro_stations: int = 0
    bus_stops: int = 0
    avg_commute_time_min: float = 45.0
    traffic_congestion_index: float = 50.0  # 0-100, higher = worse
    walkability_score: float = 50.0
    cycling_infrastructure: float = 0.0
    parking_availability: float = 50.0


@dataclass
class RealEstateSignals:
    """Real estate market indicators."""
    avg_price_per_sqft: float = 0.0
    price_growth_1y: float = 0.0         # Annual %
    price_growth_5y: float = 0.0         # 5-year CAGR
    rental_yield: float = 0.0            # Annual %
    vacancy_rate: float = 0.0
    new_supply_units: int = 0            # New units in pipeline
    absorption_rate: float = 0.0         # Units sold per month
    price_volatility: float = 0.0        # Standard deviation


@dataclass
class LocalityProfile:
    """Complete personality profile for a locality."""
    # Identity
    locality_id: str
    name: str
    city: str = "Bangalore"
    
    # Classification
    archetype: LocalityArchetype = LocalityArchetype.MIXED_USE
    growth_stage: GrowthStage = GrowthStage.GROWING
    investment_profile: InvestmentProfile = InvestmentProfile.STABLE_INCOME
    
    # Coordinates (center)
    lat: float = 0.0
    lng: float = 0.0
    area_sqkm: float = 0.0
    
    # Personality traits (0-100 scale)
    tech_orientation: float = 50.0       # How tech-focused
    family_friendliness: float = 50.0    # Family amenities
    nightlife_index: float = 30.0        # Entertainment/dining
    green_index: float = 40.0            # Parks, lakes, trees
    heritage_value: float = 20.0         # Historical significance
    cosmopolitan_index: float = 50.0     # Diversity, expat-friendly
    
    # Infrastructure scores (0-100)
    road_quality: float = 50.0
    water_supply: float = 50.0
    power_reliability: float = 70.0
    internet_connectivity: float = 60.0
    healthcare_access: float = 50.0
    education_quality: float = 50.0
    
    # Signals
    demographics: DemographicSignals = field(default_factory=DemographicSignals)
    economics: EconomicSignals = field(default_factory=EconomicSignals)
    mobility: MobilitySignals = field(default_factory=MobilitySignals)
    real_estate: RealEstateSignals = field(default_factory=RealEstateSignals)
    
    # Narrative elements
    tagline: str = ""                    # One-line description
    key_landmarks: List[str] = field(default_factory=list)
    major_employers: List[str] = field(default_factory=list)
    known_for: List[str] = field(default_factory=list)
    challenges: List[str] = field(default_factory=list)
    
    # Metadata
    confidence_score: float = 0.5
    last_updated: str = ""
    data_sources: List[str] = field(default_factory=list)
    
    def get_personality_summary(self) -> str:
        """Generate a natural language personality summary."""
        traits = []
        
        if self.tech_orientation > 70:
            traits.append("tech-centric")
        if self.family_friendliness > 70:
            traits.append("family-friendly")
        if self.nightlife_index > 60:
            traits.append("vibrant nightlife")
        if self.green_index > 60:
            traits.append("green and serene")
        if self.heritage_value > 60:
            traits.append("rich heritage")
        if self.cosmopolitan_index > 70:
            traits.append("cosmopolitan")
        
        if not traits:
            traits.append("balanced mixed-use")
        
        return f"{self.name} is a {', '.join(traits)} locality in {self.growth_stage.value} stage"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        result['archetype'] = self.archetype.value
        result['growth_stage'] = self.growth_stage.value
        result['investment_profile'] = self.investment_profile.value
        return result


class LocalityPersonalityModel:
    """
    Builds and manages locality personality profiles using available data.
    """
    
    # Bangalore locality knowledge base (curated data)
    BANGALORE_LOCALITIES = {
        'whitefield': {
            'name': 'Whitefield',
            'lat': 12.9698, 'lng': 77.7500,
            'archetype': LocalityArchetype.TECH_HUB,
            'growth_stage': GrowthStage.MATURE,
            'tagline': "Bangalore's first IT corridor and expatriate hub",
            'tech_orientation': 90, 'family_friendliness': 65,
            'cosmopolitan_index': 85, 'nightlife_index': 55,
            'key_landmarks': ['ITPB', 'Phoenix Marketcity', 'Forum Shantiniketan'],
            'major_employers': ['SAP', 'IBM', 'Oracle', 'Capgemini'],
            'known_for': ['IT parks', 'International schools', 'Expat community'],
            'challenges': ['Traffic congestion', 'Water scarcity', 'Urban sprawl'],
        },
        'koramangala': {
            'name': 'Koramangala',
            'lat': 12.9352, 'lng': 77.6245,
            'archetype': LocalityArchetype.MIXED_USE,
            'growth_stage': GrowthStage.MATURE,
            'tagline': "Startup capital of India with vibrant youth culture",
            'tech_orientation': 85, 'family_friendliness': 55,
            'cosmopolitan_index': 80, 'nightlife_index': 85,
            'key_landmarks': ['Forum Mall', 'Jyoti Nivas College', 'BDA Complex'],
            'major_employers': ['Flipkart', 'Swiggy', 'Cure.fit', 'Startups'],
            'known_for': ['Startups', 'Cafes', 'Nightlife', 'Young professionals'],
            'challenges': ['Parking', 'Noise', 'High rents'],
        },
        'indiranagar': {
            'name': 'Indiranagar',
            'lat': 12.9784, 'lng': 77.6408,
            'archetype': LocalityArchetype.RESIDENTIAL_PREMIUM,
            'growth_stage': GrowthStage.MATURE,
            'tagline': "Premium residential with trendy commercial strips",
            'tech_orientation': 60, 'family_friendliness': 70,
            'cosmopolitan_index': 85, 'nightlife_index': 90,
            'key_landmarks': ['100 Feet Road', 'CMH Road', 'Indiranagar Metro'],
            'major_employers': ['Corporate offices', 'Boutiques', 'Restaurants'],
            'known_for': ['Fine dining', 'Boutiques', 'Premium housing', 'Metro access'],
            'challenges': ['Very high prices', 'Parking', 'Gentrification'],
        },
        'hsr_layout': {
            'name': 'HSR Layout',
            'lat': 12.9116, 'lng': 77.6389,
            'archetype': LocalityArchetype.RESIDENTIAL_FAMILY,
            'growth_stage': GrowthStage.MATURING,
            'tagline': "Well-planned residential with growing startup scene",
            'tech_orientation': 70, 'family_friendliness': 80,
            'cosmopolitan_index': 65, 'nightlife_index': 45,
            'key_landmarks': ['BDA Complex', 'Agara Lake', 'Sector boundaries'],
            'major_employers': ['Home offices', 'Small IT companies'],
            'known_for': ['Planned layout', 'Family living', 'Parks', 'Good schools'],
            'challenges': ['Water issues', 'Internal road congestion'],
        },
        'sarjapur_road': {
            'name': 'Sarjapur Road',
            'lat': 12.9100, 'lng': 77.6800,
            'archetype': LocalityArchetype.EMERGING,
            'growth_stage': GrowthStage.GROWING,
            'tagline': "Rapidly developing IT corridor with new townships",
            'tech_orientation': 75, 'family_friendliness': 70,
            'cosmopolitan_index': 60, 'nightlife_index': 35,
            'key_landmarks': ['Wipro Campus', 'Total Mall', 'Rainbow Drive'],
            'major_employers': ['Wipro', 'Infosys', 'Tech parks'],
            'known_for': ['New apartments', 'IT companies', 'Gated communities'],
            'challenges': ['Severe traffic', 'Infrastructure gaps', 'Water scarcity'],
        },
        'electronic_city': {
            'name': 'Electronic City',
            'lat': 12.8456, 'lng': 77.6603,
            'archetype': LocalityArchetype.TECH_HUB,
            'growth_stage': GrowthStage.MATURE,
            'tagline': "India's original technology park with massive IT presence",
            'tech_orientation': 95, 'family_friendliness': 50,
            'cosmopolitan_index': 55, 'nightlife_index': 25,
            'key_landmarks': ['Infosys Campus', 'Wipro Campus', 'Biocon'],
            'major_employers': ['Infosys', 'Wipro', 'TCS', 'Biocon'],
            'known_for': ['IT giants', 'Affordable housing', 'Expressway'],
            'challenges': ['Distance from city', 'Limited entertainment', 'Traffic on expressway'],
        },
        'jayanagar': {
            'name': 'Jayanagar',
            'lat': 12.9308, 'lng': 77.5838,
            'archetype': LocalityArchetype.RESIDENTIAL_FAMILY,
            'growth_stage': GrowthStage.MATURE,
            'tagline': "Traditional Bangalore with strong community bonds",
            'tech_orientation': 40, 'family_friendliness': 90,
            'cosmopolitan_index': 45, 'heritage_value': 70,
            'key_landmarks': ['4th Block Complex', 'Jayanagar Shopping Complex', 'Ashoka Pillar'],
            'major_employers': ['Local businesses', 'Government offices'],
            'known_for': ['Traditional shops', 'South Indian culture', 'Good schools'],
            'challenges': ['Aging infrastructure', 'Parking', 'Limited nightlife'],
        },
        'marathahalli': {
            'name': 'Marathahalli',
            'lat': 12.9591, 'lng': 77.7009,
            'archetype': LocalityArchetype.MIXED_USE,
            'growth_stage': GrowthStage.MATURING,
            'tagline': "ORR junction with IT companies and affordable housing",
            'tech_orientation': 75, 'family_friendliness': 60,
            'cosmopolitan_index': 65, 'nightlife_index': 40,
            'key_landmarks': ['ORR Junction', 'Marathahalli Bridge', 'Innovative Multiplex'],
            'major_employers': ['IT companies', 'Call centers'],
            'known_for': ['ORR access', 'PG accommodations', 'Young workforce'],
            'challenges': ['Extreme traffic', 'Pollution', 'Overcrowding'],
        },
        'jp_nagar': {
            'name': 'JP Nagar',
            'lat': 12.9077, 'lng': 77.5850,
            'archetype': LocalityArchetype.RESIDENTIAL_FAMILY,
            'growth_stage': GrowthStage.MATURE,
            'tagline': "Spacious residential with excellent social infrastructure",
            'tech_orientation': 45, 'family_friendliness': 85,
            'cosmopolitan_index': 50, 'green_index': 60,
            'key_landmarks': ['Bannerghatta Road', 'JP Nagar Metro', 'Brigade Millennium'],
            'major_employers': ['IT parks nearby', 'Healthcare'],
            'known_for': ['Wide roads', 'Good schools', 'Hospitals', 'Parks'],
            'challenges': ['Distance from CBD', 'Limited metro coverage'],
        },
        'hebbal': {
            'name': 'Hebbal',
            'lat': 13.0358, 'lng': 77.5970,
            'archetype': LocalityArchetype.TRANSIT_ORIENTED,
            'growth_stage': GrowthStage.GROWING,
            'tagline': "North Bangalore gateway with lake and flyover",
            'tech_orientation': 65, 'family_friendliness': 65,
            'cosmopolitan_index': 60, 'green_index': 55,
            'key_landmarks': ['Hebbal Lake', 'Hebbal Flyover', 'Manyata Tech Park'],
            'major_employers': ['Manyata Tech Park', 'Embassy Manyata'],
            'known_for': ['Airport connectivity', 'Lake', 'Tech parks'],
            'challenges': ['Flyover congestion', 'Rapid densification'],
        },
    }
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / 'src' / 'data' / 'valora.db'
        self.db_path = str(db_path)
        self.profiles_cache: Dict[str, LocalityProfile] = {}
    
    def get_profile(self, locality_name: str) -> Optional[LocalityProfile]:
        """Get or build a locality profile."""
        key = locality_name.lower().replace(' ', '_')
        
        if key in self.profiles_cache:
            return self.profiles_cache[key]
        
        profile = self._build_profile(locality_name)
        if profile:
            self.profiles_cache[key] = profile
        
        return profile
    
    def _build_profile(self, locality_name: str) -> Optional[LocalityProfile]:
        """Build a locality profile from available data."""
        key = locality_name.lower().replace(' ', '_').replace('-', '_')
        
        # Start with curated data if available
        if key in self.BANGALORE_LOCALITIES:
            curated = self.BANGALORE_LOCALITIES[key]
            profile = LocalityProfile(
                locality_id=key,
                name=curated['name'],
                lat=curated['lat'],
                lng=curated['lng'],
                archetype=curated.get('archetype', LocalityArchetype.MIXED_USE),
                growth_stage=curated.get('growth_stage', GrowthStage.GROWING),
                tagline=curated.get('tagline', ''),
                tech_orientation=curated.get('tech_orientation', 50),
                family_friendliness=curated.get('family_friendliness', 50),
                cosmopolitan_index=curated.get('cosmopolitan_index', 50),
                nightlife_index=curated.get('nightlife_index', 30),
                heritage_value=curated.get('heritage_value', 20),
                green_index=curated.get('green_index', 40),
                key_landmarks=curated.get('key_landmarks', []),
                major_employers=curated.get('major_employers', []),
                known_for=curated.get('known_for', []),
                challenges=curated.get('challenges', []),
            )
        else:
            # Create basic profile from database
            profile = LocalityProfile(
                locality_id=key,
                name=locality_name.title(),
            )
        
        # Enrich with database data
        self._enrich_from_database(profile)
        
        # Calculate investment profile
        self._calculate_investment_profile(profile)
        
        profile.last_updated = datetime.now().isoformat()
        
        return profile
    
    def _enrich_from_database(self, profile: LocalityProfile):
        """Enrich profile with data from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            lat, lng = profile.lat, profile.lng
            if not lat or not lng:
                # Try to find coordinates from places table
                cursor.execute("""
                    SELECT latitude, longitude FROM places 
                    WHERE name LIKE ? LIMIT 1
                """, (f"%{profile.name}%",))
                row = cursor.fetchone()
                if row:
                    lat, lng = row['latitude'], row['longitude']
                    profile.lat, profile.lng = lat, lng
            
            if lat and lng:
                radius_deg = 2000 / 111000  # 2km radius
                
                # Real estate signals
                cursor.execute("""
                    SELECT 
                        AVG(price_per_sqft) as avg_ppsf,
                        COUNT(*) as listings
                    FROM properties
                    WHERE latitude BETWEEN ? AND ?
                    AND longitude BETWEEN ? AND ?
                    AND price_per_sqft > 0
                """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
                
                row = cursor.fetchone()
                if row and row['avg_ppsf']:
                    profile.real_estate.avg_price_per_sqft = row['avg_ppsf']
                
                # Mobility signals - metro stations
                cursor.execute("""
                    SELECT COUNT(*) as cnt FROM transport_stops
                    WHERE transport_type = 'metro'
                    AND latitude BETWEEN ? AND ?
                    AND longitude BETWEEN ? AND ?
                """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
                
                row = cursor.fetchone()
                profile.mobility.metro_stations = row['cnt'] if row else 0
                
                # Bus stops
                cursor.execute("""
                    SELECT COUNT(*) as cnt FROM transport_stops
                    WHERE transport_type = 'bus'
                    AND latitude BETWEEN ? AND ?
                    AND longitude BETWEEN ? AND ?
                """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
                
                row = cursor.fetchone()
                profile.mobility.bus_stops = row['cnt'] if row else 0
                
                # POI counts for economic signals
                cursor.execute("""
                    SELECT category, COUNT(*) as cnt FROM pois
                    WHERE latitude BETWEEN ? AND ?
                    AND longitude BETWEEN ? AND ?
                    GROUP BY category
                """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
                
                for row in cursor.fetchall():
                    cat = row['category']
                    cnt = row['cnt']
                    if cat == 'restaurant':
                        profile.nightlife_index = min(100, 30 + cnt * 2)
                    elif cat == 'school':
                        profile.family_friendliness = min(100, profile.family_friendliness + cnt * 3)
                    elif cat == 'hospital':
                        profile.healthcare_access = min(100, 40 + cnt * 10)
                    elif cat == 'park':
                        profile.green_index = min(100, 30 + cnt * 5)
                    elif cat == 'mall':
                        profile.economics.mall_count = cnt
                
                # Get terrain/flood risk
                cursor.execute("""
                    SELECT flood_risk, suitability_score
                    FROM terrain_grid
                    ORDER BY ABS(center_lat - ?) + ABS(center_lng - ?)
                    LIMIT 1
                """, (lat, lng))
                
                row = cursor.fetchone()
                if row:
                    if row['flood_risk'] == 'high':
                        profile.challenges.append('Flood risk')
                
                # Get nearby landmarks from named buildings
                cursor.execute("""
                    SELECT name FROM buildings
                    WHERE name IS NOT NULL AND name != ''
                    AND latitude BETWEEN ? AND ?
                    AND longitude BETWEEN ? AND ?
                    AND (height > 30 OR building_type IN ('commercial', 'retail', 'office'))
                    LIMIT 10
                """, (lat - radius_deg, lat + radius_deg, lng - radius_deg, lng + radius_deg))
                
                db_landmarks = [row['name'] for row in cursor.fetchall()]
                profile.key_landmarks = list(set(profile.key_landmarks + db_landmarks))[:10]
            
            conn.close()
        except Exception as e:
            print(f"[LocalityPersonality] Database enrichment error: {e}")
    
    def _calculate_investment_profile(self, profile: LocalityProfile):
        """Determine investment profile based on signals."""
        re = profile.real_estate
        
        # High growth: high price growth, growing stage
        if re.price_growth_1y > 15 or profile.growth_stage == GrowthStage.GROWING:
            profile.investment_profile = InvestmentProfile.HIGH_GROWTH
        
        # Speculative: very high price growth, high volatility
        elif re.price_growth_1y > 25 or re.price_volatility > 20:
            profile.investment_profile = InvestmentProfile.SPECULATIVE
        
        # Stable income: mature area, good rental yield
        elif profile.growth_stage == GrowthStage.MATURE and re.rental_yield > 3:
            profile.investment_profile = InvestmentProfile.STABLE_INCOME
        
        # Value play: lower prices, emerging area
        elif profile.growth_stage == GrowthStage.EMERGING:
            profile.investment_profile = InvestmentProfile.VALUE_PLAY
        
        # Defensive: heritage area, stable
        elif profile.heritage_value > 60:
            profile.investment_profile = InvestmentProfile.DEFENSIVE
        
        # Default: stable income
        else:
            profile.investment_profile = InvestmentProfile.STABLE_INCOME
    
    def get_all_profiles(self) -> List[LocalityProfile]:
        """Get profiles for all known localities."""
        profiles = []
        for key in self.BANGALORE_LOCALITIES.keys():
            profile = self.get_profile(key)
            if profile:
                profiles.append(profile)
        return profiles
    
    def compare_localities(self, locality1: str, locality2: str) -> Dict[str, Any]:
        """Compare two localities across dimensions."""
        p1 = self.get_profile(locality1)
        p2 = self.get_profile(locality2)
        
        if not p1 or not p2:
            return {"error": "One or both localities not found"}
        
        comparison = {
            'locality1': p1.name,
            'locality2': p2.name,
            'dimensions': {
                'tech_orientation': {p1.name: p1.tech_orientation, p2.name: p2.tech_orientation},
                'family_friendliness': {p1.name: p1.family_friendliness, p2.name: p2.family_friendliness},
                'nightlife': {p1.name: p1.nightlife_index, p2.name: p2.nightlife_index},
                'green_index': {p1.name: p1.green_index, p2.name: p2.green_index},
                'metro_access': {p1.name: p1.mobility.metro_stations, p2.name: p2.mobility.metro_stations},
                'avg_price': {p1.name: p1.real_estate.avg_price_per_sqft, p2.name: p2.real_estate.avg_price_per_sqft},
            },
            'archetypes': {p1.name: p1.archetype.value, p2.name: p2.archetype.value},
            'investment_profiles': {p1.name: p1.investment_profile.value, p2.name: p2.investment_profile.value},
            'recommendation': self._generate_comparison_recommendation(p1, p2),
        }
        
        return comparison
    
    def _generate_comparison_recommendation(self, p1: LocalityProfile, p2: LocalityProfile) -> str:
        """Generate comparison recommendation."""
        recs = []
        
        if p1.tech_orientation > p2.tech_orientation + 20:
            recs.append(f"{p1.name} is better for tech professionals")
        elif p2.tech_orientation > p1.tech_orientation + 20:
            recs.append(f"{p2.name} is better for tech professionals")
        
        if p1.family_friendliness > p2.family_friendliness + 20:
            recs.append(f"{p1.name} is more family-friendly")
        elif p2.family_friendliness > p1.family_friendliness + 20:
            recs.append(f"{p2.name} is more family-friendly")
        
        if p1.real_estate.avg_price_per_sqft < p2.real_estate.avg_price_per_sqft * 0.8:
            recs.append(f"{p1.name} offers better value")
        elif p2.real_estate.avg_price_per_sqft < p1.real_estate.avg_price_per_sqft * 0.8:
            recs.append(f"{p2.name} offers better value")
        
        return "; ".join(recs) if recs else "Both localities have comparable characteristics"


# Singleton
_personality_model = None


def get_locality_personality_model() -> LocalityPersonalityModel:
    """Get singleton personality model."""
    global _personality_model
    if _personality_model is None:
        _personality_model = LocalityPersonalityModel()
    return _personality_model
