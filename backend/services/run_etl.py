"""
ETL Runner Script
Run this to ingest all CSV files from data/raw directory
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.services.intelligent_etl_service import IntelligentETLService
from backend.database.connection import db_manager
import logging
import argparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main ETL runner"""
    parser = argparse.ArgumentParser(description="Run ETL to ingest raw data")
    parser.add_argument(
        "--pattern",
        default="*.csv",
        help="File pattern to match (default: *.csv)"
    )
    parser.add_argument(
        "--compute-spatial",
        action="store_true",
        help="Compute spatial features after ingestion"
    )
    parser.add_argument(
        "--raw-dir",
        default="data/raw",
        help="Raw data directory (default: data/raw)"
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 80)
    logger.info("ETL Runner - Intelligent Data Ingestion")
    logger.info("=" * 80)
    
    # Test database connection
    logger.info("\n1. Testing database connection...")
    if not db_manager.test_connection():
        logger.error("❌ Database connection failed!")
        logger.error("Please ensure PostgreSQL is running and DATABASE_URL is set correctly")
        return 1
    logger.info("✅ Database connection successful")
    
    # Initialize ETL service
    logger.info("\n2. Initializing ETL service...")
    etl = IntelligentETLService(raw_data_dir=args.raw_dir)
    logger.info(f"✅ ETL service initialized (raw_dir: {args.raw_dir})")
    
    # Check for files
    raw_path = Path(args.raw_dir)
    files = list(raw_path.rglob(args.pattern))
    
    if not files:
        logger.warning(f"⚠️  No files found matching pattern '{args.pattern}' in {args.raw_dir}")
        logger.info("\nTo get started:")
        logger.info(f"1. Place CSV files in {args.raw_dir}/")
        logger.info("2. Files can be named like: bangalore_2bhk_flats_2024.csv")
        logger.info("3. Or organized in folders: mumbai/commercial/office_bandra.csv")
        logger.info("4. Run this script again")
        return 0
    
    logger.info(f"\n3. Found {len(files)} files to process")
    for f in files[:10]:  # Show first 10
        logger.info(f"   - {f.relative_to(raw_path)}")
    if len(files) > 10:
        logger.info(f"   ... and {len(files) - 10} more files")
    
    # Ingest files
    logger.info("\n4. Starting data ingestion...")
    logger.info("-" * 80)
    
    summary = etl.ingest_all_raw_files(pattern=args.pattern)
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("INGESTION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total files: {summary['total_files']}")
    logger.info(f"✅ Success: {summary['success']}")
    logger.info(f"⚠️  Skipped: {summary['skipped']} (already processed)")
    logger.info(f"❌ Failed: {summary['failed']}")
    
    # Show details
    if summary['success'] > 0:
        logger.info("\nSuccessfully ingested files:")
        total_records = 0
        for result in summary['results']:
            if result['status'] == 'success':
                logger.info(f"  ✅ {Path(result['file']).name}: {result['inserted_records']} records")
                total_records += result['inserted_records']
        logger.info(f"\n📊 Total records ingested: {total_records}")
    
    if summary['failed'] > 0:
        logger.error("\nFailed files:")
        for result in summary['results']:
            if result['status'] == 'failed':
                logger.error(f"  ❌ {Path(result['file']).name}: {result.get('error', 'Unknown error')}")
    
    # Compute spatial features if requested
    if args.compute_spatial and summary['success'] > 0:
        logger.info("\n5. Computing spatial features...")
        logger.info("-" * 80)
        
        computed = etl.compute_spatial_features(batch_size=100)
        logger.info(f"✅ Computed spatial features for {computed} properties")
    
    # Refresh materialized views
    if summary['success'] > 0:
        logger.info("\n6. Refreshing materialized views...")
        try:
            db_manager.refresh_materialized_views()
            logger.info("✅ Materialized views refreshed")
        except Exception as e:
            logger.warning(f"⚠️  Could not refresh views: {e}")
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ ETL COMPLETED SUCCESSFULLY!")
    logger.info("=" * 80)
    
    if summary['success'] > 0:
        logger.info("\nNext steps:")
        logger.info("1. Query data via PostgreSQL or FastAPI endpoints")
        logger.info("2. Train ML models with ingested data")
        logger.info("3. Use multi-agent system for analysis")
        logger.info("\nExample query:")
        logger.info("  psql -d realestate -c \"SELECT COUNT(*) FROM properties;\"")
    
    return 0 if summary['failed'] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
