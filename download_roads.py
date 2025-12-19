#!/usr/bin/env python3
"""
Helper script to download and cache road data from OpenStreetMap.
This allows you to download once and reuse, avoiding Overpass API timeouts.
"""
import json
import requests
import sys
import argparse


def download_roads_geojson(south, west, north, east, output_file='roads.geojson', road_types='major'):
    """Download roads from Overpass API and save as GeoJSON."""

    if road_types == 'major':
        highway_filter = 'motorway|trunk|primary|secondary|tertiary'
        print("Downloading major roads only...")
    else:
        highway_filter = 'motorway|trunk|primary|secondary|tertiary|residential|unclassified'
        print("Downloading all driveable roads...")

    # Build Overpass QL query
    overpass_query = f"""
    [out:json][timeout:60];
    (
      way["highway"~"{highway_filter}"]({south},{west},{north},{east});
    );
    out geom;
    """

    print(f"Querying Overpass API...")
    print(f"Bounds: S:{south} W:{west} N:{north} E:{east}")

    # Try multiple servers
    overpass_urls = [
        "https://overpass.kumi.systems/api/interpreter",
        "http://overpass-api.de/api/interpreter",
    ]

    response = None
    for url in overpass_urls:
        try:
            print(f"Trying {url}...")
            response = requests.post(url, data={'data': overpass_query}, timeout=60)
            response.raise_for_status()
            print(f"Success!")
            break
        except Exception as e:
            print(f"Failed: {e}")
            if url == overpass_urls[-1]:
                raise
            continue

    if response is None:
        raise Exception("All Overpass API servers failed")

    # Parse response
    data = response.json()

    # Convert to GeoJSON
    features = []
    for element in data.get('elements', []):
        if element['type'] == 'way' and 'geometry' in element:
            coords = [[node['lon'], node['lat']] for node in element['geometry']]
            if len(coords) >= 2:
                feature = {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'LineString',
                        'coordinates': coords
                    },
                    'properties': {
                        'highway': element.get('tags', {}).get('highway', 'unknown'),
                        'name': element.get('tags', {}).get('name', ''),
                    }
                }
                features.append(feature)

    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }

    # Save to file
    with open(output_file, 'w') as f:
        json.dump(geojson, f, indent=2)

    print(f"\nSuccessfully downloaded {len(features)} road segments")
    print(f"Saved to: {output_file}")
    print(f"\nTo use this file, add to your config.json:")
    print(f'  "roads_geojson_file": "{output_file}"')


def main():
    parser = argparse.ArgumentParser(
        description='Download road data from OpenStreetMap and save as GeoJSON'
    )
    parser.add_argument('--south', type=float, required=True, help='Southern latitude')
    parser.add_argument('--west', type=float, required=True, help='Western longitude')
    parser.add_argument('--north', type=float, required=True, help='Northern latitude')
    parser.add_argument('--east', type=float, required=True, help='Eastern longitude')
    parser.add_argument('--output', default='roads.geojson', help='Output GeoJSON file (default: roads.geojson)')
    parser.add_argument('--road-types', choices=['major', 'all'], default='major',
                       help='Road types to download (default: major)')

    args = parser.parse_args()

    try:
        download_roads_geojson(
            args.south, args.west, args.north, args.east,
            args.output, args.road_types
        )
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
