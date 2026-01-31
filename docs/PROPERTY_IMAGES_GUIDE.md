# Property Images for AI Training - Complete Guide

## 🎯 Overview

Successfully downloaded and prepared **496 property images** with full metadata for AI training and reasoning. Images are mapped to specific properties with coordinates, prices, and attributes.

## ✅ What's Been Set Up

### 1. **Image Download System** (`scripts/download_property_images.py`)
- Downloads images from database URLs (img.staticmb.com, housingcdn.com)
- Validates image files (magic bytes check)
- Maps images to properties with full metadata
- Organizes by property ID, locality, and type
- Handles failures gracefully (476/500 success rate)

### 2. **Storage Structure**
```
data/property_images/
├── by_property/          # 496 property folders with images
├── image_metadata.json   # Complete metadata (498KB)
├── training_data.jsonl   # Training format (236KB)
└── qwen_training/        # Qwen3-VL ready data
    ├── train.json        # 446 examples
    ├── eval.json         # 50 examples
    ├── simple_format.jsonl
    ├── property_dataset.py
    ├── training_config.json
    └── dataset_statistics.json
```

### 3. **API Endpoints** (Backend Server)
```python
GET  /api/images/stats                    # Dataset statistics
GET  /api/images/property/{property_id}   # Images for property
GET  /api/images/locality/{locality}      # Images by location
GET  /api/images/nearby?lat=&lng=         # Nearby property images
GET  /api/images/training/batch           # Training batch
GET  /api/images/training/vl-format       # Vision-Language format
POST /api/images/training/export          # Export for training
GET  /api/images/file/{property_id}/{file}  # Serve image file
```

### 4. **Python Service** (`backend/services/property_image_service.py`)
```python
from services.property_image_service import get_image_service

service = get_image_service()
service.get_stats()                        # Statistics
service.get_images_for_property(id)        # Property images
service.get_images_near_location(lat, lng) # Spatial query
service.get_training_batch(32)             # Training batch
service.prepare_vl_training_data()         # VL format
```

## 📊 Dataset Statistics

- **Total Images**: 496
- **Properties**: 496 unique
- **Source**: MagicBricks real estate listings
- **Coverage**: Bangalore area with GPS coordinates (477/496)
- **Price Range**: ₹1,100 - ₹200,000,000 (avg ₹5.1M)
- **Property Types**: Residential (2BHK, 3BHK), Commercial, Warehouse
- **Bedroom Distribution**:
  - 2BHK: 109 properties
  - 3BHK: 74 properties
  - Commercial (no bedrooms): 249 properties
  - Other: 64 properties

## 🚀 Using with Qwen3-VL

### Option 1: Direct Integration in Notebook

```python
import json
from pathlib import Path
from PIL import Image

# Load training data
train_path = Path("data/property_images/qwen_training/train.json")
with open(train_path, 'r', encoding='utf-8') as f:
    train_data = json.load(f)

print(f"Training examples: {len(train_data)}")

# Examine first example
example = train_data[0]
print("\nUser prompt:", example['messages'][0]['content'][1]['text'])
print("Image path:", example['messages'][0]['content'][0]['image'])
print("Assistant response:", example['messages'][1]['content'][0]['text'][:100])

# Load an image
image_path = example['messages'][0]['content'][0]['image']
image = Image.open(image_path)
image.show()
```

### Option 2: Using the Dataset Loader

```python
import sys
sys.path.append('data/property_images/qwen_training')
from property_dataset import PropertyImageDataset

# Create dataset
dataset = PropertyImageDataset('data/property_images/qwen_training/train.json')
print(f"Dataset size: {len(dataset)}")

# Get sample
sample = dataset[0]
print(f"Image shape: {sample['image'].size}")
print(f"Prompt: {sample['prompt']}")
print(f"Response: {sample['response']}")
```

### Option 3: Fine-tuning Qwen3-VL

```python
from transformers import AutoProcessor, Qwen2VLForConditionalGeneration
from transformers import TrainingArguments, Trainer
import torch

# Load model
model_name = "Qwen/Qwen2-VL-2B-Instruct"
processor = AutoProcessor.from_pretrained(model_name)
model = Qwen2VLForConditionalGeneration.from_pretrained(
    model_name,
    torch_dtype=torch.float16,
    device_map="auto"
)

# Load dataset
train_dataset = PropertyImageDataset('data/property_images/qwen_training/train.json')
eval_dataset = PropertyImageDataset('data/property_images/qwen_training/eval.json')

# Training arguments
training_args = TrainingArguments(
    output_dir="./qwen_property_finetuned",
    num_train_epochs=3,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
    learning_rate=1e-5,
    warmup_steps=100,
    logging_steps=10,
    save_steps=100,
    eval_steps=100,
    fp16=True,
)

# Create trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
)

# Start training
trainer.train()
```

## 🎯 Use Cases

### 1. **Property Visual Analysis**
```python
# Get images near a location for market analysis
from services.property_image_service import get_image_service

service = get_image_service()
nearby = service.get_images_near_location(
    lat=12.9716, 
    lng=77.5946, 
    radius_km=2.0,
    limit=20
)

print(f"Found {len(nearby)} properties within 2km")
for prop in nearby:
    print(f"  {prop['property_type']} - ₹{prop['price']:,.0f} - {prop['_distance_km']}km away")
```

### 2. **Price Prediction from Images**
```python
# Train a model to predict price from property images
import torch.nn as nn

class PropertyPricePredictor(nn.Module):
    def __init__(self, vision_encoder):
        super().__init__()
        self.encoder = vision_encoder
        self.price_head = nn.Linear(768, 1)
    
    def forward(self, images):
        features = self.encoder(images)
        price = self.price_head(features)
        return price

# Train on property images with price labels
```

### 3. **Multi-modal Property Search**
```python
# Search properties using both text and image similarity
from transformers import CLIPProcessor, CLIPModel

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

# Query: "Modern 2BHK apartment with balcony"
# Returns visually similar properties
```

### 4. **Integration with Valora AI Chat**
```python
# In multi_agent_orchestrator.py - add visual analysis

def analyze_property_with_image(property_id: str):
    """Enhance property analysis with image data."""
    images = image_service.get_images_for_property(property_id)
    
    if images:
        # Use Qwen3-VL to analyze property image
        analysis = qwen_model.analyze(images[0]['image_path'])
        return {
            "visual_analysis": analysis,
            "metadata": images[0]
        }
```

## 🔄 Expanding the Dataset

### Download More Images
```bash
# Download all available images (5,399 properties)
python scripts/download_property_images.py --download --limit 5399 --max-images 5

# This will give you ~15,000+ images
```

### Download by Source
```bash
# Prioritize specific sources
python scripts/download_property_images.py --download --source magicbricks --limit 3000
```

### Batch Processing
```bash
# Download in batches to avoid timeouts
for i in {0..10}; do
    python scripts/download_property_images.py --download --offset $((i*500)) --limit 500
done
```

## 📈 Training Recommendations

### For Qwen3-VL (2B parameters)
- **Batch Size**: 2 per device
- **Gradient Accumulation**: 8 steps
- **Learning Rate**: 1e-5 with warmup
- **Epochs**: 3-5 epochs
- **Hardware**: RTX 3090/4090 or A100 (16GB+ VRAM)
- **Training Time**: ~2-4 hours for 496 images

### Data Augmentation
```python
from torchvision import transforms

transform = transforms.Compose([
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomRotation(degrees=5),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
    transforms.RandomResizedCrop(size=224, scale=(0.8, 1.0)),
    transforms.ToTensor(),
])
```

### Evaluation Metrics
```python
# Track these during training:
- BLEU score (text generation quality)
- Image-text retrieval accuracy
- Price prediction MAE
- Property type classification accuracy
```

## 🔗 Integration Points

### 1. **Backend AI Agents**
Images are now available to all AI agents for visual reasoning:
- Property Agent: Visual property assessment
- Valuation Agent: Image-based pricing
- Spatial Agent: Visual neighborhood analysis
- Simulation Agent: Visual impact prediction

### 2. **Frontend UI**
Add image display in property cards:
```javascript
// In PropertyCard.jsx
const imageUrl = `/api/images/file/${property.property_id}/${filename}`;
<img src={imageUrl} alt={property.title} />
```

### 3. **Chat Interface**
Enable visual Q&A:
```
User: "Show me properties similar to this image"
Agent: [Uses image similarity search]
      "Found 5 similar properties in your area..."
```

## 📝 Next Steps

1. ✅ **Completed**: Download & organize 496 images
2. ✅ **Completed**: Create training data formats
3. ✅ **Completed**: Set up API endpoints
4. 🎯 **Next**: Fine-tune Qwen3-VL on property images
5. 🎯 **Next**: Integrate visual analysis into chat agents
6. 🎯 **Next**: Download remaining ~15K images
7. 🎯 **Next**: Build custom property vision models

## 🛠️ Troubleshooting

### Images not downloading?
```bash
# Check database connection
python scripts/check_db.py

# Verify image URLs
python scripts/check_images.py

# Test download with small batch
python scripts/download_property_images.py --download --limit 10
```

### Training data not loading?
```python
# Verify paths in training data
import json
with open('data/property_images/qwen_training/train.json') as f:
    data = json.load(f)
    print(data[0]['messages'][0]['content'][0]['image'])
```

### API not responding?
```bash
# Check if image service initialized
# Look for: "[OK] Property image service initialized (496 images)"
# in backend startup logs
```

## 📚 References

- **Qwen3-VL Documentation**: https://huggingface.co/Qwen/Qwen2-VL-2B-Instruct
- **Property Image Service**: `backend/services/property_image_service.py`
- **Download Script**: `scripts/download_property_images.py`
- **Training Prep**: `scripts/prepare_vl_training.py`
- **Dataset README**: `data/property_images/README.md`

---

**Status**: ✅ Ready for AI training  
**Images**: 496 downloaded and mapped  
**Training Data**: 446 train + 50 eval examples  
**API**: 8 endpoints available  
**Last Updated**: January 30, 2026
