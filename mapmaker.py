#!/usr/bin/env python3
"""
MapMaker - One-shot OSM Map to SVG Generator

Transforms an OpenStreetMap XML file directly into an SVG road network visualization.
Import using the Overpass API for best experience using the link in the export UI 
on https://www.openstreetmap.org/.

Usage:
    python mapmaker.py <map_file> [from_color] [to_color] [options]

Examples:
    python mapmaker.py map "#101010" "#7b7b7b"
    python mapmaker.py map --from "#101010" --to "#7b7b7b"
    python mapmaker.py map --black-to-white
    python mapmaker.py map --white-to-black
    python mapmaker.py map "#101010" "#7b7b7b" --clip-outliers
    python mapmaker.py map "#101010" "#7b7b7b" -c 5 -w 4000 -o output.svg

Arguments:
    map_file            Input OSM map file (XML format, with or without extension)
    from_color          Hex color for minor roads (e.g., "#aaaaaa", "aaa", or "aa")
    to_color            Hex color for major roads (e.g., "#1a1a1a", "1a1", or "1a")

Color Options:
    --from COLOR        Hex color for least important roads (alternative to positional)
    --to COLOR          Hex color for most important roads (alternative to positional)
    --black-to-white    Preset: white (#ffffff) for minor → black (#000000) for major
    --white-to-black    Preset: black (#000000) for minor → white (#ffffff) for major

    Color formats supported:
        #rrggbb     Full hex (e.g., "#101010")
        rrggbb      Full hex without # (e.g., "101010")
        #rgb        Short hex (e.g., "#abc" → "#aabbcc")
        rgb         Short hex without # (e.g., "abc")
        xx          Single byte grayscale (e.g., "7b" → "#7b7b7b")

SVG Options:
    -w, --width N       SVG width in pixels (default: 2000, height auto-calculated)
    --height N          SVG height in pixels (overrides auto-calculation)
    -bg, --background   Background color (default: transparent)
    -o, --output FILE   Output SVG filename (default: road_map_<input>.svg)

Clipping Options:
    -c, --clip-outliers [N]
                        Remove outlier roads using percentile-based bounds.
                        Roads extending far outside the main area are excluded.
                        Optional N specifies percentile to trim from each edge.
                        Default: 2% (uses 2nd to 98th percentile of coordinates)
                        Example: --clip-outliers or --clip-outliers 5
"""

import xml.etree.ElementTree as ET
import os
import sys
import math
import argparse
from collections import defaultdict


# Road types ordered from least important (small) to most important (big)
# This determines the gradient mapping
ROAD_PRIORITY = [
    # Least important (will get 'from' color)
    'proposed',
    'corridor',
    'elevator',
    'construction',
    'platform',
    'steps',
    'footway',
    'path',
    'cycleway',
    'pedestrian',
    'service',
    'living_street',
    'residential',
    'unclassified',
    'busway',
    'tertiary_link',
    'tertiary',
    'secondary_link',
    'secondary',
    'primary_link',
    'primary',
    'trunk_link',
    'trunk',
    'motorway_link',
    'motorway',
    # Most important (will get 'to' color)
]

# Road width mapping - (stroke-width, z-index priority)
ROAD_WIDTHS = {
    'motorway': (4, 100),
    'motorway_link': (3, 99),
    'trunk': (4, 90),
    'trunk_link': (3, 89),
    'primary': (3.5, 80),
    'primary_link': (2.5, 79),
    'secondary': (3, 70),
    'secondary_link': (2, 69),
    'tertiary': (2.5, 60),
    'tertiary_link': (2, 59),
    'residential': (2, 50),
    'unclassified': (2, 50),
    'living_street': (1.5, 45),
    'service': (1, 40),
    'pedestrian': (1.5, 30),
    'footway': (0.5, 20),
    'path': (0.5, 20),
    'cycleway': (0.8, 25),
    'steps': (0.5, 20),
    'busway': (2, 55),
    'construction': (1.5, 10),
    'proposed': (0.5, 5),
    'corridor': (0.3, 5),
    'platform': (1, 15),
    'elevator': (0.3, 5),
}

DEFAULT_WIDTH = (1, 25)


def parse_hex_color(color_str):
    """
    Parse a hex color string and return (r, g, b) tuple.
    Accepts formats: #rrggbb, rrggbb, #rgb, rgb, or single byte (aa -> #aaaaaa)
    """
    # Remove # prefix if present
    color = color_str.lstrip('#')
    
    if len(color) == 6:
        # Full hex: rrggbb
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
    elif len(color) == 3:
        # Short hex: rgb -> rrggbb
        r = int(color[0] * 2, 16)
        g = int(color[1] * 2, 16)
        b = int(color[2] * 2, 16)
    elif len(color) <= 2:
        # Single byte grayscale: aa -> #aaaaaa
        val = int(color, 16)
        r = g = b = val
    else:
        raise ValueError(f"Invalid hex color format: {color_str}")
    
    return (r, g, b)


def interpolate_color(from_color, to_color, ratio):
    """
    Interpolate between two RGB color tuples (0.0 = from, 1.0 = to).
    Returns a hex color string.
    """
    r = int(from_color[0] + (to_color[0] - from_color[0]) * ratio)
    g = int(from_color[1] + (to_color[1] - from_color[1]) * ratio)
    b = int(from_color[2] + (to_color[2] - from_color[2]) * ratio)
    
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    
    return f"#{r:02x}{g:02x}{b:02x}"


def generate_road_styles(from_color, to_color):
    """
    Generate road styles with colors interpolated from 'from_color' to 'to_color'.
    Both arguments should be (r, g, b) tuples.
    """
    styles = {}
    num_types = len(ROAD_PRIORITY)
    
    for i, road_type in enumerate(ROAD_PRIORITY):
        # Ratio: 0.0 for first (least important), 1.0 for last (most important)
        ratio = i / (num_types - 1) if num_types > 1 else 0.5
        color = interpolate_color(from_color, to_color, ratio)
        
        width, z_index = ROAD_WIDTHS.get(road_type, DEFAULT_WIDTH)
        styles[road_type] = (width, color, z_index)
    
    return styles


def parse_osm_file(filepath):
    """
    Parse an OSM XML file and extract nodes and highway ways.
    Uses iterparse for memory-efficient parsing of large files.
    Returns nodes dict and ways list directly (no intermediate file).
    """
    print(f"Parsing {filepath}...")
    print("This may take a while for large files...")
    
    nodes = {}
    ways = []
    highway_node_refs = set()
    
    # First pass: collect all ways with highway tags and their node references
    print("\nPass 1: Collecting highway ways...")
    way_count = 0
    
    context = ET.iterparse(filepath, events=('end',))
    
    for event, elem in context:
        if elem.tag == 'way':
            tags = {}
            node_refs = []
            has_highway = False
            
            for child in elem:
                if child.tag == 'nd':
                    node_refs.append(child.get('ref'))
                elif child.tag == 'tag':
                    key = child.get('k')
                    value = child.get('v')
                    tags[key] = value
                    if key == 'highway':
                        has_highway = True
            
            if has_highway:
                way_data = {
                    'id': elem.get('id'),
                    'node_refs': node_refs,
                    'tags': tags
                }
                ways.append(way_data)
                highway_node_refs.update(node_refs)
                way_count += 1
                
                if way_count % 500 == 0:
                    print(f"  Found {way_count} highway ways...")
            
            elem.clear()
        elif elem.tag == 'node':
            elem.clear()
        elif elem.tag == 'relation':
            elem.clear()
    
    print(f"  Total highway ways found: {way_count}")
    print(f"  Total node references: {len(highway_node_refs)}")
    
    # Second pass: collect only nodes that are referenced by highways
    print("\nPass 2: Collecting referenced nodes...")
    node_count = 0
    
    context = ET.iterparse(filepath, events=('end',))
    
    for event, elem in context:
        if elem.tag == 'node':
            node_id = elem.get('id')
            
            if node_id in highway_node_refs:
                tags = {}
                for child in elem:
                    if child.tag == 'tag':
                        tags[child.get('k')] = child.get('v')
                
                nodes[node_id] = {
                    'lat': float(elem.get('lat')),
                    'lon': float(elem.get('lon')),
                    'tags': tags if tags else None
                }
                
                node_count += 1
                if node_count % 5000 == 0:
                    print(f"  Collected {node_count} nodes...")
            
            elem.clear()
        elif elem.tag in ('way', 'relation'):
            elem.clear()
    
    print(f"  Total nodes collected: {node_count}")
    
    return nodes, ways


def get_bounds(nodes):
    """Calculate the bounding box of all nodes."""
    if not nodes:
        return None
    
    lats = [n['lat'] for n in nodes.values()]
    lons = [n['lon'] for n in nodes.values()]
    
    return {
        'min_lat': min(lats),
        'max_lat': max(lats),
        'min_lon': min(lons),
        'max_lon': max(lons)
    }


def get_tight_bounds(nodes, percentile=2):
    """
    Calculate a tight bounding box by excluding outlier nodes.
    Uses percentiles to find the core area, cutting off roads that 
    extend far outside the main selection.
    
    Args:
        nodes: Dictionary of node data
        percentile: Percentage to trim from each side (default: 2%)
                   A value of 2 means we use the 2nd to 98th percentile
    """
    if not nodes:
        return None
    
    lats = sorted([n['lat'] for n in nodes.values()])
    lons = sorted([n['lon'] for n in nodes.values()])
    
    n = len(lats)
    if n < 10:
        # Not enough nodes for percentile-based trimming
        return get_bounds(nodes)
    
    # Calculate indices for percentile bounds
    low_idx = int(n * percentile / 100)
    high_idx = int(n * (100 - percentile) / 100) - 1
    
    # Ensure valid indices
    low_idx = max(0, low_idx)
    high_idx = min(n - 1, high_idx)
    
    return {
        'min_lat': lats[low_idx],
        'max_lat': lats[high_idx],
        'min_lon': lons[low_idx],
        'max_lon': lons[high_idx]
    }


def lat_lon_to_svg(lat, lon, bounds, width, height, padding=20):
    """
    Convert latitude/longitude to SVG coordinates.
    Note: Latitude increases northward, but SVG Y increases downward,
    so we flip the Y axis.
    """
    min_lat, max_lat = bounds['min_lat'], bounds['max_lat']
    min_lon, max_lon = bounds['min_lon'], bounds['max_lon']
    
    usable_width = width - 2 * padding
    usable_height = height - 2 * padding
    
    x_normalized = (lon - min_lon) / (max_lon - min_lon)
    y_normalized = (lat - min_lat) / (max_lat - min_lat)
    
    x = padding + x_normalized * usable_width
    y = padding + (1 - y_normalized) * usable_height
    
    return x, y



def generate_svg(nodes, ways, bounds, output_file, road_styles, 
                 width=2000, height=None, background_color=None,
                 show_only=None, line_cap='round', line_join='round'):
    """
    Generate an SVG file from the road data.
    """
    # Calculate height to maintain aspect ratio
    lat_range = bounds['max_lat'] - bounds['min_lat']
    lon_range = bounds['max_lon'] - bounds['min_lon']
    
    avg_lat = (bounds['min_lat'] + bounds['max_lat']) / 2
    lat_factor = math.cos(math.radians(avg_lat))
    aspect_ratio = (lat_range) / (lon_range * lat_factor)
    
    if height is None:
        height = int(width * aspect_ratio)
    
    print(f"\nGenerating SVG: {width}x{height} pixels")
    print(f"  Bounds: lat {bounds['min_lat']:.4f}-{bounds['max_lat']:.4f}, "
          f"lon {bounds['min_lon']:.4f}-{bounds['max_lon']:.4f}")
    
    # Group ways by highway type for z-ordering
    ways_by_type = defaultdict(list)
    for way in ways:
        highway_type = way['tags'].get('highway', 'unknown')
        if show_only is None or highway_type in show_only:
            ways_by_type[highway_type].append(way)
    
    # Sort types by z-index
    sorted_types = sorted(
        ways_by_type.keys(),
        key=lambda t: road_styles.get(t, (*DEFAULT_WIDTH, '#888888'))[2] if len(road_styles.get(t, ())) >= 3 else 25
    )
    
    # Start building SVG
    padding = 20
    
    svg_parts = []
    svg_parts.append(f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" 
     width="{width}" height="{height}" 
     viewBox="0 0 {width} {height}">
  <title>Road Network Map</title>
  <desc>Generated from OpenStreetMap data</desc>
''')
    
    if background_color:
        svg_parts.append(f'''  <!-- Background -->
  <rect width="100%" height="100%" fill="{background_color}"/>''')
    
    svg_parts.append('''
  
  <!-- Roads -->
  <g>
''')
    
    total_paths = 0
    skipped_ways = 0
    
    # Draw roads in z-order
    for highway_type in sorted_types:
        type_ways = ways_by_type[highway_type]
        style = road_styles.get(highway_type)
        
        if style:
            stroke_width, color, _ = style
        else:
            stroke_width, _ = DEFAULT_WIDTH
            color = '#888888'
        
        svg_parts.append(f'  <!-- {highway_type}: {len(type_ways)} roads -->\n')
        svg_parts.append(f'  <g class="highway-{highway_type}" '
                        f'stroke="{color}" stroke-width="{stroke_width}" '
                        f'stroke-linecap="{line_cap}" stroke-linejoin="{line_join}" '
                        f'fill="none">\n')
        
        for way in type_ways:
            path_points = []
            valid = True
            
            for node_ref in way['node_refs']:
                if node_ref not in nodes:
                    valid = False
                    break
                node = nodes[node_ref]
                x, y = lat_lon_to_svg(node['lat'], node['lon'], bounds, width, height)
                path_points.append((x, y))
            
            if not valid or len(path_points) < 2:
                skipped_ways += 1
                continue
            
            # Build path data
            path_d = f"M {path_points[0][0]:.2f} {path_points[0][1]:.2f}"
            for x, y in path_points[1:]:
                path_d += f" L {x:.2f} {y:.2f}"
            
            road_name = way['tags'].get('name', '')
            way_id = way['id']
            
            if road_name:
                svg_parts.append(f'    <path d="{path_d}" data-id="{way_id}" data-name="{road_name}"/>\n')
            else:
                svg_parts.append(f'    <path d="{path_d}" data-id="{way_id}"/>\n')
            
            total_paths += 1
        
        svg_parts.append('  </g>\n\n')
    
    svg_parts.append('  </g>\n')
    svg_parts.append('</svg>\n')
    
    # Write file
    print(f"Writing {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(svg_parts)
    
    file_size = os.path.getsize(output_file)
    print(f"\nSVG generation complete!")
    print(f"  Total paths drawn: {total_paths}")
    print(f"  Skipped ways (missing nodes): {skipped_ways}")
    print(f"  File size: {file_size / 1024 / 1024:.2f} MB")
    
    return output_file


def main():
    parser = argparse.ArgumentParser(
        description='Generate SVG road map from OSM data',
        usage='%(prog)s map_file [from_hex to_hex] [options]'
    )
    
    # Positional arguments
    parser.add_argument('map_file', 
                        help='Input OSM map file (XML format, with or without extension)')
    parser.add_argument('from_color', nargs='?', default=None,
                        help='Hex color for least important roads (e.g., "#aaaaaa" or "aa")')
    parser.add_argument('to_color', nargs='?', default=None,
                        help='Hex color for most important roads (e.g., "#1a1a1a" or "1a")')
    
    # Named gradient arguments (alternative to positional)
    parser.add_argument('--from', dest='from_hex', default=None,
                        help='Hex color for least important roads (e.g., "#aaaaaa")')
    parser.add_argument('--to', dest='to_hex', default=None,
                        help='Hex color for most important roads (e.g., "#1a1a1a")')
    
    # Preset gradients
    parser.add_argument('--black-to-white', action='store_true',
                        help='Use gradient from black (major) to white (minor)')
    parser.add_argument('--white-to-black', action='store_true',
                        help='Use gradient from white (minor) to black (major)')
    
    # SVG options
    parser.add_argument('--width', '-w', type=int, default=2000,
                        help='SVG width in pixels (default: 2000)')
    parser.add_argument('--height', type=int, default=None,
                        help='SVG height (auto-calculated if not specified)')
    parser.add_argument('--background', '-bg', default=None,
                        help='Background color (default: transparent)')
    parser.add_argument('--output', '-o', default=None,
                        help='Output SVG file (default: road_map_<input>.svg)')
    parser.add_argument('--clip-outliers', '-c', type=float, nargs='?', const=2.0, default=None,
                        metavar='PERCENT',
                        help='Clip outlier roads using percentile-based bounds. '
                             'Optional value specifies percentile to trim (default: 2%%). '
                             'Example: --clip-outliers or --clip-outliers 5')
    
    args = parser.parse_args()
    
    # Resolve input file
    map_file = args.map_file
    if not os.path.exists(map_file):
        # Try adding common extensions
        for ext in ['', '.xml', '.osm']:
            test_path = map_file + ext
            if os.path.exists(test_path):
                map_file = test_path
                break
        else:
            print(f"Error: Map file '{args.map_file}' not found!")
            sys.exit(1)
    
    # Determine gradient colors
    from_color_str = args.from_hex or args.from_color
    to_color_str = args.to_hex or args.to_color
    
    if args.black_to_white:
        from_color_str = '#ffffff'  # White for minor
        to_color_str = '#000000'    # Black for major
    elif args.white_to_black:
        from_color_str = '#000000'  # Black for minor  
        to_color_str = '#ffffff'    # White for major
    elif from_color_str is None or to_color_str is None:
        # Default: light gray to dark gray
        from_color_str = '#aaaaaa'
        to_color_str = '#1a1a1a'
    
    # Parse hex colors
    try:
        from_color = parse_hex_color(from_color_str)
        to_color = parse_hex_color(to_color_str)
    except ValueError as e:
        print(f"Error: {e}")
        print("Use formats like '#101010', '101010', '#abc', 'abc', or '7b' (grayscale)")
        sys.exit(1)
    
    from_hex = f"#{from_color[0]:02x}{from_color[1]:02x}{from_color[2]:02x}"
    to_hex = f"#{to_color[0]:02x}{to_color[1]:02x}{to_color[2]:02x}"
    print(f"Using color gradient: {from_hex} (minor) → {to_hex} (major)")
    
    # Generate road styles
    road_styles = generate_road_styles(from_color, to_color)
    
    # Determine output filename
    if args.output:
        output_file = args.output
    else:
        base_name = os.path.splitext(os.path.basename(map_file))[0]
        output_file = f"road_map_{base_name}.svg"
    
    # Parse the map file
    nodes, ways = parse_osm_file(map_file)
    
    if not nodes or not ways:
        print("Error: No road data found in the map file!")
        sys.exit(1)
    
    # Calculate bounds (use tight bounds if clipping outliers)
    if args.clip_outliers is not None:
        bounds = get_tight_bounds(nodes, percentile=args.clip_outliers)
        print(f"Using tight bounds (clipping {args.clip_outliers}% outliers from each edge)")
    else:
        bounds = get_bounds(nodes)
    
    # Generate SVG
    generate_svg(
        nodes, 
        ways, 
        bounds,
        output_file,
        road_styles,
        width=args.width,
        height=args.height,
        background_color=args.background
    )
    
    print(f"\nOutput saved to: {output_file}")


if __name__ == '__main__':
    main()
