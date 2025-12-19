# Terrain Carver - CNC Terrain Model Generator

Generate 3D terrain models from real elevation data for CNC carving. This tool downloads Digital Elevation Model (DEM) data for any location and converts it into an STL file ready for import into Fusion 360 or other CAD software.

## Features

- Geocode any address to automatically center the terrain
- Multiple high-resolution data sources:
  - **py3dep**: USGS 3DEP data (10m resolution, up to 1m for some areas) - Recommended!
  - **OpenTopography**: Global coverage with lidar support (sub-meter where available)
  - **SRTM**: Global 30m data (legacy option)
- **Road carving**: Automatically carve roads into terrain as subtle indentations
  - Downloads real road data from OpenStreetMap
  - Configurable road width and depth
  - Makes landmarks easier to identify in the final model
- Configurable area size and model dimensions
- Vertical exaggeration control for dramatic relief
- Automatic void filling and optional smoothing
- Export ready-to-use STL files for CNC carving

## Data Sources Comparison

| Source | Resolution | Coverage | Best For |
|--------|-----------|----------|----------|
| **py3dep** (Default) | 10m (often 1-3m) | USA | Highest quality US terrain |
| **OpenTopography** | Varies (1m lidar to 30m) | Global | Areas with lidar coverage |
| **SRTM** | 30m | Global | Quick tests, non-US locations |

## Setup

### 1. Create Conda Environment

```bash
conda env create -f environment.yml
conda activate terrain_carve
```

### 2. Install GDAL Tools (Optional - only needed for SRTM data source)

If you plan to use the SRTM data source, install GDAL command-line tools:

**macOS (using Homebrew):**
```bash
brew install gdal
```

**Ubuntu/Debian:**
```bash
sudo apt-get install gdal-bin
```

**Windows:**
Download and install GDAL from: https://gdal.org/download.html

**Note**: GDAL is NOT required for py3dep or OpenTopography data sources.

### 3. Verify Installation

```bash
python terrain_carver.py --help
```

## Usage

### Quick Start

Using the default configuration (224 Muir Rd, Sharon, VT):

```bash
python terrain_carver.py
```

This will generate `muir_rd_terrain.stl` in the current directory.

### Custom Location

```bash
python terrain_carver.py --address "Your Address Here" --area-size 10 --output my_terrain.stl
```

### Using Configuration File

Edit `config.json` to customize all parameters:

```json
{
  "address": "224 Muir Rd, Sharon, VT",
  "area_size_km": 5.0,
  "output_file": "muir_rd_terrain.stl",
  "model_width_mm": 200,
  "model_height_mm": 200,
  "base_thickness_mm": 5,
  "vertical_scale": 1.5,
  "smooth_iterations": 1,
  "data_source": "py3dep",
  "opentopography_api_key": "your_api_key_here"
}
```

Then run:

```bash
python terrain_carver.py --config config.json
```

## Configuration Parameters

- **address**: Address to center the terrain model
- **area_size_km**: Size of the area to capture (creates a square area)
- **output_file**: Name of the output STL file
- **model_width_mm**: Width of the final model in millimeters
- **model_height_mm**: Height of the final model in millimeters
- **base_thickness_mm**: Thickness of the base platform
- **vertical_scale**: Vertical exaggeration factor (1.0 = true scale, higher = more dramatic)
- **smooth_iterations**: Number of smoothing passes (0 = no smoothing, higher = smoother)
- **data_source**: Which data source to use - options:
  - `"py3dep"` - USGS 3DEP data (10m or better, USA only) - **Recommended for US locations**
  - `"opentopography"` - OpenTopography global DEM (30m)
  - `"opentopography_lidar"` - OpenTopography lidar data (1m or better where available)
  - `"srtm"` - SRTM 30m global data (requires GDAL)
- **opentopography_api_key**: Your OpenTopography API key (required for opentopography sources)
  - Get a free key at: https://portal.opentopography.org/requestService
- **include_roads**: Enable road carving (true/false) - adds roads as indentations in the terrain
- **road_width_m**: Width of roads in meters (default: 10.0)
  - Typical values: 5-15m depending on road type and model scale
- **road_depth_m**: Depth of road indentation in meters (default: 2.0)
  - Typical values: 1-5m - subtle but visible in the final carving

## Road Carving Feature

The road carving feature downloads real road data from OpenStreetMap and "carves" them into your terrain model as subtle indentations. This makes it much easier to identify landmarks and orient yourself on the model.

**Benefits:**
- Makes roads clearly visible on the carved model
- Helps identify location of houses and landmarks
- Creates more realistic and recognizable terrain
- No additional API keys required (uses OpenStreetMap)

**Configuration Tips:**
- Start with defaults (`road_width_m: 10`, `road_depth_m: 2`, `road_types: "major"`)
- For larger models (>200mm), you can use wider/deeper roads for visibility
- For smaller models (<100mm), reduce width/depth to avoid overwhelming detail
- Road depth is relative to terrain - a 2m indentation is subtle but visible
- Use `road_types: "major"` for main roads only (faster, less clutter)
- Use `road_types: "all"` to include residential streets (more detail, slower download)

**Example:**
```json
{
  "include_roads": true,
  "road_width_m": 10.0,
  "road_depth_m": 2.0,
  "road_types": "major"
}
```

**Note:** Road data is downloaded from public OpenStreetMap Overpass API servers. If the download times out, the script will continue without roads. The feature works best during off-peak hours or you can retry if servers are busy.

## Choosing a Data Source

### For Vermont (and most US locations):
Use **py3dep** (default) - it provides 10m or better resolution and requires no API key.

### For lidar data:
Use **opentopography_lidar** - attempts to get highest resolution lidar data, falls back to standard DEM if not available.

### For international locations:
Use **opentopography** for global coverage.

### Setting up OpenTopography:
1. Visit https://portal.opentopography.org/requestService
2. Sign up for a free account
3. Request an API key
4. Add it to your `config.json`

## Tips for CNC Carving

### Model Size
- Default is 200mm x 200mm (about 8" x 8")
- Adjust based on your CNC bed size and material
- Larger models show more terrain detail

### Vertical Scale
- Vermont terrain is hilly, so 1.5x exaggeration works well
- For flatter areas, use 2.0-3.0x
- For mountainous areas, use 1.0-1.5x

### Area Size
- 5km x 5km is good for neighborhood-scale features
- 2-3km for detailed local area
- 10-15km for broader regional view
- Remember: SRTM resolution is 30m, so very small areas may not show much detail

### Smoothing
- 0-1 iterations: Keeps natural terrain texture (good for detailed carving)
- 2-3 iterations: Smoother, easier to carve but less detail
- More smoothing = easier on your CNC bits

### Material Recommendations
- Wood: Great for larger models, shows grain patterns
- MDF: Smooth finish, easy to carve
- Foam: Fast carving, lightweight, good for prototypes
- Acrylic: Beautiful with edge lighting

## Importing into Fusion 360

1. Open Fusion 360
2. Create a new design
3. Click **Insert > Insert Mesh**
4. Select your STL file
5. The mesh will appear - you may need to adjust view scale
6. Right-click the mesh and choose **Mesh to BRep** if you want to convert to solid
7. Generate toolpaths using the CAM workspace

## Troubleshooting

### "Could not geocode address"
- Check that the address is spelled correctly
- Try a more specific address or use coordinates directly
- Make sure you have internet connection

### "Error downloading DEM data"
- Check internet connection
- Verify GDAL tools are installed: `gdalinfo --version`
- The elevation package may need to download data on first run

### Model appears flat
- Increase `vertical_scale` in config
- Check that your area has elevation changes
- Try a smaller `area_size_km` for more detail

### STL file is too large
- Reduce model dimensions
- Increase `smooth_iterations`
- Reduce `area_size_km`

### Model has holes or artifacts
- DEM data may have voids in that area
- Increase `smooth_iterations`
- Try a different area_size_km

## Advanced Usage

### Using Coordinates Instead of Address

Edit the code to use coordinates directly:

```python
# In terrain_carver.py, modify the run() method:
lat, lon = 43.8041, -72.4619  # Example coordinates
```

### Switching Between Data Sources

Simply change the `data_source` in your config.json:

```json
{
  "data_source": "py3dep"  // For best US data
}
```

or

```json
{
  "data_source": "opentopography_lidar",  // For lidar data
  "opentopography_api_key": "your_key_here"
}
```

### Multi-Material Carving

The STL can be processed to create elevation contours for multi-material layering:
- Import STL into Fusion 360
- Use Mesh to BRep
- Create offset planes at different heights
- Split the solid at each plane for different material layers

## Data Sources

This tool supports multiple elevation data sources:

### USGS 3DEP (via py3dep)
- **Resolution**: 10m (1/3 arc-second) or better, often 1-3m
- **Coverage**: USA only
- **Vertical accuracy**: ±1-2m
- **API Key**: Not required
- **Best for**: US locations, highest quality

### OpenTopography
- **Resolution**: Varies by dataset
  - Global DEM: 30m (SRTM)
  - Lidar: 1m or better where available
- **Coverage**: Global
- **Vertical accuracy**: Varies by dataset
- **API Key**: Required (free)
- **Best for**: Lidar data, international locations

### SRTM (Shuttle Radar Topography Mission)
- **Resolution**: 30m (about 98 feet)
- **Coverage**: Global
- **Vertical accuracy**: ±16m
- **API Key**: Not required
- **Best for**: Quick tests, legacy compatibility

## License

This tool is provided as-is for educational and personal use.

## Contributing

Suggestions and improvements welcome! This is a tool for makers and CNC enthusiasts.
