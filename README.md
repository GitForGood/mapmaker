# MapMaker 🗺️

**Transform OpenStreetMap data into beautiful SVG road network visualizations.**

MapMaker is a Python tool that converts OSM (OpenStreetMap) XML exports into clean, customizable SVG files perfect for wall art printing, design projects, or just admiring your favorite city's street layout.

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

> ### 🚀 Quick Start — Windows Users
> **[⬇️ Download MapMaker.exe](https://github.com/GitForGood/mapmaker/raw/main/dist/MapMaker.exe)** — No Python required!

---

## ✨ Features

- **One-shot conversion** — From OSM XML to SVG in a single command
- **Customizable color gradients** — Set colors for minor and major roads
- **Smart outlier clipping** — Automatically trim roads that extend far outside your selection
- **GUI & CLI** — Choose between a graphical interface or command-line usage
- **Windows executable** — Build a standalone `.exe` for easy distribution

---

## 📥 Getting the Map Data

### Step 1: Visit OpenStreetMap

Go to [**openstreetmap.org**](https://www.openstreetmap.org/) and navigate to the area you want to export.

### Step 2: Export Your Selection

Click the **Export** button in the top navigation. You'll see options to select your area on the map.

### ⚠️ Common Issue: "Area too large"

If you try to export directly and the area is too large, OpenStreetMap will display an error:

> *"You requested too many nodes (limit is 50000). Either request a smaller area, or use planet.osm"*

**Solution:** Use the **Overpass API** instead!

When you see this error, look in the **sidebar** of the export panel. You'll find a link that says:

> **Overpass API** — *use this for larger areas*

Click this link, and it will download the OSM XML file for your selected area without the node limit restriction.

---

## 🚀 Usage

### Command Line

```bash
# Basic usage with default grayscale gradient
python mapmaker.py mymap.osm

# Custom color gradient (hex colors)
python mapmaker.py map "#101010" "#7b7b7b"

# Using preset gradients
python mapmaker.py map --black-to-white
python mapmaker.py map --white-to-black

# Clip outlier roads and set output width
python mapmaker.py map "#101010" "#7b7b7b" --clip-outliers --width 4000

# Full example with all options
python mapmaker.py map.osm --from "#303030" --to "#a0a0a0" -c 5 -w 4000 -bg "#ffffff" -o output.svg
```

### GUI Application

Launch the graphical interface:

```bash
python mapmaker_gui.py
```

Or build and run the Windows executable:

```bash
build_exe.bat
# Executable will be in: dist\MapMaker.exe
```

---

## 📋 Command Line Options

### Color Options

| Option | Description |
|--------|-------------|
| `from_color` | Hex color for least important roads (positional) |
| `to_color` | Hex color for most important roads (positional) |
| `--from COLOR` | Alternative named argument for minor road color |
| `--to COLOR` | Alternative named argument for major road color |
| `--black-to-white` | Preset: white → black gradient |
| `--white-to-black` | Preset: black → white gradient |

**Supported color formats:**
- `#rrggbb` — Full hex (e.g., `#101010`)
- `rrggbb` — Full hex without # (e.g., `101010`)
- `#rgb` — Short hex (e.g., `#abc` → `#aabbcc`)
- `rgb` — Short hex without # (e.g., `abc`)
- `xx` — Single byte grayscale (e.g., `7b` → `#7b7b7b`)

### SVG Options

| Option | Description |
|--------|-------------|
| `-w, --width N` | SVG width in pixels (default: 2000) |
| `--height N` | SVG height (auto-calculated by default) |
| `-bg, --background` | Background color (default: transparent) |
| `-o, --output FILE` | Output filename (default: `road_map_<input>.svg`) |

### Clipping Options

| Option | Description |
|--------|-------------|
| `-c, --clip-outliers [N]` | Remove outlier roads using percentile-based bounds. Optional N specifies percentile to trim from each edge (default: 2%) |

---

## 🏗️ Road Priority System

Roads are styled with different widths and colors based on their importance:

| Priority | Road Types |
|----------|------------|
| **Highest** | Motorway, Trunk |
| **High** | Primary, Secondary |
| **Medium** | Tertiary, Residential, Unclassified |
| **Low** | Service, Pedestrian, Cycleway |
| **Lowest** | Footway, Path, Steps |

---

## 📦 Requirements

- Python 3.7+
- No external dependencies for basic usage in the command line

### Windows Executable

Download the standalone version: [**MapMaker.exe**](dist/MapMaker.exe)

---

## 🖼️ Example Output

The generated SVG files are perfect for:
- **Wall art prints** — Create stunning city map posters
- **Design projects** — Use as backgrounds or design elements
- **Laser cutting** — SVG format works great with CNC/laser cutters
- **Web graphics** — Scalable vectors for any resolution

---

## 📄 License

MIT License — feel free to use, modify, and distribute.

---

## 🙏 Acknowledgments

- Map data © [OpenStreetMap](https://www.openstreetmap.org/) contributors
- Inspired by [city-roads](https://anvaka.github.io/city-roads/) by Anvaka
