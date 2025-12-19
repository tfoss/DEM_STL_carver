# Fusion 360 Road Projection Guide

This guide explains how to project roads onto your terrain mesh and create a shallow decorative toolpath in Fusion 360.

## Overview

Instead of carving roads into the DEM data (which creates geometric artifacts), we'll:
1. Import the clean terrain STL (without carved roads)
2. Project a 2D road map image onto the 3D surface
3. Create a shallow engraving toolpath that follows the terrain contours

This gives you much cleaner results with precise control over road depth.

## Step-by-Step Workflow

### Part 1: Prepare the Terrain Model

1. **Generate terrain WITHOUT roads:**
   ```bash
   # Edit config.json: set "include_roads": false
   python terrain_carver.py
   ```
   This creates a clean terrain STL without road artifacts.

2. **Import into Fusion 360:**
   - File → Insert → Insert Mesh
   - Select your terrain STL file
   - Click OK

3. **Convert Mesh to Solid Body:**
   - Right-click the mesh in the browser
   - Select "Mesh to BRep"
   - Wait for conversion (may take a minute)
   - You now have a solid body you can work with

### Part 2: Add Roads to Terrain

#### Method A: Import DXF (Recommended - Easiest!)

1. **Generate DXF file:**
   ```bash
   python generate_road_dxf.py --dem dem_data/terrain.tif --roads muir_rd_roads_all.geojson --output muir_rd_roads.dxf --width 100 --height 100
   ```
   This creates a DXF file with roads as vector polylines, perfectly scaled to match your terrain dimensions.

2. **Create Construction Plane:**
   - Create → Construction Plane → Offset from Plane
   - Select XY plane (or create one at terrain base)
   - Offset to be slightly above terrain (e.g., 5-10mm above highest point)
   - This gives you a flat reference plane for the DXF

3. **Create Sketch on Construction Plane:**
   - Create → Create Sketch
   - Select your construction plane
   - This creates a 2D sketch workspace

4. **Import DXF:**
   - Sketch → Insert → Insert DXF
   - Browse to `muir_rd_roads.dxf`
   - Click OK
   - Roads appear as polylines at exactly the right scale and position!
   - No manual scaling or tracing needed!

5. **Ready for CAM:**
   - These polylines can now be used directly in your Trace toolpath
   - The Trace toolpath will project them down onto the terrain surface
   - Skip to Part 3 to create the toolpath

#### Method B: Using Decal/Texture (Visualization Only)

1. **Apply Decal to Surface:**
   - Switch to "Render" workspace (top toolbar)
   - In Appearance panel, find your terrain body
   - Right-click → Appearance
   - In Appearance panel, click "+" to add a decal
   - Browse to `muir_rd_road_map.png`
   - Position and scale the decal to match terrain bounds

2. **Create Toolpath from Decal:**
   - Switch to "Manufacture" workspace
   - This method is primarily for visualization
   - For actual toolpaths, use Method A (DXF) or Method C (manual tracing)

#### Method C: Using Sketch Projection (Manual Tracing)

1. **Create Reference Plane:**
   - Create → Construction Plane
   - Select "Offset from Plane"
   - Pick the top of your bounding box
   - Offset ~10mm above highest terrain point

2. **Insert Canvas Image:**
   - Create a sketch on the reference plane
   - Sketch → Insert → Canvas
   - Select `muir_rd_road_map.png`
   - Click on the sketch plane to place it

3. **Scale Canvas to Match Terrain:**
   - The image needs to match your terrain dimensions
   - Your terrain is 100mm x 100mm (from config)
   - Right-click canvas → Edit Canvas
   - Set width: 100mm, height: 100mm
   - Position to align with terrain bounds

4. **Trace Roads (Option 1 - Manual):**
   - Use sketch tools to trace over white road lines
   - Create splines or polylines following roads
   - This gives you full control over which roads to include

5. **Trace Roads (Option 2 - Automatic):**
   - Sketch → Insert → Insert DXF
   - (You'd need to convert PNG to DXF first - see below)

#### Method D: Alternative - Project Sketch onto Surface (Advanced)

Note: The terrain BRep has many small faces, not a single "top face." The simpler approach is to use a construction plane (Methods A or C) and let the CAM Trace toolpath handle projection.

If you want to create curves that follow the surface directly:

1. **Create 2D Sketch First:**
   - Use Method A (DXF) or Method C (Canvas) to create road curves on a construction plane

2. **Project to Surface in CAM:**
   - When creating the Trace toolpath, select "From Model" for bottom height
   - The toolpath will automatically project your 2D curves onto the 3D terrain surface
   - This is easier and more reliable than trying to sketch directly on the complex surface

### Part 3: Create CAM Toolpath

1. **Switch to Manufacture Workspace:**
   - Click "MANUFACTURE" at top of Fusion 360

2. **Create Setup:**
   - Setup → New Setup
   - Select terrain top as stock top
   - Set stock to "From Solid" selecting your terrain
   - Z-axis pointing up

3. **Create Project Toolpath (Correct Method for 3D Surfaces):**

   The Project toolpath is specifically designed to project 2D curves onto 3D surfaces.

   - **3D → Project** (NOT 2D → Trace!)
   - **Tool Tab:**
     - Select a small ball-nose bit (1/16" or 1/8" ball)
     - Smaller tools give finer detail, larger tools cut faster

   - **Geometry Tab:**
     - Click "Select" under Curves
     - Select your DXF road polylines from the sketch
     - These are the 2D curves that will be projected

   - **Heights Tab:**
     - **Bottom Height**:
       - From: "Selected contour(s)" or "Model top"
       - Offset: -0.02 in to -0.06 in (-0.5mm to -1.5mm)
       - This negative offset controls road depth INTO the surface
     - **Top Height** / **Retract Height**: Leave at defaults
     - **Feed Height**: Usually "From contour" or similar

   - **Passes Tab:**
     - **Tolerance**: 0.001 in to 0.004 in (smaller = smoother but slower)
     - **Maximum Stepover**: 50-75% of tool diameter
     - **Optimal Load**: Not critical for shallow decorative cuts
     - **Stock to Leave**:
       - Radial: 0
       - Axial: 0 (we want full depth)

   - **Linking Tab:**
     - **Projection Direction**: Typically -Z (straight down)
     - This determines how the 2D curves project onto the 3D surface

4. **Simulate:**
   - Click "Simulate" to preview
   - Roads should now follow the terrain surface as shallow grooves
   - Verify the tool follows terrain contours while maintaining road pattern
   - Adjust Bottom Height offset if roads are too shallow or too deep

5. **Tips for Project Toolpath:**
   - Start with -0.02 in (-0.5mm) offset for subtle roads
   - Increase to -0.04 in (-1mm) or -0.06 in (-1.5mm) for more visible grooves
   - The tool will project your 2D curves down onto the 3D terrain surface
   - Unlike Trace, Project is designed specifically for 3D surface following

## Tips for Best Results

### Road Visibility
- **Shallow cuts work best:** 0.5-1.5mm depth is enough to see on wood
- **Finish pass:** Add a separate finishing trace at exact depth for clean lines
- **Small tooling:** Use smallest bit practical (1/16" or 1/8" ball nose)

### Canvas Alignment
- Your road map PNG exactly matches DEM dimensions
- Terrain model: 100mm x 100mm (from your config)
- Set canvas to exactly 100mm x 100mm to match

### Material Considerations
- **Wood:** 0.5-1mm depth shows well, can stain grooves darker
- **MDF:** Deeper cuts (1-2mm) may be needed for visibility
- **Acrylic:** Very shallow (0.2-0.5mm) works, or use contrasting inlay

### Workflow Shortcuts
- **Save road traces:** Save your road splines as a separate sketch/body
- **Reuse for variations:** Easy to adjust depth without re-tracing
- **Multiple passes:** Do terrain roughing pass, then shallow road detail pass

## Generating Road Vectors

### Method 1: Direct from GeoJSON (Recommended)

Use the included script to generate perfect vector roads:

```bash
python generate_road_dxf.py --dem dem_data/terrain.tif --roads muir_rd_roads_all.geojson --output muir_rd_roads.dxf --width 100 --height 100
```

This creates a DXF with:
- Roads as clean polylines (not rasterized)
- Exact scale matching your terrain (100mm x 100mm)
- Proper coordinate transformation from lat/lon
- Ready for immediate import into Fusion 360

### Method 2: Converting PNG to Vector (Alternative)

If you only have the PNG road map:

1. **Using Inkscape (free):**
   ```bash
   # Install: brew install inkscape
   inkscape muir_rd_road_map.png --export-type=dxf --export-filename=road_map.dxf
   ```

2. **Or use online converter:**
   - https://convertio.co/png-dxf/
   - Upload `muir_rd_road_map.png`
   - Download DXF

Note: PNG-to-vector conversion may require cleanup in Fusion 360, as it traces pixels rather than using actual road geometry.

## Troubleshooting

**Toolpath doesn't follow terrain surface (stays flat at top):**
- **SOLUTION**: Use **3D → Project** toolpath, NOT 2D → Trace
- Trace is designed for 2D paths on flat surfaces
- Project is designed to project 2D curves onto 3D surfaces
- This is the most common mistake!

**Roads don't align with terrain:**
- Check DXF was generated from same DEM as terrain STL
- Verify terrain is 100mm x 100mm (check bounding box)
- Roads should auto-align if generated with generate_road_dxf.py

**Can't select road curves in Project toolpath:**
- Make sure you imported DXF into a sketch on a construction plane
- In Project, click "Select" under "Curves" in Geometry tab
- Select the polylines from your sketch

**Roads too shallow/deep:**
- Adjust "Bottom Height" offset in Heights tab
- Start with -0.02 in (-0.5mm) for subtle roads
- Increase to -0.04 in (-1mm) or -0.06 in (-1.5mm) for deeper grooves
- Test on scrap material first

**Toolpath is very slow/detailed:**
- Increase Tolerance in Passes tab (0.004 in instead of 0.001 in)
- Use larger tool diameter if detail allows
- Reduce Maximum Stepover percentage

## Alternative: Multi-Material Inlay

For dramatic effect, you can inlay contrasting material:

1. **Cut road grooves deeper:** 2-3mm depth
2. **Prepare inlay material:** Thin veneer, colored epoxy, or metal strips
3. **Glue inlay into grooves**
4. **Sand flush** with terrain surface

This creates permanent, high-contrast roads that really pop!
