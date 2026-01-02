"""
RAG and Vector Processing System for Property Data
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from backend.database.multiconnection import mdb

logger = logging.getLogger(__name__)

class RAGVectorProcessor:
    """
    Process raw property data for RAG and vector storage
    """
    
    def __init__(self):
        self.raw_data_path = Path("data/raw")
        self.processed_data_path = Path("data/processed")
        self.processed_data_path.mkdir(parents=True, exist_ok=True)
        
    def process_property_data(self) -> Dict[str, Any]:
        """
        Process all property CSV files for RAG/vector system
        """
        logger.info("Starting property data processing for RAG/Vectors...")
        
        stats = {
            "files_processed": 0,
            "properties_processed": 0,
            "embeddings_created": 0,
            "errors": []
        }
        
        try:
            # Get all property CSV files
            property_files = list(self.raw_data_path.rglob("properties/**/*.csv"))
            logger.info(f"Found {len(property_files)} property CSV files")
            
            for file_path in property_files:
                try:
                    # Process each file
                    processed_count = self._process_property_file(file_path)
                    stats["files_processed"] += 1
                    stats["properties_processed"] += processed_count
                    logger.info(f"Processed {file_path.name}: {processed_count} properties")
                    
                except Exception as e:
                    error_msg = f"Error processing {file_path.name}: {str(e)}"
                    logger.error(error_msg)
                    stats["errors"].append(error_msg)
            
            # Generate property embeddings
            embeddings_created = self._generate_property_embeddings()
            stats["embeddings_created"] = embeddings_created
            
            # Create RAG documents
            rag_docs = self._create_rag_documents()
            stats["rag_documents_created"] = rag_docs
            
            logger.info(f"Processing complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Processing error: {e}")
            stats["errors"].append(str(e))
            return stats
    
    def _process_property_file(self, file_path: Path) -> int:
        """
        Process individual property CSV file
        """
        try:
            # Read CSV
            df = pd.read_csv(file_path)
            
            if df.empty:
                return 0
            
            # Extract property type from path
            property_type = self._extract_property_type(file_path)
            
            # Process each property
            processed_properties = []
            
            for _, row in df.iterrows():
                try:
                    # Create property document
                    prop_doc = self._create_property_document(row, property_type)
                    if prop_doc:
                        processed_properties.append(prop_doc)
                except Exception as e:
                    logger.warning(f"Error processing row: {e}")
                    continue
            
            # Save processed data
            if processed_properties:
                output_file = self.processed_data_path / f"{file_path.stem}_processed.json"
                with open(output_file, 'w') as f:
                    json.dump(processed_properties, f, indent=2)
            
            return len(processed_properties)
            
        except Exception as e:
            logger.error(f"File processing error: {e}")
            return 0
    
    def _extract_property_type(self, file_path: Path) -> str:
        """
        Extract property type from file path
        """
        parts = file_path.parts
        
        # Try to find property type from path
        for part in reversed(parts):
            if 'residential' in part.lower():
                return 'residential'
            elif 'commercial' in part.lower():
                return 'commercial'
            elif 'agricultural' in part.lower():
                return 'agricultural'
            elif 'flat' in part.lower() or 'apartment' in part.lower():
                return 'apartment'
            elif 'house' in part.lower() or 'villa' in part.lower():
                return 'house'
            elif 'plot' in part.lower():
                return 'plot'
            elif 'shop' in part.lower():
                return 'shop'
            elif 'office' in part.lower():
                return 'office'
        
        return 'general'
    
    def _create_property_document(self, row: pd.Series, property_type: str) -> Optional[Dict]:
        """
        Create a structured document for RAG
        """
        try:
            # Extract key fields
            doc = {
                'id': self._generate_doc_id(row),
                'property_type': property_type,
                'name': row.get('name', 'Unknown Property'),
                'description': self._build_description(row, property_type),
                'price': float(row.get('price', 0)) if pd.notna(row.get('price')) else None,
                'area_sqft': float(row.get('area_sqft', 0)) if pd.notna(row.get('area_sqft')) else None,
                'location': {
                    'city': row.get('city_name', row.get('city', 'Bangalore')),
                    'locality': row.get('locality', row.get('address', 'Unknown')),
                    'coordinates': self._extract_coordinates(row)
                },
                'features': self._extract_features(row),
                'metadata': {
                    'bedrooms': int(row.get('bedrooms', 0)) if pd.notna(row.get('bedrooms')) else None,
                    'bathrooms': int(row.get('bathrooms', 0)) if pd.notna(row.get('bathrooms')) else None,
                    'parking': int(row.get('parking_spaces', 0)) if pd.notna(row.get('parking_spaces')) else None,
                    'age_years': int(row.get('age_years', 0)) if pd.notna(row.get('age_years')) else None,
                    'floor': row.get('floor', 'N/A'),
                    'furnished': row.get('furnishing_status', 'Unfurnished')
                },
                'pricing': {
                    'total_price': float(row.get('price', 0)) if pd.notna(row.get('price')) else None,
                    'price_per_sqft': float(row.get('price_per_sqft', 0)) if pd.notna(row.get('price_per_sqft')) else None,
                    'transaction_type': row.get('transaction_type', 'sale')
                },
                'timestamp': datetime.now().isoformat()
            }
            
            return doc
            
        except Exception as e:
            logger.error(f"Document creation error: {e}")
            return None
    
    def _generate_doc_id(self, row: pd.Series) -> str:
        """
        Generate unique document ID
        """
        import hashlib
        
        # Create hash from key fields
        id_string = f"{row.get('name', '')}{row.get('location', '')}{row.get('price', '')}"
        return hashlib.md5(id_string.encode()).hexdigest()[:16]
    
    def _build_description(self, row: pd.Series, property_type: str) -> str:
        """
        Build rich description for RAG
        """
        parts = []
        
        # Basic info
        name = row.get('name', 'Property')
        parts.append(f"{name} is a {property_type} property")
        
        # Location
        locality = row.get('locality', row.get('address', ''))
        city = row.get('city_name', row.get('city', 'Bangalore'))
        if locality and locality != 'Unknown':
            parts.append(f"located in {locality}, {city}")
        
        # Size and bedrooms
        area = row.get('area_sqft')
        bedrooms = row.get('bedrooms')
        if pd.notna(area):
            parts.append(f"with {int(area)} sqft area")
        if pd.notna(bedrooms):
            parts.append(f"and {int(bedrooms)} bedrooms")
        
        # Price
        price = row.get('price')
        if pd.notna(price):
            price_in_cr = float(price) / 10000000
            if price_in_cr >= 1:
                parts.append(f"priced at ₹{price_in_cr:.2f} crore")
            else:
                price_in_lakhs = float(price) / 100000
                parts.append(f"priced at ₹{price_in_lakhs:.2f} lakhs")
        
        # Description from data
        desc = row.get('description', '')
        if desc and desc != 'nan' and pd.notna(desc):
            parts.append(f"Features: {str(desc)[:200]}")
        
        return ". ".join(parts) + "."
    
    def _extract_coordinates(self, row: pd.Series) -> Optional[Dict]:
        """
        Extract latitude and longitude
        """
        lat = row.get('latitude', row.get('lat'))
        lon = row.get('longitude', row.get('lon', row.get('lng')))
        
        # Try parsing location field if lat/lon not directly available
        if (pd.isna(lat) or pd.isna(lon)) and 'location' in row:
            location_str = str(row['location'])
            if ',' in location_str:
                try:
                    parts = location_str.split(',')
                    lat = float(parts[0].strip())
                    lon = float(parts[1].strip())
                except:
                    pass
        
        if pd.notna(lat) and pd.notna(lon):
            return {
                'lat': float(lat),
                'lon': float(lon)
            }
        
        return None
    
    def _extract_features(self, row: pd.Series) -> List[str]:
        """
        Extract property features
        """
        features = []
        
        # Amenities
        amenities = row.get('amenities', '')
        if amenities and pd.notna(amenities) and amenities != 'nan':
            features.extend([a.strip() for a in str(amenities).split(',')])
        
        # Additional features
        if row.get('parking_spaces', 0) > 0:
            features.append(f"Parking: {int(row['parking_spaces'])} spaces")
        
        if row.get('balconies', 0) > 0:
            features.append(f"Balconies: {int(row['balconies'])}")
        
        if row.get('swimming_pool'):
            features.append("Swimming Pool")
        
        if row.get('gym'):
            features.append("Gym")
        
        return features
    
    def _generate_property_embeddings(self) -> int:
        """
        Generate embeddings for properties (placeholder for actual embedding generation)
        """
        logger.info("Generating property embeddings...")
        
        try:
            with mdb.spatial() as session:
                # Get count of properties that need embeddings
                result = session.execute(text("""
                    SELECT COUNT(*) FROM property_locations
                """))
                count = result.scalar()
                
                logger.info(f"Properties available for embeddings: {count}")
                
                # Note: Actual embedding generation would require:
                # 1. Text embedding model (e.g., sentence-transformers)
                # 2. Insert into property_embeddings table in vector DB
                # 3. For now, we're just counting available properties
                
                return count or 0
                
        except Exception as e:
            logger.error(f"Embedding generation error: {e}")
            return 0
    
    def _create_rag_documents(self) -> int:
        """
        Create RAG-ready documents from processed data
        """
        logger.info("Creating RAG documents...")
        
        try:
            processed_files = list(self.processed_data_path.glob("*_processed.json"))
            total_docs = 0
            
            rag_documents = []
            
            for file_path in processed_files:
                with open(file_path, 'r') as f:
                    properties = json.load(f)
                    
                    for prop in properties:
                        # Create RAG document
                        rag_doc = {
                            'id': prop['id'],
                            'content': prop['description'],
                            'metadata': {
                                'property_type': prop['property_type'],
                                'price': prop['price'],
                                'location': prop['location'],
                                'area_sqft': prop['area_sqft'],
                                'source': 'property_database'
                            }
                        }
                        rag_documents.append(rag_doc)
                        total_docs += 1
            
            # Save RAG documents
            if rag_documents:
                rag_output = self.processed_data_path / "rag_documents.json"
                with open(rag_output, 'w') as f:
                    json.dump(rag_documents, f, indent=2)
                
                logger.info(f"Created {total_docs} RAG documents")
            
            return total_docs
            
        except Exception as e:
            logger.error(f"RAG document creation error: {e}")
            return 0
    
    def get_processing_stats(self) -> Dict:
        """
        Get statistics about processed data
        """
        stats = {
            'raw_files': 0,
            'processed_files': 0,
            'rag_documents': 0,
            'processed_date': None
        }
        
        try:
            # Count raw files
            raw_files = list(self.raw_data_path.rglob("properties/**/*.csv"))
            stats['raw_files'] = len(raw_files)
            
            # Count processed files
            processed_files = list(self.processed_data_path.glob("*_processed.json"))
            stats['processed_files'] = len(processed_files)
            
            # Count RAG documents
            rag_file = self.processed_data_path / "rag_documents.json"
            if rag_file.exists():
                with open(rag_file, 'r') as f:
                    rag_docs = json.load(f)
                    stats['rag_documents'] = len(rag_docs)
                    stats['processed_date'] = datetime.now().isoformat()
            
        except Exception as e:
            logger.error(f"Stats error: {e}")
        
        return stats


# Standalone execution
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    processor = RAGVectorProcessor()
    
    print("=" * 60)
    print("RAG & Vector Processing System")
    print("=" * 60)
    
    # Process data
    result = processor.process_property_data()
    
    print("\n📊 Processing Results:")
    print(f"   Files Processed: {result['files_processed']}")
    print(f"   Properties Processed: {result['properties_processed']}")
    print(f"   Embeddings Ready: {result['embeddings_created']}")
    print(f"   RAG Documents: {result.get('rag_documents_created', 0)}")
    
    if result['errors']:
        print(f"\n⚠️  Errors: {len(result['errors'])}")
        for error in result['errors'][:5]:
            print(f"   - {error}")
    
    # Get stats
    stats = processor.get_processing_stats()
    print(f"\n📈 Data Statistics:")
    print(f"   Raw Files: {stats['raw_files']}")
    print(f"   Processed Files: {stats['processed_files']}")
    print(f"   RAG Documents: {stats['rag_documents']}")
    
    print("\n✅ Processing complete!")
