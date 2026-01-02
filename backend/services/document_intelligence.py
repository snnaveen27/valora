"""
Advanced Document Intelligence System for Real Estate
Understands any document type with AI-powered analysis
"""

import logging
import json
import csv
import io
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import pandas as pd
import geopandas as gpd
from datetime import datetime
import hashlib
import re

logger = logging.getLogger(__name__)

class DocumentIntelligence:
    """
    Advanced document understanding system that can process and understand
    any document type in the context of real estate
    """
    
    def __init__(self):
        self.supported_formats = {
            'pdf': self._process_pdf,
            'csv': self._process_csv,
            'json': self._process_json,
            'geojson': self._process_geojson,
            'kml': self._process_kml,
            'shp': self._process_shapefile,
            'xlsx': self._process_excel,
            'xls': self._process_excel,
            'txt': self._process_text,
            'jpg': self._process_image,
            'jpeg': self._process_image,
            'png': self._process_image,
            'tiff': self._process_image
        }
        
        self.context_patterns = {
            'property': r'(?i)(property|properties|real estate|apartment|house|villa|plot|land)',
            'location': r'(?i)(location|address|locality|area|zone|district|city|bangalore)',
            'price': r'(?i)(price|cost|value|rate|amount|₹|rs|inr|lakh|crore)',
            'area': r'(?i)(sqft|sq\.ft|square feet|area|size|dimension)',
            'amenities': r'(?i)(amenities|facilities|features|parking|gym|pool|garden)',
            'legal': r'(?i)(legal|document|registration|title|deed|agreement)',
            'infrastructure': r'(?i)(metro|road|highway|school|hospital|mall|park)'
        }
    
    def understand_document(self, 
                           document_path: Optional[str] = None,
                           document_content: Optional[Union[bytes, str]] = None,
                           document_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Understand any document with AI-powered analysis
        """
        try:
            # Determine document type
            if document_path:
                doc_type = Path(document_path).suffix.lower().replace('.', '')
            elif document_type:
                doc_type = document_type.lower()
            else:
                doc_type = self._detect_document_type(document_content)
            
            # Process based on type
            if doc_type in self.supported_formats:
                processor = self.supported_formats[doc_type]
                result = processor(document_path, document_content)
            else:
                result = self._process_generic(document_content)
            
            # Add context understanding
            result['context_analysis'] = self._analyze_context(result)
            result['real_estate_relevance'] = self._calculate_relevance(result)
            result['actionable_insights'] = self._generate_insights(result)
            
            return {
                'status': 'success',
                'document_type': doc_type,
                'understanding': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Document understanding error: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _process_pdf(self, path: Optional[str], content: Optional[bytes]) -> Dict:
        """Process PDF documents - maps, plans, reports"""
        result = {
            'type': 'pdf',
            'extracted_data': {}
        }
        
        try:
            import PyPDF2
            import fitz  # PyMuPDF
            
            if path:
                # Extract text from PDF
                doc = fitz.open(path)
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
            else:
                # Process from bytes
                doc = fitz.open(stream=content, filetype="pdf")
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
            
            # Extract real estate information
            result['extracted_data'] = {
                'text': text[:5000],  # First 5000 chars
                'properties_found': self._extract_properties(text),
                'locations': self._extract_locations(text),
                'prices': self._extract_prices(text),
                'areas': self._extract_areas(text),
                'dates': self._extract_dates(text),
                'legal_info': self._extract_legal_info(text)
            }
            
            # Determine PDF type
            if 'map' in text.lower() or 'zone' in text.lower():
                result['pdf_category'] = 'map/zoning'
            elif 'agreement' in text.lower() or 'deed' in text.lower():
                result['pdf_category'] = 'legal'
            elif 'plan' in text.lower() or 'layout' in text.lower():
                result['pdf_category'] = 'architectural'
            else:
                result['pdf_category'] = 'general'
                
        except Exception as e:
            logger.error(f"PDF processing error: {e}")
            result['error'] = str(e)
        
        return result
    
    def _process_csv(self, path: Optional[str], content: Optional[str]) -> Dict:
        """Process CSV files - property listings, data"""
        result = {
            'type': 'csv',
            'data_analysis': {}
        }
        
        try:
            if path:
                df = pd.read_csv(path)
            else:
                df = pd.read_csv(io.StringIO(content))
            
            # Analyze CSV structure
            result['data_analysis'] = {
                'rows': len(df),
                'columns': list(df.columns),
                'data_types': df.dtypes.to_dict(),
                'missing_values': df.isnull().sum().to_dict(),
                'summary_stats': df.describe().to_dict() if len(df) > 0 else {}
            }
            
            # Detect real estate data
            property_columns = self._detect_property_columns(df.columns)
            if property_columns:
                result['property_data'] = {
                    'identified_columns': property_columns,
                    'property_count': len(df),
                    'unique_locations': df[property_columns.get('location', 'city')].nunique() if 'location' in property_columns else 0,
                    'price_range': {
                        'min': df[property_columns.get('price', 'price')].min() if 'price' in property_columns else None,
                        'max': df[property_columns.get('price', 'price')].max() if 'price' in property_columns else None
                    }
                }
            
            # Extract samples
            result['sample_data'] = df.head(10).to_dict('records')
            
        except Exception as e:
            logger.error(f"CSV processing error: {e}")
            result['error'] = str(e)
        
        return result
    
    def _process_geojson(self, path: Optional[str], content: Optional[str]) -> Dict:
        """Process GeoJSON files - spatial data"""
        result = {
            'type': 'geojson',
            'spatial_analysis': {}
        }
        
        try:
            if path:
                gdf = gpd.read_file(path)
            else:
                gdf = gpd.read_file(json.loads(content))
            
            # Analyze spatial data
            result['spatial_analysis'] = {
                'features': len(gdf),
                'geometry_types': gdf.geometry.type.value_counts().to_dict(),
                'crs': str(gdf.crs) if gdf.crs else 'Unknown',
                'bounds': list(gdf.total_bounds),
                'properties': list(gdf.columns[gdf.columns != 'geometry'])
            }
            
            # Calculate spatial metrics
            if not gdf.empty:
                result['spatial_metrics'] = {
                    'total_area': gdf.geometry.area.sum() if gdf.geometry.type.iloc[0] in ['Polygon', 'MultiPolygon'] else None,
                    'total_length': gdf.geometry.length.sum() if gdf.geometry.type.iloc[0] in ['LineString', 'MultiLineString'] else None,
                    'centroid': [gdf.geometry.unary_union.centroid.x, gdf.geometry.unary_union.centroid.y]
                }
            
            # Extract property-related features
            property_features = gdf[gdf.columns[gdf.columns.str.contains('property|building|plot', case=False, na=False)]]
            if not property_features.empty:
                result['property_features'] = {
                    'count': len(property_features),
                    'attributes': property_features.head(5).to_dict('records')
                }
            
        except Exception as e:
            logger.error(f"GeoJSON processing error: {e}")
            result['error'] = str(e)
        
        return result
    
    def _process_kml(self, path: Optional[str], content: Optional[str]) -> Dict:
        """Process KML files - Google Earth data"""
        result = {
            'type': 'kml',
            'kml_data': {}
        }
        
        try:
            import fiona
            fiona.supported_drivers['KML'] = 'rw'
            
            if path:
                gdf = gpd.read_file(path, driver='KML')
            else:
                # Process from string content
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.kml', delete=False, mode='w') as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                gdf = gpd.read_file(tmp_path, driver='KML')
                Path(tmp_path).unlink()
            
            result['kml_data'] = {
                'features': len(gdf),
                'placemarks': gdf['Name'].tolist() if 'Name' in gdf.columns else [],
                'descriptions': gdf['Description'].tolist()[:5] if 'Description' in gdf.columns else [],
                'geometry_types': gdf.geometry.type.value_counts().to_dict()
            }
            
        except Exception as e:
            logger.error(f"KML processing error: {e}")
            result['error'] = str(e)
        
        return result
    
    def _process_shapefile(self, path: Optional[str], content: Optional[bytes]) -> Dict:
        """Process Shapefile - GIS data"""
        result = {
            'type': 'shapefile',
            'gis_data': {}
        }
        
        try:
            if path:
                gdf = gpd.read_file(path)
                
                result['gis_data'] = {
                    'features': len(gdf),
                    'crs': str(gdf.crs),
                    'attributes': list(gdf.columns[gdf.columns != 'geometry']),
                    'geometry_types': gdf.geometry.type.value_counts().to_dict(),
                    'bounds': list(gdf.total_bounds)
                }
            
        except Exception as e:
            logger.error(f"Shapefile processing error: {e}")
            result['error'] = str(e)
        
        return result
    
    def _process_excel(self, path: Optional[str], content: Optional[bytes]) -> Dict:
        """Process Excel files - property data"""
        result = {
            'type': 'excel',
            'excel_data': {}
        }
        
        try:
            if path:
                xls = pd.ExcelFile(path)
            else:
                xls = pd.ExcelFile(io.BytesIO(content))
            
            result['excel_data'] = {
                'sheets': xls.sheet_names,
                'data': {}
            }
            
            # Process each sheet
            for sheet in xls.sheet_names[:3]:  # First 3 sheets
                df = pd.read_excel(xls, sheet_name=sheet)
                result['excel_data']['data'][sheet] = {
                    'rows': len(df),
                    'columns': list(df.columns),
                    'sample': df.head(5).to_dict('records')
                }
            
        except Exception as e:
            logger.error(f"Excel processing error: {e}")
            result['error'] = str(e)
        
        return result
    
    def _process_json(self, path: Optional[str], content: Optional[str]) -> Dict:
        """Process JSON files"""
        result = {
            'type': 'json',
            'json_structure': {}
        }
        
        try:
            if path:
                with open(path, 'r') as f:
                    data = json.load(f)
            else:
                data = json.loads(content)
            
            result['json_structure'] = self._analyze_json_structure(data)
            
            # Check for property data
            if isinstance(data, list) and len(data) > 0:
                if self._is_property_data(data[0]):
                    result['property_data'] = {
                        'count': len(data),
                        'sample': data[:5]
                    }
            
        except Exception as e:
            logger.error(f"JSON processing error: {e}")
            result['error'] = str(e)
        
        return result
    
    def _process_text(self, path: Optional[str], content: Optional[str]) -> Dict:
        """Process text files"""
        result = {
            'type': 'text',
            'text_analysis': {}
        }
        
        try:
            if path:
                with open(path, 'r', encoding='utf-8') as f:
                    text = f.read()
            else:
                text = content
            
            result['text_analysis'] = {
                'length': len(text),
                'lines': len(text.split('\n')),
                'words': len(text.split()),
                'extracted_info': {
                    'properties': self._extract_properties(text),
                    'locations': self._extract_locations(text),
                    'prices': self._extract_prices(text)
                }
            }
            
        except Exception as e:
            logger.error(f"Text processing error: {e}")
            result['error'] = str(e)
        
        return result
    
    def _process_image(self, path: Optional[str], content: Optional[bytes]) -> Dict:
        """Process image files - property photos, maps"""
        result = {
            'type': 'image',
            'image_analysis': {}
        }
        
        try:
            from PIL import Image
            import pytesseract
            
            if path:
                img = Image.open(path)
            else:
                img = Image.open(io.BytesIO(content))
            
            # Basic image info
            result['image_analysis'] = {
                'dimensions': img.size,
                'format': img.format,
                'mode': img.mode
            }
            
            # Try OCR for text extraction
            try:
                text = pytesseract.image_to_string(img)
                if text:
                    result['ocr_text'] = text[:1000]
                    result['extracted_info'] = {
                        'locations': self._extract_locations(text),
                        'prices': self._extract_prices(text)
                    }
            except:
                pass
            
            # Determine image type
            if path and any(keyword in str(path).lower() for keyword in ['map', 'plan', 'layout']):
                result['image_category'] = 'map/plan'
            else:
                result['image_category'] = 'property_photo'
            
        except Exception as e:
            logger.error(f"Image processing error: {e}")
            result['error'] = str(e)
        
        return result
    
    def _process_generic(self, content: Any) -> Dict:
        """Process generic/unknown document types"""
        return {
            'type': 'generic',
            'content_preview': str(content)[:500] if content else None
        }
    
    def _detect_document_type(self, content: Union[bytes, str]) -> str:
        """Detect document type from content"""
        if isinstance(content, bytes):
            # Check magic bytes
            if content.startswith(b'%PDF'):
                return 'pdf'
            elif content.startswith(b'\x89PNG'):
                return 'png'
            elif content.startswith(b'\xff\xd8\xff'):
                return 'jpg'
        elif isinstance(content, str):
            # Check content patterns
            try:
                json.loads(content)
                return 'json'
            except:
                pass
            
            if ',' in content and '\n' in content:
                return 'csv'
        
        return 'unknown'
    
    def _extract_properties(self, text: str) -> List[str]:
        """Extract property references from text"""
        properties = []
        patterns = [
            r'(\d+)\s*BHK',
            r'(\d+)\s*bedroom',
            r'apartment|flat|villa|house|plot',
            r'residential|commercial'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            properties.extend(matches)
        
        return list(set(properties))[:10]
    
    def _extract_locations(self, text: str) -> List[str]:
        """Extract location references from text"""
        locations = []
        
        # Common Bangalore localities
        bangalore_areas = [
            'Whitefield', 'Koramangala', 'HSR Layout', 'Electronic City',
            'Marathahalli', 'Indiranagar', 'JP Nagar', 'Hebbal',
            'Sarjapur', 'BTM Layout', 'Bangalore', 'Bengaluru'
        ]
        
        for area in bangalore_areas:
            if area.lower() in text.lower():
                locations.append(area)
        
        return locations
    
    def _extract_prices(self, text: str) -> List[str]:
        """Extract price references from text"""
        prices = []
        patterns = [
            r'₹\s*[\d,]+(?:\.\d+)?\s*(?:lakh|lakhs|L|crore|crores|Cr)?',
            r'Rs\.?\s*[\d,]+(?:\.\d+)?\s*(?:lakh|lakhs|L|crore|crores|Cr)?',
            r'INR\s*[\d,]+(?:\.\d+)?'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            prices.extend(matches)
        
        return prices[:10]
    
    def _extract_areas(self, text: str) -> List[str]:
        """Extract area measurements from text"""
        areas = []
        patterns = [
            r'\d+(?:,\d+)?\s*(?:sq\.?ft|sqft|square feet)',
            r'\d+(?:,\d+)?\s*(?:sq\.?m|sqm|square meters)',
            r'\d+(?:,\d+)?\s*acres?'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            areas.extend(matches)
        
        return areas[:10]
    
    def _extract_dates(self, text: str) -> List[str]:
        """Extract date references from text"""
        dates = []
        patterns = [
            r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}',
            r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4}',
            r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        
        return dates[:5]
    
    def _extract_legal_info(self, text: str) -> Dict:
        """Extract legal information from text"""
        legal_info = {
            'has_agreement': 'agreement' in text.lower(),
            'has_registration': 'registration' in text.lower() or 'registered' in text.lower(),
            'has_title': 'title' in text.lower(),
            'has_deed': 'deed' in text.lower(),
            'has_encumbrance': 'encumbrance' in text.lower()
        }
        
        return legal_info
    
    def _detect_property_columns(self, columns: List[str]) -> Dict[str, str]:
        """Detect property-related columns in dataset"""
        column_mapping = {}
        
        for col in columns:
            col_lower = col.lower()
            if 'price' in col_lower or 'cost' in col_lower:
                column_mapping['price'] = col
            elif 'location' in col_lower or 'locality' in col_lower or 'address' in col_lower:
                column_mapping['location'] = col
            elif 'area' in col_lower or 'sqft' in col_lower or 'size' in col_lower:
                column_mapping['area'] = col
            elif 'bedroom' in col_lower or 'bhk' in col_lower:
                column_mapping['bedrooms'] = col
            elif 'property' in col_lower and 'type' in col_lower:
                column_mapping['property_type'] = col
        
        return column_mapping
    
    def _is_property_data(self, item: Dict) -> bool:
        """Check if JSON item contains property data"""
        property_keys = ['price', 'location', 'area', 'property', 'bedroom', 'sqft', 'locality']
        
        if isinstance(item, dict):
            item_keys = ' '.join(item.keys()).lower()
            return any(key in item_keys for key in property_keys)
        
        return False
    
    def _analyze_json_structure(self, data: Any, max_depth: int = 3, current_depth: int = 0) -> Dict:
        """Analyze JSON structure recursively"""
        if current_depth >= max_depth:
            return {'type': type(data).__name__, 'truncated': True}
        
        if isinstance(data, dict):
            return {
                'type': 'object',
                'keys': list(data.keys())[:20],
                'key_count': len(data)
            }
        elif isinstance(data, list):
            return {
                'type': 'array',
                'length': len(data),
                'item_type': type(data[0]).__name__ if data else None
            }
        else:
            return {'type': type(data).__name__}
    
    def _analyze_context(self, result: Dict) -> Dict:
        """Analyze document context for real estate relevance"""
        context = {
            'is_property_document': False,
            'document_purpose': 'unknown',
            'relevance_score': 0
        }
        
        # Check for property-related content
        doc_str = json.dumps(result).lower()
        
        property_score = sum(1 for pattern in self.context_patterns['property'].split('|') 
                           if pattern.strip('()') in doc_str)
        location_score = sum(1 for pattern in self.context_patterns['location'].split('|') 
                           if pattern.strip('()') in doc_str)
        
        total_score = property_score + location_score
        
        if total_score > 5:
            context['is_property_document'] = True
            context['relevance_score'] = min(100, total_score * 10)
        
        # Determine document purpose
        if 'legal' in doc_str:
            context['document_purpose'] = 'legal'
        elif 'map' in doc_str or 'zone' in doc_str:
            context['document_purpose'] = 'mapping'
        elif 'price' in doc_str or 'cost' in doc_str:
            context['document_purpose'] = 'valuation'
        elif 'property' in doc_str:
            context['document_purpose'] = 'property_listing'
        
        return context
    
    def _calculate_relevance(self, result: Dict) -> float:
        """Calculate real estate relevance score"""
        score = 0
        
        # Check for property data
        if 'property_data' in result:
            score += 30
        
        # Check for location data
        if 'locations' in str(result):
            score += 20
        
        # Check for price data
        if 'price' in str(result).lower():
            score += 20
        
        # Check for spatial data
        if 'spatial_analysis' in result or 'geometry' in str(result):
            score += 20
        
        # Check for legal data
        if 'legal' in str(result).lower():
            score += 10
        
        return min(100, score)
    
    def _generate_insights(self, result: Dict) -> List[str]:
        """Generate actionable insights from document"""
        insights = []
        
        doc_type = result.get('type', 'unknown')
        
        if doc_type == 'csv' and 'property_data' in result:
            count = result['property_data'].get('property_count', 0)
            insights.append(f"Found {count} property records ready for analysis")
            
            price_range = result['property_data'].get('price_range', {})
            if price_range.get('min') and price_range.get('max'):
                insights.append(f"Price range: ₹{price_range['min']:,.0f} - ₹{price_range['max']:,.0f}")
        
        elif doc_type == 'geojson' and 'spatial_analysis' in result:
            features = result['spatial_analysis'].get('features', 0)
            insights.append(f"Spatial data contains {features} geographic features")
            
            if 'spatial_metrics' in result:
                area = result['spatial_metrics'].get('total_area')
                if area:
                    insights.append(f"Total coverage area: {area:,.2f} sq units")
        
        elif doc_type == 'pdf':
            category = result.get('pdf_category', 'general')
            insights.append(f"Document type: {category}")
            
            if 'extracted_data' in result:
                locations = result['extracted_data'].get('locations', [])
                if locations:
                    insights.append(f"References locations: {', '.join(locations[:3])}")
        
        # Add generic insights
        relevance = result.get('real_estate_relevance', 0)
        if relevance > 70:
            insights.append("Highly relevant for real estate analysis")
        elif relevance > 40:
            insights.append("Moderately relevant for real estate analysis")
        
        return insights
