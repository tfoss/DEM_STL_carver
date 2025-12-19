#!/usr/bin/env python3
"""
Generate a DXF file of roads for direct import into Fusion 360.
Creates vector format roads that can be imported as sketch geometry.
"""
import argparse
import numpy as np
import geopandas as gpd
import rasterio
import ezdxf
from ezdxf import units


def generate_road_dxf(dem_file, roads_geojson, output_dxf, model_width_mm=100, model_height_mm=100):
    """
    Generate a DXF file of roads scaled to match the terrain model dimensions.

    Args:
        dem_file: Path to DEM GeoTIFF file (to get bounds)
        roads_geojson: Path to roads GeoJSON file
        output_dxf: Output DXF filename
        model_width_mm: Width of terrain model in mm (from config)
        model_height_mm: Height of terrain model in mm (from config)
    """
    print(f"Loading DEM: {dem_file}")

    # Load DEM to get bounds
    with rasterio.open(dem_file) as src:
        bounds = src.bounds
        dem_width_deg = bounds.right - bounds.left
        dem_height_deg = bounds.top - bounds.bottom

    print(f"DEM bounds: {bounds}")
    print(f"DEM size: {dem_width_deg:.6f}° x {dem_height_deg:.6f}°")

    # Load roads
    print(f"Loading roads: {roads_geojson}")
    roads_gdf = gpd.read_file(roads_geojson)
    if roads_gdf.crs is None:
        roads_gdf.set_crs('EPSG:4326', inplace=True)

    print(f"Found {len(roads_gdf)} road segments")

    # Create DXF document
    doc = ezdxf.new('R2010')
    doc.units = units.MM

    # Set insertion units explicitly to millimeters (critical for Fusion 360)
    # $INSUNITS: 4 = millimeters
    doc.header['$INSUNITS'] = 4

    msp = doc.modelspace()

    # Create a layer for roads
    doc.layers.add(name='ROADS', color=7)

    # Scale factor: convert from degrees to millimeters
    scale_x = model_width_mm / dem_width_deg
    scale_y = model_height_mm / dem_height_deg

    print(f"Scale factors: X={scale_x:.2f} mm/deg, Y={scale_y:.2f} mm/deg")

    # Convert origin (bottom-left of DEM bounds)
    origin_x = bounds.left
    origin_y = bounds.bottom

    total_segments = 0

    # Process each road
    for idx, road in roads_gdf.iterrows():
        geom = road.geometry

        # Handle LineString
        if geom.geom_type == 'LineString':
            coords = list(geom.coords)
            # Convert coords from lat/lon to mm, with origin at (0,0)
            points = []
            for lon, lat in coords:
                x_mm = (lon - origin_x) * scale_x
                y_mm = (lat - origin_y) * scale_y
                points.append((x_mm, y_mm))

            # Add polyline to DXF
            if len(points) >= 2:
                msp.add_lwpolyline(points, dxfattribs={'layer': 'ROADS'})
                total_segments += 1

        # Handle MultiLineString
        elif geom.geom_type == 'MultiLineString':
            for line in geom.geoms:
                coords = list(line.coords)
                points = []
                for lon, lat in coords:
                    x_mm = (lon - origin_x) * scale_x
                    y_mm = (lat - origin_y) * scale_y
                    points.append((x_mm, y_mm))

                if len(points) >= 2:
                    msp.add_lwpolyline(points, dxfattribs={'layer': 'ROADS'})
                    total_segments += 1

    # Save DXF
    doc.saveas(output_dxf)

    print(f"\nDXF file saved: {output_dxf}")
    print(f"Total road segments: {total_segments}")
    print(f"Dimensions: {model_width_mm}mm x {model_height_mm}mm")
    print(f"\nTo use in Fusion 360:")
    print("1. Create a sketch on a plane (top of terrain or offset above)")
    print("2. Sketch → Insert → Insert DXF")
    print(f"3. Select {output_dxf}")
    print("4. Roads will import as polylines at correct scale!")
    print("5. Use these polylines directly for Trace toolpath")


def main():
    parser = argparse.ArgumentParser(
        description='Generate DXF file of roads for Fusion 360 import'
    )
    parser.add_argument('--dem', required=True, help='Path to DEM GeoTIFF file')
    parser.add_argument('--roads', required=True, help='Path to roads GeoJSON file')
    parser.add_argument('--output', default='roads.dxf', help='Output DXF filename')
    parser.add_argument('--width', type=float, default=100,
                       help='Model width in mm (from config.json model_width_mm)')
    parser.add_argument('--height', type=float, default=100,
                       help='Model height in mm (from config.json model_height_mm)')

    args = parser.parse_args()

    generate_road_dxf(args.dem, args.roads, args.output, args.width, args.height)


if __name__ == '__main__':
    main()
