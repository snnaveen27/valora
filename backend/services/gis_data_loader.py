import os
import sys
import argparse
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional

import geopandas as gpd
from shapely.geometry import box
from sqlalchemy import create_engine, text

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("gis_loader")

# Default Bangalore bbox (minx, miny, maxx, maxy)
BANGALORE_BBOX = (77.35, 12.75, 77.85, 13.20)

# Skip patterns (extremely large OSM layers)
SKIP_PATTERNS = [
    r"^gis_osm_roads_",
    r"^gis_osm_buildings_",
    r"^gis_osm_waterways_",
    r"^gis_osm_water_a_",
    r"^gis_osm_pois_",
]

SIZE_SKIP_BYTES = 250 * 1024 * 1024  # 250MB


def sanitize_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"[^a-z0-9_]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    if not name:
        name = "layer"
    # ensure it starts with a letter
    if not re.match(r"^[a-z]", name):
        name = f"t_{name}"
    return name[:60]


def should_skip_by_pattern(stem: str) -> bool:
    for pat in SKIP_PATTERNS:
        if re.match(pat, stem):
            return True
    return False


def detect_crs(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    if gdf.crs is None:
        # Assume WGS84 if missing
        logger.warning("CRS missing; assuming EPSG:4326 (WGS84)")
        gdf.set_crs(epsg=4326, inplace=True)
    return gdf


def reproject_to_wgs84(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = detect_crs(gdf)
    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    return gdf


def clip_to_bbox(gdf: gpd.GeoDataFrame, bbox: Tuple[float, float, float, float]) -> gpd.GeoDataFrame:
    gdf = reproject_to_wgs84(gdf)
    geom_bbox = box(*bbox)
    mask = gdf.geometry.intersects(geom_bbox)
    return gdf.loc[mask]


def create_spatial_index(engine, table: str, geom_col: str = "geom"):
    idx_name = sanitize_name(f"idx_{table}_{geom_col}_gist")
    sql = text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table} USING GIST({geom_col});")
    with engine.begin() as conn:
        conn.execute(sql)


def write_layer(engine, gdf: gpd.GeoDataFrame, table_name: str, if_exists: str = "replace"):
    if gdf.empty or gdf.geometry.is_empty.all():
        logger.warning(f"{table_name}: empty geometry; skipping")
        return
    gdf = reproject_to_wgs84(gdf)
    # lineage columns
    gdf = gdf.copy()
    # ensure geometry column is named 'geom'
    try:
        if getattr(gdf, "geometry", None) is not None and gdf.geometry.name != "geom":
            gdf = gdf.rename_geometry("geom")
    except Exception:
        pass
    gdf["ingested_at"] = datetime.utcnow()
    # Write to PostGIS
    gdf.to_postgis(table_name, engine, if_exists=if_exists, index=False, dtype=None)
    create_spatial_index(engine, table_name, "geom")
    logger.info(f"Wrote {len(gdf)} features to {table_name}")


def load_kml(engine, path: Path, table_prefix: str, bbox: Optional[Tuple[float, float, float, float]]):
    import fiona
    try:
        layers = fiona.listlayers(str(path))
    except Exception as e:
        logger.error(f"Could not list KML layers for {path.name}: {e}")
        return
    for layer in layers:
        try:
            gdf = gpd.read_file(str(path), layer=layer)
            if bbox:
                gdf = clip_to_bbox(gdf, bbox)
            table = sanitize_name(f"{table_prefix}_{layer}")
            write_layer(engine, gdf, table, if_exists="replace")
        except Exception as e:
            logger.warning(f"Failed to load KML layer {layer} from {path.name}: {e}")


def load_vector(engine, path: Path, table_prefix: str, bbox: Optional[Tuple[float, float, float, float]]):
    try:
        gdf = gpd.read_file(str(path))
        if bbox:
            gdf = clip_to_bbox(gdf, bbox)
        table = sanitize_name(table_prefix)
        write_layer(engine, gdf, table, if_exists="replace")
    except Exception as e:
        logger.warning(f"Failed to load vector {path.name}: {e}")


def main():
    parser = argparse.ArgumentParser(description="Load GIS files into PostGIS")
    parser.add_argument("--path", default=str(Path("data/raw/gis").resolve()), help="Folder containing GIS files")
    parser.add_argument("--db", default=os.getenv("SPATIAL_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/realestate_spatial"), help="PostGIS database URL")
    parser.add_argument("--bbox", default="bangalore", help="minx,miny,maxx,maxy or 'bangalore' or 'none'")
    parser.add_argument("--include-large", action="store_true", help="Attempt to load very large OSM layers (may be slow)")
    args = parser.parse_args()

    folder = Path(args.path)
    if not folder.exists():
        logger.error(f"Path not found: {folder}")
        sys.exit(1)

    if args.bbox == "bangalore":
        bbox = BANGALORE_BBOX
    elif args.bbox == "none":
        bbox = None
    else:
        parts = [float(x) for x in args.bbox.split(",")]
        if len(parts) != 4:
            logger.error("--bbox must be 'bangalore', 'none', or 'minx,miny,maxx,maxy'")
            sys.exit(1)
        bbox = tuple(parts)  # type: ignore

    engine = create_engine(args.db)

    # Collect files
    files: List[Path] = []
    exts = {".geojson", ".json", ".shp", ".kml"}
    for p in folder.iterdir():
        if p.suffix.lower() in exts:
            files.append(p)
        if p.suffix.lower() == ".pbf":
            logger.warning(f"Skipping OSM PBF (use osm2pgsql/pyrosm): {p.name}")

    # Group shapefile components (.shp)
    unique_files: List[Path] = []
    seen = set()
    for f in files:
        if f.suffix.lower() == ".shp":
            if f.stem in seen:
                continue
            seen.add(f.stem)
            unique_files.append(f)
        elif f.suffix.lower() in {".geojson", ".json", ".kml"}:
            unique_files.append(f)

    # Load
    for f in sorted(unique_files):
        stem = sanitize_name(f.stem)
        if should_skip_by_pattern(stem) and not args.include_large:
            logger.info(f"Skipping large OSM layer by pattern: {f.name}")
            continue
        try:
            size = f.stat().st_size
        except Exception:
            size = 0
        if (size and size > SIZE_SKIP_BYTES) and not args.include_large:
            logger.info(f"Skipping large file ({size/1e6:.1f} MB): {f.name}")
            continue

        logger.info(f"Loading {f.name} -> table prefix 'gis_{stem}'")
        table_prefix = f"gis_{stem}"
        if f.suffix.lower() == ".kml":
            load_kml(engine, f, table_prefix, bbox)
        else:
            load_vector(engine, f, table_prefix, bbox)

    logger.info("GIS loading complete")


if __name__ == "__main__":
    main()
