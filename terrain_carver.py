#!/usr/bin/env python3
"""
Terrain Carver - Generate 3D models from DEM data for CNC carving
"""
import os
import sys
import json
import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.features import rasterize
import trimesh
from geopy.geocoders import Nominatim
from scipy import ndimage
import subprocess
import tempfile
import shutil
import requests
from shapely.geometry import LineString, MultiLineString
import geopandas as gpd


class TerrainCarver:
    def __init__(self, config_file='config.json'):
        """Initialize the terrain carver with configuration."""
        self.config = self.load_config(config_file)
        self.dem_file = None
        self.elevation_data = None
        self.bounds = None

    def load_config(self, config_file):
        """Load configuration from JSON file."""
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
        else:
            # Default configuration
            return {
                'address': '224 Muir Rd, Sharon, VT',
                'area_size_km': 5.0,  # Size of area to capture (km x km)
                'output_file': 'terrain_model.stl',
                'model_width_mm': 200,  # Width of final model in mm
                'model_height_mm': 200,  # Height of final model in mm
                'base_thickness_mm': 5,  # Thickness of base
                'vertical_scale': 1.5,  # Vertical exaggeration factor
                'smooth_iterations': 1,  # Number of smoothing passes
                'data_source': 'py3dep',  # 'srtm', 'py3dep', or 'opentopography'
                'opentopography_api_key': None,  # Required for opentopography
                'include_roads': False,  # Whether to carve roads into terrain
                'road_depth_m': 2.0,  # Depth of road indentation in meters
                'road_width_m': 10.0,  # Width of roads in meters
                'road_types': 'major',  # 'major' (main roads only) or 'all' (all driveable roads)
                'roads_geojson_file': None,  # Optional: path to pre-downloaded GeoJSON file
            }

    def geocode_address(self, address):
        """Convert address to lat/lon coordinates."""
        print(f"Geocoding address: {address}")
        geolocator = Nominatim(user_agent="terrain_carver")
        location = geolocator.geocode(address)

        if location:
            print(f"Location found: {location.latitude}, {location.longitude}")
            return location.latitude, location.longitude
        else:
            raise ValueError(f"Could not geocode address: {address}")

    def calculate_bounds(self, lat, lon, area_size_km):
        """Calculate bounding box around center point."""
        # Approximate degrees per km at this latitude
        km_per_deg_lat = 110.574
        km_per_deg_lon = 111.320 * np.cos(np.radians(lat))

        half_size = area_size_km / 2.0
        lat_offset = half_size / km_per_deg_lat
        lon_offset = half_size / km_per_deg_lon

        bounds = {
            'south': lat - lat_offset,
            'north': lat + lat_offset,
            'west': lon - lon_offset,
            'east': lon + lon_offset
        }

        print(f"Bounds: S:{bounds['south']:.4f} N:{bounds['north']:.4f} "
              f"W:{bounds['west']:.4f} E:{bounds['east']:.4f}")

        return bounds

    def download_dem_data(self, bounds, output_dir='dem_data'):
        """Download DEM data using elevation package."""
        os.makedirs(output_dir, exist_ok=True)

        # Create a temporary file for the clipped DEM
        output_file = os.path.join(output_dir, 'terrain.tif')

        print("Downloading DEM data...")
        print("This uses SRTM 30m resolution data")

        # Use elevation command line tool to download and clip data
        cmd = [
            'eio',
            'clip',
            '-o', output_file,
            '--bounds',
            str(bounds['west']),
            str(bounds['south']),
            str(bounds['east']),
            str(bounds['north'])
        ]

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("DEM data downloaded successfully")
            self.dem_file = output_file
            return output_file
        except subprocess.CalledProcessError as e:
            print(f"Error downloading DEM data: {e}")
            print(f"stderr: {e.stderr}")
            raise

    def download_dem_data_py3dep(self, bounds, output_dir='dem_data'):
        """Download DEM data using py3dep (USGS 3DEP)."""
        try:
            import py3dep
        except ImportError:
            raise ImportError("py3dep package not installed. Run: pip install py3dep")

        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'terrain.tif')

        print("Downloading DEM data using USGS 3DEP...")
        print("This will get the highest resolution data available (typically 10m or better)")

        try:
            # py3dep automatically selects the best available resolution
            # For most of the US, this is 10m or 1m
            dem = py3dep.get_map(
                "DEM",
                (bounds['west'], bounds['south'], bounds['east'], bounds['north']),
                resolution=10,  # Target resolution in meters
                crs=4326
            )

            # Save to GeoTIFF
            dem.rio.to_raster(output_file, driver='GTiff')

            print(f"DEM data downloaded successfully")
            print(f"Resolution: ~{dem.rio.resolution()[0] * 111000:.1f}m")  # Approx conversion
            self.dem_file = output_file
            return output_file

        except Exception as e:
            print(f"Error downloading DEM data with py3dep: {e}")
            raise

    def download_dem_data_opentopography(self, bounds, output_dir='dem_data'):
        """Download DEM data using OpenTopography API (highest resolution lidar when available)."""
        api_key = self.config.get('opentopography_api_key')
        if not api_key:
            raise ValueError("OpenTopography API key not found in config")

        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'terrain.tif')

        print("Downloading DEM data from OpenTopography...")
        print("Attempting to get highest resolution lidar data...")

        # OpenTopography SRTMGL1 (30m) endpoint - we'll use this as fallback
        # For lidar, we'd need to query available datasets first
        # Using SRTMGL1_E as a reliable option, but can be extended for lidar datasets

        base_url = "https://portal.opentopography.org/API/globaldem"

        params = {
            'demtype': 'SRTMGL1_E',  # SRTM 30m enhanced
            'south': bounds['south'],
            'north': bounds['north'],
            'west': bounds['west'],
            'east': bounds['east'],
            'outputFormat': 'GTiff',
            'API_Key': api_key
        }

        try:
            print(f"Requesting data from OpenTopography...")
            response = requests.get(base_url, params=params, stream=True)
            response.raise_for_status()

            # Save the response to file
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print("DEM data downloaded successfully")
            self.dem_file = output_file
            return output_file

        except requests.exceptions.RequestException as e:
            print(f"Error downloading from OpenTopography: {e}")
            raise

    def download_dem_data_opentopography_lidar(self, bounds, output_dir='dem_data'):
        """Download highest resolution lidar data from OpenTopography."""
        api_key = self.config.get('opentopography_api_key')
        if not api_key:
            raise ValueError("OpenTopography API key not found in config")

        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, 'terrain.tif')

        print("Downloading lidar data from OpenTopography...")
        print("This may take a while for high-resolution data...")

        # Use the raster API for point cloud-derived rasters
        base_url = "https://portal.opentopography.org/API/usgsdem"

        params = {
            'demtype': 'PointCloud',  # Request point cloud derived DEM
            'south': bounds['south'],
            'north': bounds['north'],
            'west': bounds['west'],
            'east': bounds['east'],
            'outputFormat': 'GTiff',
            'API_Key': api_key
        }

        try:
            print(f"Requesting lidar data from OpenTopography...")
            print("Note: This will automatically select best available lidar coverage")
            response = requests.get(base_url, params=params, stream=True, timeout=300)
            response.raise_for_status()

            # Save the response to file
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print("Lidar data downloaded successfully")
            self.dem_file = output_file
            return output_file

        except requests.exceptions.RequestException as e:
            print(f"Error downloading lidar from OpenTopography: {e}")
            print("Falling back to standard DEM...")
            return self.download_dem_data_opentopography(bounds, output_dir)

    def download_roads(self, bounds):
        """Download road data from OpenStreetMap or load from local GeoJSON file."""

        # Check if user provided a local GeoJSON file
        geojson_file = self.config.get('roads_geojson_file')
        if geojson_file and os.path.exists(geojson_file):
            print(f"Loading roads from local file: {geojson_file}")
            try:
                gdf = gpd.read_file(geojson_file)
                # Ensure it has a CRS
                if gdf.crs is None:
                    gdf.set_crs('EPSG:4326', inplace=True)
                print(f"Loaded {len(gdf)} road segments from file")
                return gdf
            except Exception as e:
                print(f"Warning: Could not load GeoJSON file: {e}")
                print("Falling back to Overpass API...")

        print("Downloading road data from OpenStreetMap...")

        try:
            from shapely.geometry import LineString
            import json

            # Create bounding box for OSM query
            south, west, north, east = bounds['south'], bounds['west'], bounds['north'], bounds['east']

            # Determine which road types to include based on config
            road_types_mode = self.config.get('road_types', 'major')

            if road_types_mode == 'major':
                # Major roads only
                print(f"Downloading major roads only...")
                highway_filter = 'motorway|trunk|primary|secondary|tertiary'
            else:
                # All driveable roads
                print(f"Downloading all driveable roads...")
                highway_filter = 'motorway|trunk|primary|secondary|tertiary|residential|unclassified'

            # Build Overpass QL query - much faster and more direct
            overpass_query = f"""
            [out:json][timeout:25];
            (
              way["highway"~"{highway_filter}"]({south},{west},{north},{east});
            );
            out geom;
            """

            print(f"Querying Overpass API for bounds: S:{south:.4f} W:{west:.4f} N:{north:.4f} E:{east:.4f}")

            # Query Overpass API directly - try multiple servers
            overpass_urls = [
                "https://overpass.kumi.systems/api/interpreter",  # Try faster server first
                "http://overpass-api.de/api/interpreter",  # Fallback to main server
            ]

            response = None
            for url in overpass_urls:
                try:
                    print(f"Trying {url}...")
                    response = requests.post(url, data={'data': overpass_query}, timeout=30)
                    response.raise_for_status()
                    break  # Success!
                except (requests.exceptions.Timeout, requests.exceptions.HTTPError) as e:
                    print(f"Failed with {url}: {e}")
                    if url == overpass_urls[-1]:  # Last URL
                        raise  # Re-raise if all URLs failed
                    continue  # Try next URL

            if response is None:
                raise Exception("All Overpass API servers failed")

            data = response.json()

            # Extract geometries
            geometries = []
            for element in data.get('elements', []):
                if element['type'] == 'way' and 'geometry' in element:
                    coords = [(node['lon'], node['lat']) for node in element['geometry']]
                    if len(coords) >= 2:
                        geometries.append(LineString(coords))

            if not geometries:
                print("No roads found in this area")
                return None

            # Create GeoDataFrame
            gdf = gpd.GeoDataFrame({'geometry': geometries}, crs='EPSG:4326')

            print(f"Found {len(gdf)} road segments")

            return gdf

        except Exception as e:
            print(f"Warning: Could not download road data: {e}")
            print("Continuing without roads...")
            return None

    def rasterize_roads(self, roads_gdf, elevation_data, transform, road_width_m, road_depth_m):
        """Burn roads into elevation data as indentations."""
        if roads_gdf is None or len(roads_gdf) == 0:
            return elevation_data

        print(f"Carving {len(roads_gdf)} road segments into terrain...")
        print(f"Road width: {road_width_m}m, depth: {road_depth_m}m")

        # Create a copy of elevation data
        carved_elevation = elevation_data.copy()

        # Get the resolution in meters (approximate)
        pixel_width = abs(transform[0])  # degrees per pixel
        pixel_height = abs(transform[4])  # degrees per pixel

        # Convert to meters (approximate at this latitude)
        # Using the center of the bounds
        lat_center = (self.bounds['north'] + self.bounds['south']) / 2
        meters_per_degree_lon = 111320 * np.cos(np.radians(lat_center))
        meters_per_degree_lat = 110574

        pixel_width_m = pixel_width * meters_per_degree_lon
        pixel_height_m = pixel_height * meters_per_degree_lat

        # Project to a local UTM coordinate system for accurate buffering in meters
        # Determine UTM zone based on center longitude
        lon_center = (self.bounds['west'] + self.bounds['east']) / 2
        utm_zone = int((lon_center + 180) / 6) + 1
        utm_crs = f'EPSG:{32600 + utm_zone}' if lat_center >= 0 else f'EPSG:{32700 + utm_zone}'

        # Project to UTM, buffer, then project back to WGS84
        roads_buffered = roads_gdf.to_crs(utm_crs)
        roads_buffered['geometry'] = roads_buffered.geometry.buffer(road_width_m / 2)  # Buffer in meters
        roads_buffered = roads_buffered.to_crs('EPSG:4326')  # Back to WGS84 for rasterization

        # Create shapes for rasterization
        shapes = [(geom, 1) for geom in roads_buffered.geometry]

        # Rasterize roads onto a mask
        road_mask = rasterize(
            shapes,
            out_shape=elevation_data.shape,
            transform=transform,
            fill=0,
            dtype=np.uint8
        )

        # Apply road indentation where mask is 1
        # Subtract the road depth from elevation
        carved_elevation = np.where(road_mask == 1,
                                    elevation_data - road_depth_m,
                                    elevation_data)

        print(f"Roads carved into terrain (affected {np.sum(road_mask)} pixels)")

        return carved_elevation

    def load_elevation_data(self, dem_file=None):
        """Load elevation data from GeoTIFF file."""
        if dem_file is None:
            dem_file = self.dem_file

        print(f"Loading elevation data from {dem_file}")

        with rasterio.open(dem_file) as src:
            # Read the elevation data
            elevation = src.read(1)

            # Get metadata
            self.elevation_data = elevation
            self.transform = src.transform
            self.crs = src.crs

            print(f"Elevation data shape: {elevation.shape}")
            print(f"Elevation range: {np.nanmin(elevation):.1f}m to {np.nanmax(elevation):.1f}m")

            return elevation

    def process_elevation_data(self, elevation_data=None):
        """Process elevation data - fill voids, smooth, etc."""
        if elevation_data is None:
            elevation_data = self.elevation_data

        print("Processing elevation data...")

        # Replace NaN values with interpolation
        mask = np.isnan(elevation_data)
        if np.any(mask):
            print("Filling void data...")
            elevation_data = self.fill_voids(elevation_data)

        # Apply smoothing if requested
        smooth_iterations = self.config.get('smooth_iterations', 0)
        if smooth_iterations > 0:
            print(f"Applying {smooth_iterations} smoothing iterations...")
            for _ in range(smooth_iterations):
                elevation_data = ndimage.gaussian_filter(elevation_data, sigma=1.0)

        self.elevation_data = elevation_data
        return elevation_data

    def fill_voids(self, elevation_data):
        """Fill void/NaN values using interpolation."""
        mask = np.isnan(elevation_data)
        indices = ndimage.distance_transform_edt(
            mask, return_distances=False, return_indices=True
        )
        return elevation_data[tuple(indices)]

    def create_mesh(self, elevation_data=None):
        """Create 3D mesh from elevation data."""
        if elevation_data is None:
            elevation_data = self.elevation_data

        print("Creating 3D mesh...")

        # Get configuration
        model_width = self.config['model_width_mm']
        model_height = self.config['model_height_mm']
        base_thickness = self.config['base_thickness_mm']
        vertical_scale = self.config['vertical_scale']

        # Normalize elevation data
        elev_min = np.nanmin(elevation_data)
        elev_max = np.nanmax(elevation_data)
        elev_range = elev_max - elev_min

        print(f"Elevation range: {elev_range:.1f}m")

        # Normalize to 0-1
        normalized_elev = (elevation_data - elev_min) / elev_range

        # Calculate vertical scale in mm
        # We want the terrain relief to be scaled appropriately
        max_relief = min(model_width, model_height) * 0.3  # Max 30% of model size
        vertical_mm = normalized_elev * max_relief * vertical_scale

        # Create coordinate grids
        rows, cols = elevation_data.shape
        x = np.linspace(0, model_width, cols)
        y = np.linspace(0, model_height, rows)
        xx, yy = np.meshgrid(x, y)

        # Flip y to match conventional orientation
        yy = model_height - yy

        # Add base thickness
        zz = vertical_mm + base_thickness

        # Create vertices for top surface
        vertices_top = np.column_stack([
            xx.ravel(),
            yy.ravel(),
            zz.ravel()
        ])

        # Create faces for top surface using triangulation
        faces_top = []
        for i in range(rows - 1):
            for j in range(cols - 1):
                # Two triangles per grid cell
                v1 = i * cols + j
                v2 = i * cols + (j + 1)
                v3 = (i + 1) * cols + j
                v4 = (i + 1) * cols + (j + 1)

                # Triangle 1
                faces_top.append([v1, v2, v3])
                # Triangle 2
                faces_top.append([v2, v4, v3])

        faces_top = np.array(faces_top)

        # Create bottom surface (flat base)
        vertices_bottom = vertices_top.copy()
        vertices_bottom[:, 2] = 0  # Z = 0 for bottom

        # Combine vertices
        num_top_verts = len(vertices_top)
        vertices = np.vstack([vertices_top, vertices_bottom])

        # Create bottom faces (reversed winding for correct normals)
        faces_bottom = faces_top.copy() + num_top_verts
        faces_bottom = faces_bottom[:, [0, 2, 1]]  # Reverse winding

        # Create side walls
        faces_sides = []

        # Front edge (y=0)
        for j in range(cols - 1):
            v1_top = j
            v2_top = j + 1
            v1_bot = v1_top + num_top_verts
            v2_bot = v2_top + num_top_verts
            faces_sides.append([v1_top, v1_bot, v2_top])
            faces_sides.append([v2_top, v1_bot, v2_bot])

        # Back edge (y=max)
        for j in range(cols - 1):
            base_idx = (rows - 1) * cols
            v1_top = base_idx + j
            v2_top = base_idx + j + 1
            v1_bot = v1_top + num_top_verts
            v2_bot = v2_top + num_top_verts
            faces_sides.append([v1_top, v2_top, v1_bot])
            faces_sides.append([v2_top, v2_bot, v1_bot])

        # Left edge (x=0)
        for i in range(rows - 1):
            v1_top = i * cols
            v2_top = (i + 1) * cols
            v1_bot = v1_top + num_top_verts
            v2_bot = v2_top + num_top_verts
            faces_sides.append([v1_top, v2_top, v1_bot])
            faces_sides.append([v2_top, v2_bot, v1_bot])

        # Right edge (x=max)
        for i in range(rows - 1):
            v1_top = i * cols + (cols - 1)
            v2_top = (i + 1) * cols + (cols - 1)
            v1_bot = v1_top + num_top_verts
            v2_bot = v2_top + num_top_verts
            faces_sides.append([v1_top, v1_bot, v2_top])
            faces_sides.append([v2_top, v1_bot, v2_bot])

        faces_sides = np.array(faces_sides)

        # Combine all faces
        faces = np.vstack([faces_top, faces_bottom, faces_sides])

        # Create trimesh object
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)

        # Process mesh to fix normals and clean up
        mesh.process()
        mesh.fix_normals()

        print(f"Mesh created: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces")
        print(f"Model dimensions: {model_width}mm x {model_height}mm x {base_thickness + max_relief * vertical_scale:.1f}mm")

        return mesh

    def export_stl(self, mesh, output_file=None):
        """Export mesh to STL file."""
        if output_file is None:
            output_file = self.config['output_file']

        print(f"Exporting to {output_file}...")
        mesh.export(output_file)
        print(f"STL file created successfully: {output_file}")
        print(f"File size: {os.path.getsize(output_file) / 1024 / 1024:.2f} MB")

        return output_file

    def run(self):
        """Run the complete terrain carving pipeline."""
        print("="*60)
        print("Terrain Carver - CNC Terrain Model Generator")
        print("="*60)

        # Geocode address
        lat, lon = self.geocode_address(self.config['address'])

        # Calculate bounds
        self.bounds = self.calculate_bounds(lat, lon, self.config['area_size_km'])

        # Download DEM data based on configured source
        data_source = self.config.get('data_source', 'srtm').lower()
        print(f"Using data source: {data_source}")

        if data_source == 'py3dep':
            self.download_dem_data_py3dep(self.bounds)
        elif data_source == 'opentopography':
            self.download_dem_data_opentopography(self.bounds)
        elif data_source == 'opentopography_lidar':
            self.download_dem_data_opentopography_lidar(self.bounds)
        elif data_source == 'srtm':
            self.download_dem_data(self.bounds)
        else:
            raise ValueError(f"Unknown data source: {data_source}. "
                           f"Use 'srtm', 'py3dep', 'opentopography', or 'opentopography_lidar'")

        # Load elevation data
        self.load_elevation_data()

        # Download and carve roads if requested
        if self.config.get('include_roads', False):
            roads_gdf = self.download_roads(self.bounds)
            if roads_gdf is not None:
                self.elevation_data = self.rasterize_roads(
                    roads_gdf,
                    self.elevation_data,
                    self.transform,
                    self.config.get('road_width_m', 10.0),
                    self.config.get('road_depth_m', 2.0)
                )

        # Process elevation data
        self.process_elevation_data()

        # Create mesh
        mesh = self.create_mesh()

        # Export STL
        output_file = self.export_stl(mesh)

        print("="*60)
        print("Complete! Your terrain model is ready.")
        print(f"Output file: {output_file}")
        print("You can now import this STL file into Fusion 360")
        print("="*60)

        return output_file


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Generate 3D terrain models from DEM data')
    parser.add_argument('--config', default='config.json', help='Configuration file')
    parser.add_argument('--address', help='Address to center the terrain model')
    parser.add_argument('--area-size', type=float, help='Area size in km')
    parser.add_argument('--output', help='Output STL file')

    args = parser.parse_args()

    # Create terrain carver
    carver = TerrainCarver(args.config)

    # Override config with command line arguments
    if args.address:
        carver.config['address'] = args.address
    if args.area_size:
        carver.config['area_size_km'] = args.area_size
    if args.output:
        carver.config['output_file'] = args.output

    # Run the pipeline
    carver.run()


if __name__ == '__main__':
    main()
