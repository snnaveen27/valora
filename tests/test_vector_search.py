"""
Test script for vector similarity search
Demonstrates property recommendations and semantic search
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.database.connection import db_manager
from backend.services.vector_embedding_service import VectorEmbeddingService
from backend.services.postgres_data_processor import PostgresDataProcessor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Test vector search functionality"""
    
    logger.info("=" * 80)
    logger.info("Vector Search Test")
    logger.info("=" * 80)
    
    # Test database connection
    if not db_manager.test_connection():
        logger.error("❌ Database connection failed!")
        return 1
    
    # Initialize services
    vector_service = VectorEmbeddingService()
    data_processor = PostgresDataProcessor()
    
    logger.info("\n1. Testing embedding generation...")
    
    # Sample property data
    sample_property = {
        'city': 'Bangalore',
        'locality': 'Koramangala',
        'property_type': 'residential',
        'property_subtype': '2bhk',
        'bedrooms': 2,
        'bathrooms': 2,
        'area_sqft': 1100,
        'price': 7500000,
        'furnishing': 'semi-furnished',
        'parking_spaces': 1,
        'amenities': ['swimming pool', 'gym', 'security', 'power backup'],
        'metadata': {
            'description': 'Modern 2BHK apartment in prime Koramangala location with excellent amenities'
        }
    }
    
    # Generate embeddings
    embeddings = vector_service.generate_property_embeddings(sample_property)
    
    logger.info(f"✅ Generated {len(embeddings)} embeddings:")
    for key, embedding in embeddings.items():
        logger.info(f"   - {key}: {len(embedding)} dimensions")
    
    logger.info("\n2. Testing semantic search...")
    
    # Test semantic search queries
    search_queries = [
        "2BHK apartment in Bangalore with swimming pool",
        "luxury villa with garden in Mumbai",
        "budget friendly 1BHK near metro station",
        "commercial office space in tech hub",
        "house with parking and security"
    ]
    
    for query in search_queries:
        logger.info(f"\nQuery: '{query}'")
        results = vector_service.semantic_search(
            query_text=query,
            limit=5
        )
        
        if results:
            logger.info(f"Found {len(results)} results:")
            for i, result in enumerate(results[:3]):
                logger.info(f"   {i+1}. {result['city']} - {result['locality']} - ₹{result['price']:,.0f} (similarity: {result['similarity_score']:.3f})")
        else:
            logger.info("   No results found")
    
    logger.info("\n3. Testing similar properties...")
    
    # Get a sample property from database
    properties = data_processor.query_properties(limit=1)
    
    if properties:
        sample_id = properties[0]['id']
        logger.info(f"Finding properties similar to: {properties[0]['city']} - {properties[0]['locality']}")
        
        similar = vector_service.find_similar_properties(
            property_id=sample_id,
            similarity_threshold=0.5,
            limit=5
        )
        
        if similar:
            logger.info(f"Found {len(similar)} similar properties:")
            for i, prop in enumerate(similar[:3]):
                logger.info(f"   {i+1}. {prop['city']} - {prop['locality']} - ₹{prop['price']:,.0f} (similarity: {prop['similarity_score']:.3f})")
        else:
            logger.info("   No similar properties found")
    else:
        logger.warning("   No properties found in database")
    
    logger.info("\n4. Getting embedding statistics...")
    
    stats = vector_service.get_embedding_stats()
    
    logger.info("Embedding Coverage:")
    logger.info(f"   Total properties: {stats.get('total_properties', 0)}")
    
    for embedding_type in ['description', 'amenities', 'location', 'combined']:
        coverage = stats.get(f'{embedding_type}_coverage_pct', 0)
        logger.info(f"   {embedding_type.capitalize()} embeddings: {coverage}%")
    
    logger.info("\n5. Batch update embeddings...")
    
    updated = vector_service.batch_update_embeddings(limit=10)
    logger.info(f"Updated embeddings for {updated} properties")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ Vector Search Test Completed!")
    logger.info("=" * 80)
    
    logger.info("\nVector search capabilities:")
    logger.info("✅ Semantic property search using natural language")
    logger.info("✅ Similar property recommendations")
    logger.info("✅ Embedding generation from property data")
    logger.info("✅ Batch embedding updates")
    logger.info("✅ Similarity thresholds and filtering")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
