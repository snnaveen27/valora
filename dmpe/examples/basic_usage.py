"""
Basic usage example for the Valora Dynamic Market Prediction Engine (DMPE).

This script demonstrates how to:
1. Create a ValoraAgent instance
2. Train a prediction model
3. Make predictions
4. Save and load models
"""

import os
import pandas as pd
from pathlib import Path

# Add the project root to the Python path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from src.valora.core import ValoraAgent, ModelConfig, ModelType

def load_sample_data() -> pd.DataFrame:
    """Load sample real estate data."""
    # In a real application, you would load this from a database or file
    data = {
        'area': [1200, 1500, 1800, 2000, 1600, 1400, 1700, 1900, 1100, 1300],
        'bedrooms': [2, 3, 3, 4, 3, 2, 3, 4, 2, 2],
        'bathrooms': [1, 2, 2, 2.5, 2, 1, 2, 2.5, 1, 1],
        'location': ['A', 'B', 'A', 'C', 'B', 'A', 'C', 'B', 'A', 'C'],
        'price': [250000, 320000, 350000, 420000, 380000, 290000, 360000, 400000, 230000, 270000]
    }
    return pd.DataFrame(data)

def main():
    # Initialize the agent
    agent = ValoraAgent()
    
    # Load sample data
    data = load_sample_data()
    print("Sample data:")
    print(data.head())
    
    # Define model configuration
    config = ModelConfig(
        model_type=ModelType.XGBOOST,
        target='price',
        features=['area', 'bedrooms', 'bathrooms', 'location'],
        model_params={
            'n_estimators': 100,
            'max_depth': 3,
            'learning_rate': 0.1
        }
    )
    
    # Train the model
    print("\nTraining model...")
    metrics = agent.train_model(data, model_name='price_predictor', config=config)
    print(f"Model trained with metrics: {metrics}")
    
    # Make a prediction
    sample_property = {
        'area': 1650,
        'bedrooms': 3,
        'bathrooms': 2,
        'location': 'B'
    }
    
    prediction = agent.predict('price_predictor', sample_property)
    print(f"\nPredicted price for the property: ${prediction:,.2f}")
    
    # Save the model
    models_dir = Path('models')
    models_dir.mkdir(exist_ok=True)
    agent.save_model('price_predictor', models_dir)
    print(f"\nModel saved to {models_dir}/price_predictor")
    
    # Load the model
    new_agent = ValoraAgent()
    new_agent.load_model('price_predictor', models_dir)
    
    # Verify the loaded model works
    new_prediction = new_agent.predict('price_predictor', sample_property)
    print(f"Prediction from loaded model: ${new_prediction:,.2f}")

if __name__ == "__main__":
    main()
