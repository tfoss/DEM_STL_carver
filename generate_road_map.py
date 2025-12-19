#!/usr/bin/env python3
"""
Generate a 2D road map image for projecting onto terrain mesh in Fusion 360.
Creates a black/white image where roads are white lines on black background.
"""
import argparse
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import rasterio
from rasterio.features import rasterize


def generate_road_map(dem_file, roads_geojson, output_image, road_width_px=3, dpi=300):
    """
    Generate a road map image that exactly matches the DEM bounds and resolution.

    Args:
        dem_file: Path to DEM GeoTIFF file
        roads_geojson: Path to roads GeoJSON file
        output_image: Output PNG filename
        road_width_px: Width of roads in pixels (default: 3)
        dpi: DPI for output image (default: 300 for high quality)
    """
    print(f"Loading DEM: {dem_file}")

    # Load DEM to get exact dimensions and transform
    with rasterio.open(dem_file) as src:
        dem_shape = src.shape
        transform = src.transform
        bounds = src.bounds

    print(f"DEM dimensions: {dem_shape[1]} x {dem_shape[0]} pixels")
    print(f"DEM bounds: {bounds}")

    # Load roads
    print(f"Loading roads: {roads_geojson}")
    roads_gdf = gpd.read_file(roads_geojson)
    if roads_gdf.crs is None:
        roads_gdf.set_crs('EPSG:4326', inplace=True)

    print(f"Found {len(roads_gdf)} road segments")

    # Create a blank image (black background)
    road_map = np.zeros(dem_shape, dtype=np.uint8)

    # Rasterize roads onto the image (white lines)
    # We'll use a simple approach: rasterize with a buffer
    from shapely.geometry import LineString

    # Calculate appropriate buffer in degrees for road width
    # Approximate: 1 pixel = transform resolution
    pixel_width_deg = abs(transform[0])
    buffer_deg = pixel_width_deg * (road_width_px / 2)

    print(f"Road width: {road_width_px} pixels (~{buffer_deg * 111000:.1f}m)")

    # Buffer roads to create width
    roads_buffered = roads_gdf.copy()
    roads_buffered['geometry'] = roads_buffered.geometry.buffer(buffer_deg)

    # Rasterize buffered roads
    shapes = [(geom, 255) for geom in roads_buffered.geometry]  # 255 = white

    road_map = rasterize(
        shapes,
        out_shape=dem_shape,
        transform=transform,
        fill=0,  # Black background
        dtype=np.uint8
    )

    print(f"Roads rasterized: {np.sum(road_map > 0)} pixels")

    # Save as high-quality PNG
    fig, ax = plt.subplots(figsize=(dem_shape[1]/dpi, dem_shape[0]/dpi), dpi=dpi)
    ax.imshow(road_map, cmap='gray', vmin=0, vmax=255, interpolation='nearest')
    ax.axis('off')
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0, wspace=0, hspace=0)

    plt.savefig(output_image, dpi=dpi, bbox_inches='tight', pad_inches=0,
                facecolor='black', edgecolor='none')
    plt.close()

    print(f"\nRoad map saved to: {output_image}")
    print(f"Image size: {dem_shape[1]} x {dem_shape[0]} pixels at {dpi} DPI")
    print(f"\nNext steps in Fusion 360:")
    print("1. Import your terrain STL")
    print("2. Convert mesh to BRep (Mesh > Convert Mesh)")
    print("3. Create a sketch on a plane above the terrain")
    print("4. Insert > Canvas > Insert from My Computer")
    print("5. Select this road map PNG and scale to match terrain size")
    print("6. Use Extrude or Emboss to project roads onto surface")
    print("7. In CAM workspace, create a Trace or 2D Contour toolpath following the projected sketch")


def main():
    parser = argparse.ArgumentParser(
        description='Generate 2D road map image for CNC projection onto terrain'
    )
    parser.add_argument('--dem', required=True, help='Path to DEM GeoTIFF file')
    parser.add_argument('--roads', required=True, help='Path to roads GeoJSON file')
    parser.add_argument('--output', default='road_map.png', help='Output PNG filename')
    parser.add_argument('--width', type=int, default=3, help='Road width in pixels (default: 3)')
    parser.add_argument('--dpi', type=int, default=300, help='Output DPI (default: 300)')

    args = parser.parse_args()

    generate_road_map(args.dem, args.roads, args.output, args.width, args.dpi)


if __name__ == '__main__':
    main()
