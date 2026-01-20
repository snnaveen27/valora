"""
Extract and process DEM (Digital Elevation Model) data for Bengaluru
Generates elevation tiles, slope, aspect, and hillshade for terrain analysis
"""

import rasterio
import numpy as np
import json
from pathlib import Path
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.enums import ColorInterp
import math

def calculate_slope_aspect(elevation_data, transform):
    """Calculate slope and aspect from elevation data"""
    # Get cell size in meters (approximate for lat/lng)
    cell_size_x = abs(transform[0]) * 111320  # degrees to meters at equator
    cell_size_y = abs(transform[4]) * 111320
    
    # Calculate gradients
    dz_dx = np.gradient(elevation_data, axis=1) / cell_size_x
    dz_dy = np.gradient(elevation_data, axis=0) / cell_size_y
    
    # Calculate slope (in degrees)
    slope = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2)) * 180 / np.pi
    
    # Calculate aspect (in degrees, 0=North, 90=East, 180=South, 270=West)
    aspect = np.arctan2(-dz_dy, dz_dx) * 180 / np.pi
    aspect = (90 - aspect) % 360
    
    return slope, aspect

def calculate_hillshade(elevation_data, transform, azimuth=315, altitude=45):
    """Calculate hillshade for visualization"""
    cell_size_x = abs(transform[0]) * 111320
    cell_size_y = abs(transform[4]) * 111320
    
    dz_dx = np.gradient(elevation_data, axis=1) / cell_size_x
    dz_dy = np.gradient(elevation_data, axis=0) / cell_size_y
    
    slope = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
    aspect = np.arctan2(-dz_dy, dz_dx)
    
    azimuth_rad = azimuth * np.pi / 180
    altitude_rad = altitude * np.pi / 180
    
    hillshade = 255 * (
        (np.cos(altitude_rad) * np.cos(slope)) +
        (np.sin(altitude_rad) * np.sin(slope) * np.cos(azimuth_rad - aspect))
    )
    
    hillshade = np.clip(hillshade, 0, 255).astype(np.uint8)
    return hillshade

def create_elevation_tiles(dem_path, output_dir, tile_size_deg=0.05):
    """Create tiled elevation data for efficient querying"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("📊 Processing DEM data...")
    
    with rasterio.open(dem_path) as src:
        bounds = src.bounds
        width = src.width
        height = src.height
        transform = src.transform
        crs = src.crs
        
        print(f"   DEM Size: {width}x{height}")
        print(f"   Bounds: {bounds}")
        print(f"   CRS: {crs}")
        
        # Read full elevation data
        elevation = src.read(1)
        
        # Replace nodata values with NaN
        if src.nodata is not None:
            elevation[elevation == src.nodata] = np.nan
        
        # Calculate derived products
        print("   Calculating slope and aspect...")
        slope, aspect = calculate_slope_aspect(elevation, transform)
        
        print("   Calculating hillshade...")
        hillshade = calculate_hillshade(elevation, transform)
        
        # Get statistics
        valid_elevation = elevation[~np.isnan(elevation)]
        stats = {
            'min_elevation': float(np.min(valid_elevation)),
            'max_elevation': float(np.max(valid_elevation)),
            'mean_elevation': float(np.mean(valid_elevation)),
            'std_elevation': float(np.std(valid_elevation)),
            'bounds': {
                'west': bounds.left,
                'south': bounds.bottom,
                'east': bounds.right,
                'north': bounds.top
            },
            'width': width,
            'height': height,
            'resolution': abs(transform[0])
        }
        
        print(f"   Elevation range: {stats['min_elevation']:.1f}m - {stats['max_elevation']:.1f}m")
        print(f"   Mean elevation: {stats['mean_elevation']:.1f}m")
        
        # Create tiles
        print(f"\n🗺️  Creating elevation tiles (tile size: {tile_size_deg}°)...")
        
        tiles = []
        tile_id = 0
        
        lat_start = bounds.bottom
        while lat_start < bounds.top:
            lat_end = min(lat_start + tile_size_deg, bounds.top)
            
            lng_start = bounds.left
            while lng_start < bounds.right:
                lng_end = min(lng_start + tile_size_deg, bounds.right)
                
                # Calculate pixel coordinates
                row_start = int((bounds.top - lat_end) / abs(transform[4]))
                row_end = int((bounds.top - lat_start) / abs(transform[4]))
                col_start = int((lng_start - bounds.left) / abs(transform[0]))
                col_end = int((lng_end - bounds.left) / abs(transform[0]))
                
                # Clip to valid range
                row_start = max(0, min(row_start, height))
                row_end = max(0, min(row_end, height))
                col_start = max(0, min(col_start, width))
                col_end = max(0, min(col_end, width))
                
                if row_start < row_end and col_start < col_end:
                    tile_elevation = elevation[row_start:row_end, col_start:col_end]
                    tile_slope = slope[row_start:row_end, col_start:col_end]
                    tile_aspect = aspect[row_start:row_end, col_start:col_end]
                    
                    # Skip tiles with all NaN
                    if not np.all(np.isnan(tile_elevation)):
                        tile_data = {
                            'tile_id': tile_id,
                            'bounds': {
                                'west': lng_start,
                                'south': lat_start,
                                'east': lng_end,
                                'north': lat_end
                            },
                            'center': {
                                'lat': (lat_start + lat_end) / 2,
                                'lng': (lng_start + lng_end) / 2
                            },
                            'elevation': {
                                'min': float(np.nanmin(tile_elevation)),
                                'max': float(np.nanmax(tile_elevation)),
                                'mean': float(np.nanmean(tile_elevation))
                            },
                            'slope': {
                                'min': float(np.nanmin(tile_slope)),
                                'max': float(np.nanmax(tile_slope)),
                                'mean': float(np.nanmean(tile_slope))
                            }
                        }
                        
                        tiles.append(tile_data)
                        tile_id += 1
                
                lng_start = lng_end
            lat_start = lat_end
        
        print(f"   Created {len(tiles)} tiles")
        
        # Save tile index
        index_file = output_dir / 'elevation_index.json'
        index_data = {
            'stats': stats,
            'tile_count': len(tiles),
            'tile_size_deg': tile_size_deg,
            'tiles': tiles
        }
        
        with open(index_file, 'w') as f:
            json.dump(index_data, f, indent=2)
        
        print(f"   Saved tile index: {index_file}")
        
        # Save derived products as GeoTIFF
        print("\n💾 Saving derived products...")
        
        # Save slope
        slope_file = output_dir / 'slope.tif'
        with rasterio.open(
            slope_file, 'w',
            driver='GTiff',
            height=height,
            width=width,
            count=1,
            dtype=slope.dtype,
            crs=crs,
            transform=transform,
            compress='lzw'
        ) as dst:
            dst.write(slope, 1)
        print(f"   ✅ Slope: {slope_file}")
        
        # Save aspect
        aspect_file = output_dir / 'aspect.tif'
        with rasterio.open(
            aspect_file, 'w',
            driver='GTiff',
            height=height,
            width=width,
            count=1,
            dtype=aspect.dtype,
            crs=crs,
            transform=transform,
            compress='lzw'
        ) as dst:
            dst.write(aspect, 1)
        print(f"   ✅ Aspect: {aspect_file}")
        
        # Save hillshade
        hillshade_file = output_dir / 'hillshade.tif'
        with rasterio.open(
            hillshade_file, 'w',
            driver='GTiff',
            height=height,
            width=width,
            count=1,
            dtype=hillshade.dtype,
            crs=crs,
            transform=transform,
            compress='lzw'
        ) as dst:
            dst.write(hillshade, 1)
        print(f"   ✅ Hillshade: {hillshade_file}")
        
        return index_data

def main():
    print("🏔️  DEM Data Extraction for Bengaluru")
    print("=" * 60)
    
    dem_path = Path(__file__).parent.parent / 'src' / 'data' / 'dem_bengaluru.tif'
    output_dir = Path(__file__).parent.parent / 'src' / 'data' / 'terrain'
    
    if not dem_path.exists():
        print(f"❌ DEM file not found: {dem_path}")
        return
    
    print(f"📂 Input: {dem_path}")
    print(f"📁 Output: {output_dir}")
    print()
    
    index_data = create_elevation_tiles(dem_path, output_dir, tile_size_deg=0.05)
    
    print(f"\n✅ DEM extraction complete!")
    print(f"📊 Statistics:")
    print(f"   Elevation range: {index_data['stats']['min_elevation']:.1f}m - {index_data['stats']['max_elevation']:.1f}m")
    print(f"   Mean elevation: {index_data['stats']['mean_elevation']:.1f}m")
    print(f"   Tiles created: {index_data['tile_count']}")
    print(f"\n📁 Output directory: {output_dir}")

if __name__ == '__main__':
    main()
