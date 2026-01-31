"""
Prepare Property Images for Qwen3-VL Training
Generates training data in format compatible with Qwen3-VL fine-tuning.
"""

import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from services.property_image_service import get_image_service


def create_training_config(output_dir: Path):
    """Create training configuration file."""
    config = {
        "model_name": "Qwen/Qwen2-VL-2B-Instruct",
        "output_dir": str(output_dir / "checkpoints"),
        "num_train_epochs": 3,
        "per_device_train_batch_size": 2,
        "gradient_accumulation_steps": 8,
        "learning_rate": 1e-5,
        "warmup_steps": 100,
        "logging_steps": 10,
        "save_steps": 100,
        "eval_steps": 100,
        "save_total_limit": 3,
        "fp16": True,
        "dataloader_num_workers": 4,
        "remove_unused_columns": False,
        "dataset": {
            "train": str(output_dir / "train.json"),
            "eval": str(output_dir / "eval.json"),
            "format": "conversations"
        }
    }
    
    config_path = output_dir / "training_config.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"✅ Created training config: {config_path}")
    return config_path


def prepare_qwen_format(image_service, output_dir: Path, train_split: float = 0.9):
    """
    Prepare training data in Qwen3-VL format.
    
    Format expected by Qwen3-VL:
    {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": "path/to/image.jpg"},
                    {"type": "text", "text": "What property is this?"}
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "This is a 2BHK apartment..."}
                ]
            }
        ]
    }
    """
    print("\n📦 Preparing Qwen3-VL training data...")
    
    # Get all training data
    data = image_service.training_data
    
    if not data:
        print("❌ No training data available. Run download script first.")
        return
    
    # Create training examples
    examples = []
    for record in data:
        # Get property details
        prop_type = record.get('property_type', 'Property')
        bedrooms = record.get('bedrooms')
        area = record.get('area_sqft')
        price = record.get('price')
        locality = record.get('locality')
        listing = record.get('listing_type')
        
        # Build description
        description_parts = []
        
        if prop_type:
            description_parts.append(prop_type.strip())
        
        if bedrooms:
            description_parts.append(f"with {bedrooms} bedrooms")
        
        if area:
            description_parts.append(f"spanning {area:.0f} square feet")
        
        if price:
            if price >= 10000000:
                price_str = f"₹{price/10000000:.2f} crore"
            elif price >= 100000:
                price_str = f"₹{price/100000:.2f} lakh"
            else:
                price_str = f"₹{price:.0f}"
            
            if listing == 'rent':
                description_parts.append(f"available for rent at {price_str}/month")
            else:
                description_parts.append(f"priced at {price_str}")
        
        if locality:
            description_parts.append(f"located in {locality}")
        
        description = ". ".join(description_parts) + "."
        
        # Create example in Qwen format
        example = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": record['image_path']},
                        {"type": "text", "text": "Describe this property in detail."}
                    ]
                },
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": description}
                    ]
                }
            ]
        }
        
        examples.append(example)
    
    # Split into train/eval
    split_idx = int(len(examples) * train_split)
    train_data = examples[:split_idx]
    eval_data = examples[split_idx:]
    
    # Save splits
    train_path = output_dir / "train.json"
    eval_path = output_dir / "eval.json"
    
    with open(train_path, 'w', encoding='utf-8') as f:
        json.dump(train_data, f, indent=2, ensure_ascii=False)
    
    with open(eval_path, 'w', encoding='utf-8') as f:
        json.dump(eval_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Training set: {len(train_data)} examples → {train_path}")
    print(f"✅ Evaluation set: {len(eval_data)} examples → {eval_path}")
    
    # Show sample
    print(f"\n📄 Sample training example:")
    print(json.dumps(train_data[0], indent=2, ensure_ascii=False)[:500] + "...")
    
    return train_path, eval_path


def create_simple_format(image_service, output_dir: Path):
    """
    Create simple image-caption pairs for basic VL training.
    
    Format:
    {
        "image": "path/to/image.jpg",
        "caption": "2BHK apartment for rent at ₹25,000/month in Bangalore"
    }
    """
    print("\n📦 Creating simple format...")
    
    simple_data = []
    for record in image_service.training_data:
        # Build caption
        parts = []
        if record.get('bedrooms'):
            parts.append(f"{record['bedrooms']}BHK")
        if record.get('property_type'):
            parts.append(record['property_type'].strip())
        if record.get('listing_type'):
            parts.append(f"for {record['listing_type']}")
        if record.get('price'):
            price = record['price']
            if price >= 10000000:
                parts.append(f"at ₹{price/10000000:.1f}Cr")
            elif price >= 100000:
                parts.append(f"at ₹{price/100000:.1f}L")
        if record.get('locality'):
            parts.append(f"in {record['locality']}")
        
        caption = " ".join(parts)
        
        simple_data.append({
            "image": record['image_path'],
            "caption": caption,
            "metadata": {
                "property_id": record['property_id'],
                "bedrooms": record.get('bedrooms'),
                "price": record.get('price'),
                "coordinates": {
                    "lat": record.get('latitude'),
                    "lng": record.get('longitude')
                }
            }
        })
    
    output_path = output_dir / "simple_format.jsonl"
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in simple_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"✅ Simple format: {len(simple_data)} examples → {output_path}")
    return output_path


def create_jupyter_loader(output_dir: Path):
    """Create helper code for loading data in Jupyter notebooks."""
    code = '''"""
Property Image Dataset Loader
Use this in your Jupyter notebook to load the training data.
"""

import json
from pathlib import Path
from PIL import Image
import torch
from torch.utils.data import Dataset

class PropertyImageDataset(Dataset):
    """Dataset for property images with metadata."""
    
    def __init__(self, json_path, transform=None):
        self.data = []
        with open(json_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.transform = transform
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        
        # Load image
        image_path = Path(item['messages'][0]['content'][0]['image'])
        image = Image.open(image_path).convert('RGB')
        
        if self.transform:
            image = self.transform(image)
        
        # Get text
        prompt = item['messages'][0]['content'][1]['text']
        response = item['messages'][1]['content'][0]['text']
        
        return {
            'image': image,
            'prompt': prompt,
            'response': response
        }

# Example usage:
# from property_dataset import PropertyImageDataset
# dataset = PropertyImageDataset('data/property_images/qwen_training/train.json')
# print(f"Dataset size: {len(dataset)}")
# sample = dataset[0]
# print(f"Prompt: {sample['prompt']}")
# print(f"Response: {sample['response']}")
'''
    
    loader_path = output_dir / "property_dataset.py"
    with open(loader_path, 'w') as f:
        f.write(code)
    
    print(f"✅ Created dataset loader: {loader_path}")
    return loader_path


def generate_statistics(image_service, output_dir: Path):
    """Generate detailed statistics about the dataset."""
    stats = image_service.get_stats()
    
    # Enhanced statistics
    data = image_service.training_data
    
    # Price distribution
    prices = [r['price'] for r in data if r.get('price')]
    if prices:
        price_stats = {
            "min": min(prices),
            "max": max(prices),
            "avg": sum(prices) / len(prices),
            "median": sorted(prices)[len(prices)//2]
        }
    else:
        price_stats = {}
    
    # Bedroom distribution
    bedroom_dist = {}
    for r in data:
        beds = r.get('bedrooms', 'unknown')
        bedroom_dist[beds] = bedroom_dist.get(beds, 0) + 1
    
    # Area distribution
    areas = [r['area_sqft'] for r in data if r.get('area_sqft')]
    if areas:
        area_stats = {
            "min": min(areas),
            "max": max(areas),
            "avg": sum(areas) / len(areas)
        }
    else:
        area_stats = {}
    
    enhanced_stats = {
        **stats,
        "price_statistics": price_stats,
        "bedroom_distribution": bedroom_dist,
        "area_statistics": area_stats,
        "coordinates_coverage": sum(1 for r in data if r.get('latitude') and r.get('longitude'))
    }
    
    stats_path = output_dir / "dataset_statistics.json"
    with open(stats_path, 'w') as f:
        json.dump(enhanced_stats, f, indent=2)
    
    print(f"✅ Generated statistics: {stats_path}")
    
    # Print summary
    print(f"\n📊 Dataset Statistics:")
    print(f"   Total images: {len(data)}")
    print(f"   With coordinates: {enhanced_stats['coordinates_coverage']}")
    if price_stats:
        print(f"   Price range: ₹{price_stats['min']:,.0f} - ₹{price_stats['max']:,.0f}")
        print(f"   Average price: ₹{price_stats['avg']:,.0f}")
    if bedroom_dist:
        print(f"   Bedroom distribution: {bedroom_dist}")
    
    return stats_path


def main():
    """Main preparation workflow."""
    print("="*60)
    print("PROPERTY IMAGE TRAINING DATA PREPARATION")
    print("="*60)
    
    # Initialize service
    print("\n🔄 Loading image service...")
    image_service = get_image_service()
    
    if not image_service.training_data:
        print("\n❌ No training data found!")
        print("   Run: python scripts/download_property_images.py --download --limit 500")
        return
    
    # Create output directory
    output_dir = Path(__file__).parent.parent / "data" / "property_images" / "qwen_training"
    output_dir.mkdir(exist_ok=True)
    
    # Prepare Qwen format
    train_path, eval_path = prepare_qwen_format(image_service, output_dir)
    
    # Create simple format
    simple_path = create_simple_format(image_service, output_dir)
    
    # Create dataset loader
    loader_path = create_jupyter_loader(output_dir)
    
    # Create training config
    config_path = create_training_config(output_dir)
    
    # Generate statistics
    stats_path = generate_statistics(image_service, output_dir)
    
    print("\n" + "="*60)
    print("✅ PREPARATION COMPLETE")
    print("="*60)
    print(f"\n📁 Output directory: {output_dir}")
    print(f"\n🎯 Next steps:")
    print(f"   1. Review training data: {train_path}")
    print(f"   2. Check statistics: {stats_path}")
    print(f"   3. Use in notebook: from property_dataset import PropertyImageDataset")
    print(f"   4. Start training with config: {config_path}")
    print(f"\n📓 For Qwen3-VL notebook:")
    print(f"   - Load data: PropertyImageDataset('{train_path}')")
    print(f"   - Training examples: {len(image_service.training_data) * 0.9:.0f}")
    print(f"   - Evaluation examples: {len(image_service.training_data) * 0.1:.0f}")


if __name__ == "__main__":
    main()
