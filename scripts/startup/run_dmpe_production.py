"""
DMPE Production Pipeline
Complete end-to-end pipeline integrating data processing, model training, and RAG indexing
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime
import json

# Add paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "dmpe" / "src"))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/dmpe_production.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create logs directory
Path("logs").mkdir(exist_ok=True)

class DMPEProductionPipeline:
    """Complete production pipeline for DMPE system"""
    
    def __init__(self):
        self.project_root = project_root
        self.data_dir = project_root / "data"
        self.raw_dir = self.data_dir / "raw"
        self.processed_dir = self.data_dir / "processed"
        self.models_dir = project_root / "dmpe" / "models"
        
        # Create directories
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        self.stats = {
            'start_time': datetime.now(),
            'datasets_processed': 0,
            'models_trained': 0,
            'vectors_indexed': 0,
            'errors': []
        }
    
    def step1_process_data(self):
        """Step 1: Process raw data using DMPE's UnifiedRealEstateProcessor"""
        logger.info("="*80)
        logger.info("STEP 1: PROCESSING RAW DATA WITH DMPE")
        logger.info("="*80)
        
        try:
            from valora.data.real_estate_processor import UnifiedRealEstateProcessor
            
            # Initialize processor
            processor = UnifiedRealEstateProcessor(data_dir=str(self.raw_dir))
            
            # Process all datasets
            logger.info("Loading and processing all datasets...")
            processed_datasets = processor.process_all_data()
            
            logger.info(f"Processed {len(processed_datasets)} datasets")
            
            # Save processed data
            logger.info("Saving processed datasets...")
            processor.save_processed_data(processed_datasets, str(self.processed_dir))
            
            # Generate market summary
            logger.info("Generating market summary...")
            summary = processor.get_market_summary(processed_datasets)
            
            # Save summary
            summary_file = self.processed_dir / f"market_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)
            
            logger.info(f"Market summary saved to: {summary_file}")
            logger.info(f"Total properties: {summary['total_properties']:,}")
            logger.info(f"Cities: {summary['cities']}")
            logger.info(f"Property types: {len(summary['property_types'])}")
            
            self.stats['datasets_processed'] = len(processed_datasets)
            self.processed_datasets = processed_datasets
            
            return processed_datasets
            
        except Exception as e:
            logger.error(f"Error in data processing: {e}", exc_info=True)
            self.stats['errors'].append({'step': 'data_processing', 'error': str(e)})
            return None
    
    def step2_train_models(self, datasets):
        """Step 2: Train ML models using DMPE's MarketPredictionEngine"""
        logger.info("\n" + "="*80)
        logger.info("STEP 2: TRAINING ML MODELS WITH DMPE")
        logger.info("="*80)
        
        if not datasets:
            logger.error("No datasets available for training")
            return False
        
        try:
            from valora.core.prediction_engine import MarketPredictionEngine
            
            # Initialize engine
            engine = MarketPredictionEngine(models_dir=str(self.models_dir))
            
            # Train price prediction models
            logger.info("Training price prediction models...")
            engine.train_price_models(datasets)
            
            logger.info(f"Trained {len(engine.price_models)} price models")
            
            # Train rental models
            logger.info("Training rental prediction models...")
            engine.train_rental_models(datasets)
            
            logger.info(f"Trained {len(engine.rental_models)} rental models")
            
            # Generate market forecast
            logger.info("Generating market forecasts...")
            forecast = engine.generate_market_forecast(datasets, periods=12)
            
            # Save forecast
            forecast_file = self.models_dir / f"market_forecast_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(forecast_file, 'w') as f:
                json.dump(forecast, f, indent=2)
            
            logger.info(f"Market forecast saved to: {forecast_file}")
            
            self.stats['models_trained'] = len(engine.price_models) + len(engine.rental_models)
            
            return True
            
        except Exception as e:
            logger.error(f"Error in model training: {e}", exc_info=True)
            self.stats['errors'].append({'step': 'model_training', 'error': str(e)})
            return False
    
    def step3_index_rag(self, datasets):
        """Step 3: Index data in Pinecone for RAG"""
        logger.info("\n" + "="*80)
        logger.info("STEP 3: INDEXING DATA IN PINECONE RAG")
        logger.info("="*80)
        
        if not datasets:
            logger.error("No datasets available for indexing")
            return False
        
        # Check if Pinecone is configured
        if not os.getenv("PINECONE_API_KEY"):
            logger.warning("PINECONE_API_KEY not set - skipping RAG indexing")
            logger.info("To enable RAG: Set PINECONE_API_KEY in .env file")
            return False
        
        try:
            from valora.rag.pinecone_rag import build_index_from_datasets
            
            index_name = os.getenv("PINECONE_INDEX", "valora-realestate")
            
            logger.info(f"Building Pinecone index: {index_name}")
            logger.info("This may take several minutes...")
            
            # Build index
            vectors_indexed = build_index_from_datasets(
                index_name=index_name,
                datasets=datasets,
                batch_size=128
            )
            
            logger.info(f"Successfully indexed {vectors_indexed:,} vectors in Pinecone")
            
            self.stats['vectors_indexed'] = vectors_indexed
            
            return True
            
        except Exception as e:
            logger.error(f"Error in RAG indexing: {e}", exc_info=True)
            self.stats['errors'].append({'step': 'rag_indexing', 'error': str(e)})
            return False
    
    def generate_report(self):
        """Generate final pipeline report"""
        logger.info("\n" + "="*80)
        logger.info("DMPE PRODUCTION PIPELINE REPORT")
        logger.info("="*80)
        
        duration = (datetime.now() - self.stats['start_time']).total_seconds()
        
        logger.info(f"\nExecution Summary:")
        logger.info(f"  Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        logger.info(f"  Datasets Processed: {self.stats['datasets_processed']}")
        logger.info(f"  Models Trained: {self.stats['models_trained']}")
        logger.info(f"  Vectors Indexed: {self.stats['vectors_indexed']:,}")
        
        if self.stats['errors']:
            logger.warning(f"\n  Errors Encountered: {len(self.stats['errors'])}")
            for error in self.stats['errors']:
                logger.warning(f"    - {error['step']}: {error['error']}")
        else:
            logger.info("\n  ✓ No errors encountered")
        
        logger.info(f"\nOutput Locations:")
        logger.info(f"  Processed Data: {self.processed_dir}")
        logger.info(f"  Trained Models: {self.models_dir}")
        
        logger.info("\nNext Steps:")
        logger.info("  1. Start backend API: python backend/start_backend.py")
        logger.info("  2. Start frontend: npm run dev")
        logger.info("  3. Access API docs: http://localhost:8000/docs")
        logger.info("  4. Access frontend: http://localhost:3000")
        
        logger.info("="*80)
        
        # Save report
        report = {
            'pipeline_run': {
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': duration,
                'status': 'completed' if not self.stats['errors'] else 'completed_with_errors'
            },
            'statistics': self.stats,
            'output_paths': {
                'processed_data': str(self.processed_dir),
                'models': str(self.models_dir)
            }
        }
        
        report_file = self.project_root / f"dmpe_pipeline_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"\nDetailed report saved to: {report_file}")
        
        return not bool(self.stats['errors'])
    
    def run(self):
        """Run the complete DMPE production pipeline"""
        logger.info("\n" + "="*80)
        logger.info("STARTING DMPE PRODUCTION PIPELINE")
        logger.info("="*80)
        logger.info(f"Project Root: {self.project_root}")
        logger.info(f"Data Directory: {self.data_dir}")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info("="*80 + "\n")
        
        try:
            # Step 1: Process Data
            datasets = self.step1_process_data()
            if not datasets:
                logger.error("Pipeline failed at Step 1: Data Processing")
                return False
            
            # Step 2: Train Models
            success = self.step2_train_models(datasets)
            if not success:
                logger.warning("Pipeline completed Step 2 with errors")
            
            # Step 3: Index RAG
            success = self.step3_index_rag(datasets)
            if not success:
                logger.warning("Pipeline completed Step 3 with errors or skipped")
            
            # Generate report
            return self.generate_report()
            
        except KeyboardInterrupt:
            logger.info("\nPipeline interrupted by user")
            return False
        except Exception as e:
            logger.error(f"Pipeline failed with unexpected error: {e}", exc_info=True)
            return False


if __name__ == "__main__":
    pipeline = DMPEProductionPipeline()
    success = pipeline.run()
    sys.exit(0 if success else 1)
