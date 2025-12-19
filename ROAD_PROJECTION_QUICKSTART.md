# Road Projection Quick Start

## What You Have

### Files for Road Projection Workflow:
1. **muir_rd_terrain_clean.stl** - Clean terrain without roads (12.81 MB)
2. **muir_rd_roads.dxf** - Roads as vector polylines (DXF format for direct import)
3. **muir_rd_road_map.png** - 2D road map image (304 x 221 pixels @ 300 DPI)
4. **muir_rd_roads_all.geojson** - Raw road data (15 road segments)

### Model Specs:
- **Dimensions**: 100mm x 100mm x ~50mm tall
- **Resolution**: ~9.1m per pixel (py3dep data)
- **Roads**: 15 segments including Muir Rd and all residential streets

## Quick Workflow

### 1. Import to Fusion 360
```
File → Insert → Insert Mesh → select muir_rd_terrain_clean.stl
```

### 2. Convert to Solid
```
Right-click mesh → Mesh to BRep
(wait 1-2 minutes for conversion)
```

### 3. Add Roads

**Option A - Import DXF (Recommended - No Tracing!):**
```
Create → Create Sketch → pick top of terrain
Sketch → Insert → Insert DXF → select muir_rd_roads.dxf
Roads import as perfect polylines at correct scale!
```

**Option B - Canvas for Manual Tracing:**
```
Create → Create Sketch → pick top of terrain
Sketch → Insert → Canvas → select muir_rd_road_map.png
Scale to 100mm x 100mm
Trace roads with spline tool
```

**Option C - Decal (visualization only):**
```
Switch to Render workspace
Select terrain → Appearance → Add Decal
Browse to muir_rd_road_map.png
Scale and position to match
```

### 4. Create Toolpath (CAM Workspace)

```
Setup → New Setup → select terrain
2D → Trace
  - Select your traced road splines
  - Tool: 1/16" or 1/8" ball nose
  - Bottom Height: 0mm (rides on surface)
  - Optimal Load: 0.5-1.5mm (shallow decorative cut)
Simulate → verify roads appear as grooves
```

## Key Settings

### Canvas Scaling
- **Width**: 100mm (matches your terrain model_width_mm)
- **Height**: 100mm (matches your terrain model_height_mm)
- **Alignment**: Center on terrain bounds

### Recommended Cut Depths
- **Wood**: 0.5-1.5mm (can stain darker for contrast)
- **MDF**: 1-2mm (deeper for visibility)
- **Acrylic**: 0.2-0.5mm (very shallow)

### Tooling
- **Roughing terrain**: 1/4" or 1/8" ball nose
- **Road detail**: 1/16" or 1/8" ball nose (smaller = finer detail)
- **Speeds**: Standard for material, shallow depth means fast feed

## Tips

1. **Do terrain first, roads second:**
   - Rough/finish entire terrain
   - Then add shallow road toolpath
   - This prevents damaging delicate road grooves during roughing

2. **Test road depth on scrap:**
   - Cut a test groove at 0.5mm, 1mm, 1.5mm
   - See what shows best on your material

3. **Enhance visibility:**
   - Rub dark stain/marker into grooves, wipe surface
   - Or fill with contrasting epoxy/wood filler
   - Or inlay thin veneer strips

4. **Save your work:**
   - Save the traced road sketch separately
   - Easy to adjust depth without re-tracing

## Comparison

### Method 1: Carved Roads (your previous approach)
- ❌ Roads distort terrain geometry
- ❌ Can't control depth precisely
- ❌ Hard to edit after generation
- ✅ Single STL file

### Method 2: Projected Roads (this approach)
- ✅ Clean terrain geometry
- ✅ Precise depth control in CAM
- ✅ Easy to adjust or disable
- ✅ Better CNC results
- ✅ Can use different tools for terrain vs roads

## Need Help?

See full guide: `FUSION360_ROAD_PROJECTION_GUIDE.md`

## Regenerate Files

To regenerate with different settings:

```bash
# Generate DXF vector roads (recommended)
python generate_road_dxf.py --dem dem_data/terrain.tif --roads muir_rd_roads_all.geojson --output muir_rd_roads.dxf --width 100 --height 100

# Or generate PNG road map for manual tracing
python generate_road_map.py --dem dem_data/terrain.tif --roads muir_rd_roads_all.geojson --output muir_rd_road_map.png --width 5

# Generate new terrain (adjust config.json first)
python terrain_carver.py
```
