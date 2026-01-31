"""
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
