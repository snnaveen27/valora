# Property Images for AI Training

## Overview

This directory contains **496 property images** downloaded from the Valora database, mapped to specific properties with full metadata. These images are ready for AI model training, particularly for Vision-Language models like Qwen3-VL.

## 📊 Dataset Statistics

- **Total Images**: 496
- **Source**: MagicBricks (real estate listings)
- **Properties Covered**: 496 unique properties
- **Average Images per Property**: ~1 (up to 3 max)
- **Coverage**: Bangalore properties with coordinates

## 📁 Directory Structure

```
property_images/
├── by_property/          # Images organized by property ID
│   ├── magicbricks_*/    # One folder per property
│   └── ...               # 496 property folders
├── by_locality/          # Symlinks organized by locality
├── by_type/              # Symlinks organized by property type
├── image_metadata.json   # Complete metadata for all images
├── training_data.jsonl   # Training data in JSONL format
├── vl_training_data.json # Vision-Language format (exported)
└── README.md            # This file
```

## 🎯 Use Cases

### 1. **Property Recognition & Classification**
- Train models to identify property types (2BHK, 3BHK, commercial, etc.)
- Recognize architectural styles and building conditions
- Classify listings (rent vs sale)

### 2. **Market Analysis**
- Visual property valuation
- Amenity detection from images
- Quality assessment

### 3. **Spatial Reasoning**
- Location-based property analysis
- Neighborhood characteristics from visual cues
- Urban pattern recognition

### 4. **Vision-Language Models**
- Property description generation
- Image-to-text for listings
- Multi-modal property search

## 📄 Data Formats

### Training Data (JSONL)
Each line contains:
```json
{
  "image_path": "data/property_images/by_property/magicbricks_*/image.jpg",
  "property_id": "magicbricks_12345",
  "source": "magicbricks",
  "property_type": "2BHK Residential House",
  "listing_type": "rent",
  "locality": "Bangalore",
  "city": "Bangalore",
  "bedrooms": 2,
  "bathrooms": 2,
  "area_sqft": 1200.0,
  "price": 25000.0,
  "price_per_sqft": 21.0,
  "latitude": 12.9716,
  "longitude": 77.5946
}
```

### Vision-Language Format
Optimized for Qwen3-VL and similar models:
```json
{
  "image": "/path/to/image.jpg",
  "conversations": [
    {
      "role": "user",
      "content": "<image>\nDescribe this property image."
    },
    {
      "role": "assistant",
      "content": "2BHK Residential House | 2 BHK | 1200 sq.ft | ₹25000 | in Bangalore"
    }
  ],
  "metadata": {
    "property_id": "magicbricks_12345",
    "latitude": 12.9716,
    "longitude": 77.5946,
    "price": 25000.0,
    "bedrooms": 2
  }
}
```

## 🚀 Quick Start

### Using the Download Script

```bash
# Analyze available images in database
python scripts/download_property_images.py --analyze

# Download more images (500 properties, max 3 images each)
python scripts/download_property_images.py --download --limit 500 --max-images 3

# View summary
python scripts/download_property_images.py --summary
```

### Using the API

```python
# Get image statistics
GET /api/images/stats

# Get images for a property
GET /api/images/property/{property_id}

# Get images near a location
GET /api/images/nearby?lat=12.9716&lng=77.5946&radius_km=2.0

# Get training batch
GET /api/images/training/batch?batch_size=32

# Export VL training data
POST /api/images/training/export

# Serve image file
GET /api/images/file/{property_id}/{filename}
```

### Using the Python Service

```python
from backend.services.property_image_service import get_image_service

# Initialize service
image_service = get_image_service()

# Get stats
stats = image_service.get_stats()

# Get images for property
images = image_service.get_images_for_property("magicbricks_12345")

# Get nearby images
nearby = image_service.get_images_near_location(lat=12.9716, lng=77.5946, radius_km=2.0)

# Get training batch
batch = image_service.get_training_batch(batch_size=32, property_type="2BHK")

# Export for training
output_path = image_service.export_for_training()
```

## 🧠 Training Examples

### Qwen3-VL Fine-tuning

```python
import json
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

# Load model
model = Qwen3VLForConditionalGeneration.from_pretrained("Qwen/Qwen3-VL-2B")
processor = AutoProcessor.from_pretrained("Qwen/Qwen3-VL-2B")

# Load training data
with open("data/property_images/vl_training_data.json", "r") as f:
    training_data = json.load(f)

# Process batch
for item in training_data[:10]:
    image_path = item["image"]
    conversation = item["conversations"]
    # ... training logic
```

### Custom Vision Model

```python
import torch
from PIL import Image

# Load training data
with open("data/property_images/training_data.jsonl", "r") as f:
    data = [json.loads(line) for line in f]

# Create dataset
class PropertyDataset(torch.utils.data.Dataset):
    def __init__(self, data):
        self.data = data
    
    def __getitem__(self, idx):
        item = self.data[idx]
        image = Image.open(item["image_path"])
        label = {
            "bedrooms": item["bedrooms"],
            "price": item["price"],
            "locality": item["locality"]
        }
        return image, label
```

## 📈 Expansion

To download more images:

```bash
# Download from all 5,399 properties with images
python scripts/download_property_images.py --download --limit 5399 --max-images 5

# This will give you ~15,000+ images total
```

## 🔗 Integration with Valora AI

These images are integrated with:
- **Multi-agent chat**: Visual property analysis
- **Simulation engine**: Visual impact prediction
- **Valuation model**: Image-based pricing
- **Spatial reasoning**: Visual neighborhood analysis

## 📝 Metadata Fields

Each image record includes:
- `property_id`: Unique property identifier
- `image_path`: Relative path to image
- `source`: Data source (magicbricks, housing, etc.)
- `property_type`: Type description
- `listing_type`: rent/sale/lease
- `locality`: Location name
- `city`: Bangalore
- `bedrooms`: Number of bedrooms
- `bathrooms`: Number of bathrooms
- `area_sqft`: Total area in square feet
- `price`: Listed price
- `price_per_sqft`: Price per square foot
- `latitude`: Geo coordinate
- `longitude`: Geo coordinate

## 🎓 Research Applications

1. **Urban Morphology**: Analyze building patterns from images
2. **Price Prediction**: Visual features → price correlation
3. **Amenity Detection**: Identify features from property images
4. **Quality Assessment**: Condition scoring from visuals
5. **Multi-modal Retrieval**: Text + image search

## 🔒 Data Privacy

- Images are from public real estate listings
- Downloaded for research and AI training purposes
- Property IDs are anonymized
- No personal information included

## 📊 Quality Metrics

- ✅ All images validated (JPEG/PNG/WebP magic bytes)
- ✅ Minimum size: 500 bytes
- ✅ Valid coordinates for 496/496 images
- ✅ Complete metadata for all images
- ✅ Organized directory structure

## 🚀 Next Steps

1. **Expand Dataset**: Download all ~15K images
2. **Add Augmentation**: Generate variations for training
3. **Create Annotations**: Add detailed labels
4. **Build Models**: Train custom property vision models
5. **Deploy**: Integrate with live property analysis

---

**Last Updated**: January 30, 2026  
**Version**: 1.0  
**Maintainer**: Valora AI Team
