"""
Apify Dataset Downloader
Downloads all datasets from your Apify account to local storage.
"""

import os
import requests
import json
from pathlib import Path
from datetime import datetime
import time
from dotenv import load_dotenv

load_dotenv()

APIFY_API_TOKEN = os.environ.get('APIFY_API_TOKEN', '')

DATASET_IDS = [
    'wuN0jzpUUw6BIcSNE', 'rs0mtMOnndcONCAcQ', 'FRrgWHy7HY1eLkpvc', 'Fb5XyOUTK04QSfO6K',
    'sbwhpGul3tq7tK6uI', 'xx43GLW0OMB5Jq5k5', '1doogGgQShD8u4n0T', 'mlUdNiizF3CHiLgJ5',
    'fyC83AFcRL4SegZXA', '2U7TKPDGrSHOeEp8L', 'LIzICqz0MdTjii9pq', '0EcdFox4qorYUov4S',
    '9BWqsNMtJQq06b2PR', 'mUsQii0Ih66zQ7rT0', 'mCbanObYFUQ5rH04h', 'OXZ3c9LF9qgnfdPLf',
    'xFPl03QSJhxNpg1e0', '2hGjIbfXYafH4sGaz', 'Tt956ZfmmMlW9ThpB', 'EXgVR2OLEJRrIFgum',
    'LfVGDatvC2kByLJ4g', '3sWb8ryj155gVw8iW', 'ZSKx6JKoAdpTYF4yC', 'cW8svXCRI5CE2Bagl',
    'A0tBDZaBkOCmydpy3', '0KHIKpzBG559RoRvj', 'jXy96uNGHhqLm0kpz', '1VYJAA4qbeyYTkcAb',
    '71p3jvg0NplhQfkKB', 'AbNBf6B4Vk4deXOsE', '0Dm80ER5QgB5bXC7o', 'TA47qaGOCfPQXRoG3',
    'hL3zhvrez7sWZn4sy', 'c4XTT1Z97xeYfFjnX', '6WNFv7ZdTliVcchLJ', 'ZBr7WqXe2iFZY1CuA',
    'OsA8AzHVOlIqTv67S', 'vAxlYgbiG7Ib7E69E', 'AelReZuW1PQPcIMsx', 'HXrJ6Axqdbg1tZinq',
    'weMmi5cB00CdtODS4', 'ij6j98Pvfs5OXhspA', 'qonFwMGgjCC75DIbJ', 'hHIcngCm4x1vmt1xq',
    'jE6OQzqoQL9taWAgI', 'fM2DUJAJyJXAkqX0V', '1VRO7zlbSFrjzYnaj', 'zdVD1T1i5632LWX77',
    'CknPafZmt8rgRCxYd', 'XqCWtGji3wPUWq41V', 'U8wyIZjHAyQewv3Yv', 'C9LY1h4SOgrhpbeYK',
    'DvryymYjOaO1aUWc9', 'Dgaceu34pKrqS9twv', 'aBRxmlrTqenmJ1wZn', 'VIhsB0L3FvcZgU620',
    'R74I7PWyPCu9TqkGI', '19TXqaJuJuARFjHib'
]

def download_dataset(dataset_id: str, output_dir: Path, format: str = 'json'):
    """
    Download a single dataset from Apify.
    
    Args:
        dataset_id: The Apify dataset ID
        output_dir: Directory to save the dataset
        format: Output format (json, csv, xlsx, html, jsonl)
    
    Returns:
        Tuple of (success: bool, record_count: int)
    """
    url = f'https://api.apify.com/v2/datasets/{dataset_id}/items'
    params = {
        'token': APIFY_API_TOKEN,
        'format': format
    }
    
    try:
        print(f'Downloading dataset {dataset_id}...')
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        
        output_file = output_dir / f'{dataset_id}.{format}'
        record_count = 0
        
        if format == 'json':
            data = response.json()
            record_count = len(data)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f'✓ Saved {record_count} records to {output_file}')
        else:
            with open(output_file, 'wb') as f:
                f.write(response.content)
            print(f'✓ Saved to {output_file}')
        
        return True, record_count
        
    except requests.exceptions.RequestException as e:
        print(f'✗ Error downloading {dataset_id}: {e}')
        return False, 0
    except Exception as e:
        print(f'✗ Unexpected error for {dataset_id}: {e}')
        return False, 0

def download_all_datasets(output_dir: str = 'data/posted_properties', format: str = 'json', delay: float = 0.5):
    """
    Download all datasets from Apify.
    
    Args:
        output_dir: Directory to save all datasets
        format: Output format (json, csv, xlsx, html, jsonl)
        delay: Delay between requests in seconds to avoid rate limiting
    """
    if not APIFY_API_TOKEN:
        print('ERROR: APIFY_API_TOKEN environment variable not set!')
        print('Please set it using: set APIFY_API_TOKEN=your_token_here')
        return
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print(f'Starting download of {len(DATASET_IDS)} datasets...')
    print(f'Output directory: {output_path.absolute()}')
    print(f'Format: {format}')
    print('-' * 60)
    
    successful = 0
    failed = 0
    total_records = 0
    dataset_records = []
    
    for i, dataset_id in enumerate(DATASET_IDS, 1):
        print(f'[{i}/{len(DATASET_IDS)}] ', end='')
        
        success, record_count = download_dataset(dataset_id, output_path, format)
        if success:
            successful += 1
            total_records += record_count
            dataset_records.append((dataset_id, record_count))
        else:
            failed += 1
        
        if i < len(DATASET_IDS):
            time.sleep(delay)
    
    print('-' * 60)
    print(f'Download complete!')
    print(f'✓ Successful: {successful}')
    print(f'✗ Failed: {failed}')
    print(f'Total datasets: {len(DATASET_IDS)}')
    print(f'\n📊 TOTAL RECORDS DOWNLOADED: {total_records:,}')
    print('-' * 60)
    
    summary_file = output_path / 'download_summary.txt'
    with open(summary_file, 'w') as f:
        f.write(f'Apify Dataset Download Summary\n')
        f.write(f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
        f.write(f'=' * 60 + '\n\n')
        f.write(f'Total datasets: {len(DATASET_IDS)}\n')
        f.write(f'Successful: {successful}\n')
        f.write(f'Failed: {failed}\n')
        f.write(f'Format: {format}\n')
        f.write(f'\nTOTAL RECORDS: {total_records:,}\n')
        f.write(f'\n' + '=' * 60 + '\n')
        f.write(f'\nDataset Details:\n')
        f.write(f'-' * 60 + '\n')
        for dataset_id, count in dataset_records:
            f.write(f'{dataset_id}: {count:,} records\n')
    
    print(f'\nSummary saved to: {summary_file}')

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Download all datasets from Apify')
    parser.add_argument('--output', '-o', default='data/posted_properties', help='Output directory (default: data/posted_properties)')
    parser.add_argument('--format', '-f', default='json', choices=['json', 'csv', 'xlsx', 'html', 'jsonl'], help='Output format (default: json)')
    parser.add_argument('--delay', '-d', type=float, default=0.5, help='Delay between requests in seconds (default: 0.5)')
    
    args = parser.parse_args()
    
    download_all_datasets(args.output, args.format, args.delay)
