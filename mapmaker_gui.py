#!/usr/bin/env python3
"""
MapMaker GUI - Desktop application for generating SVG road maps from OSM data.

A graphical interface for the mapmaker.py script.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import os
import sys
import threading

# Import the core mapmaker functions
from mapmaker import (
    parse_osm_file, 
    get_bounds, 
    get_tight_bounds, 
    generate_svg, 
    generate_road_styles,
    parse_hex_color
)


class MapMakerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MapMaker - OSM to SVG Generator")
        self.root.geometry("600x780")
        self.root.resizable(True, True)
        
        # Variables
        self.map_file = tk.StringVar()
        self.output_file = tk.StringVar()
        self.from_color = tk.StringVar(value="#aaaaaa")
        self.to_color = tk.StringVar(value="#1a1a1a")
        self.width = tk.IntVar(value=2000)
        self.clip_outliers = tk.BooleanVar(value=True)
        self.clip_percent = tk.DoubleVar(value=2.0)
        self.background_color = tk.StringVar(value="")
        self.use_background = tk.BooleanVar(value=False)
        
        # Status
        self.is_processing = False
        
        self.create_widgets()
        
    def create_widgets(self):
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="MapMaker", font=("Segoe UI", 24, "bold"))
        title_label.pack(pady=(0, 5))
        
        subtitle_label = ttk.Label(main_frame, text="OSM to SVG Road Map Generator", 
                                   font=("Segoe UI", 10), foreground="gray")
        subtitle_label.pack(pady=(0, 20))
        
        # === File Selection Section ===
        file_frame = ttk.LabelFrame(main_frame, text="Input File", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 15))
        
        file_inner = ttk.Frame(file_frame)
        file_inner.pack(fill=tk.X)
        
        self.file_entry = ttk.Entry(file_inner, textvariable=self.map_file, width=50)
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        browse_btn = ttk.Button(file_inner, text="Browse...", command=self.browse_file)
        browse_btn.pack(side=tk.RIGHT)
        
        # === Color Section ===
        color_frame = ttk.LabelFrame(main_frame, text="Color Gradient", padding="10")
        color_frame.pack(fill=tk.X, pady=(0, 15))
        
        # From color (minor roads)
        from_frame = ttk.Frame(color_frame)
        from_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(from_frame, text="Minor Roads:", width=15).pack(side=tk.LEFT)
        
        self.from_color_preview = tk.Canvas(from_frame, width=30, height=25, 
                                            bg=self.from_color.get(), highlightthickness=1)
        self.from_color_preview.pack(side=tk.LEFT, padx=(0, 5))
        
        self.from_color_entry = ttk.Entry(from_frame, textvariable=self.from_color, width=12)
        self.from_color_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.from_color_entry.bind('<KeyRelease>', lambda e: self.update_color_preview('from'))
        
        from_pick_btn = ttk.Button(from_frame, text="Pick", width=6,
                                   command=lambda: self.pick_color('from'))
        from_pick_btn.pack(side=tk.LEFT)
        
        # To color (major roads)
        to_frame = ttk.Frame(color_frame)
        to_frame.pack(fill=tk.X)
        
        ttk.Label(to_frame, text="Major Roads:", width=15).pack(side=tk.LEFT)
        
        self.to_color_preview = tk.Canvas(to_frame, width=30, height=25,
                                          bg=self.to_color.get(), highlightthickness=1)
        self.to_color_preview.pack(side=tk.LEFT, padx=(0, 5))
        
        self.to_color_entry = ttk.Entry(to_frame, textvariable=self.to_color, width=12)
        self.to_color_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.to_color_entry.bind('<KeyRelease>', lambda e: self.update_color_preview('to'))
        
        to_pick_btn = ttk.Button(to_frame, text="Pick", width=6,
                                 command=lambda: self.pick_color('to'))
        to_pick_btn.pack(side=tk.LEFT)
        
        # Preset buttons
        preset_frame = ttk.Frame(color_frame)
        preset_frame.pack(fill=tk.X, pady=(15, 0))
        
        ttk.Label(preset_frame, text="Presets:", width=15).pack(side=tk.LEFT)
        
        ttk.Button(preset_frame, text="Light → Dark", 
                   command=lambda: self.set_preset("#aaaaaa", "#1a1a1a")).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="White → Black",
                   command=lambda: self.set_preset("#ffffff", "#000000")).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="Black → White",
                   command=lambda: self.set_preset("#000000", "#ffffff")).pack(side=tk.LEFT, padx=2)
        
        # === SVG Options Section ===
        options_frame = ttk.LabelFrame(main_frame, text="SVG Options", padding="10")
        options_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Width
        width_frame = ttk.Frame(options_frame)
        width_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(width_frame, text="Width (px):", width=15).pack(side=tk.LEFT)
        width_spin = ttk.Spinbox(width_frame, from_=500, to=10000, increment=100,
                                 textvariable=self.width, width=10)
        width_spin.pack(side=tk.LEFT)
        ttk.Label(width_frame, text="(height auto-calculated)", 
                  foreground="gray").pack(side=tk.LEFT, padx=(10, 0))
        
        # Background color
        bg_frame = ttk.Frame(options_frame)
        bg_frame.pack(fill=tk.X)
        
        self.bg_check = ttk.Checkbutton(bg_frame, text="Background Color:", 
                                        variable=self.use_background,
                                        command=self.toggle_background)
        self.bg_check.pack(side=tk.LEFT)
        
        self.bg_color_preview = tk.Canvas(bg_frame, width=30, height=25,
                                          bg="white", highlightthickness=1)
        self.bg_color_preview.pack(side=tk.LEFT, padx=(10, 5))
        
        self.bg_color_entry = ttk.Entry(bg_frame, textvariable=self.background_color, 
                                        width=12, state='disabled')
        self.bg_color_entry.pack(side=tk.LEFT, padx=(0, 5))
        
        self.bg_pick_btn = ttk.Button(bg_frame, text="Pick", width=6,
                                      command=lambda: self.pick_color('bg'), state='disabled')
        self.bg_pick_btn.pack(side=tk.LEFT)
        
        # === Clipping Section ===
        clip_frame = ttk.LabelFrame(main_frame, text="Outlier Clipping", padding="10")
        clip_frame.pack(fill=tk.X, pady=(0, 15))
        
        clip_check_frame = ttk.Frame(clip_frame)
        clip_check_frame.pack(fill=tk.X)
        
        self.clip_check = ttk.Checkbutton(clip_check_frame, 
                                          text="Clip outlier roads (recommended)",
                                          variable=self.clip_outliers,
                                          command=self.toggle_clip)
        self.clip_check.pack(side=tk.LEFT)
        
        clip_pct_frame = ttk.Frame(clip_frame)
        clip_pct_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(clip_pct_frame, text="Clip percentage:", width=15).pack(side=tk.LEFT)
        self.clip_spin = ttk.Spinbox(clip_pct_frame, from_=0.5, to=10.0, increment=0.5,
                                     textvariable=self.clip_percent, width=8)
        self.clip_spin.pack(side=tk.LEFT)
        ttk.Label(clip_pct_frame, text="% from each edge", 
                  foreground="gray").pack(side=tk.LEFT, padx=(5, 0))
        
        # === Output Section ===
        output_frame = ttk.LabelFrame(main_frame, text="Output File", padding="10")
        output_frame.pack(fill=tk.X, pady=(0, 15))
        
        output_inner = ttk.Frame(output_frame)
        output_inner.pack(fill=tk.X)
        
        self.output_entry = ttk.Entry(output_inner, textvariable=self.output_file, width=50)
        self.output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        output_browse_btn = ttk.Button(output_inner, text="Browse...", 
                                       command=self.browse_output)
        output_browse_btn.pack(side=tk.RIGHT)
        
        ttk.Label(output_frame, text="Leave empty to auto-generate from input filename",
                  foreground="gray").pack(anchor=tk.W, pady=(5, 0))
        
        # === Generate Button ===
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=(15, 10), fill=tk.X)
        
        self.generate_btn = tk.Button(
            btn_frame, 
            text="Generate SVG", 
            command=self.generate,
            font=("Segoe UI", 14, "bold"),
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            cursor="hand2",
            relief=tk.FLAT,
            padx=30,
            pady=12
        )
        self.generate_btn.pack()
        
        # === Status/Progress ===
        self.status_label = ttk.Label(main_frame, text="Ready", foreground="gray")
        self.status_label.pack(pady=(10, 5))
        
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate', length=400)
        self.progress.pack(pady=(5, 0))
        
        # Update color previews
        self.update_color_preview('from')
        self.update_color_preview('to')
        
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select OSM Map File",
            filetypes=[
                ("OSM XML files", "*.xml *.osm"),
                ("All files", "*.*")
            ]
        )
        if filename:
            self.map_file.set(filename)
            # Auto-generate output filename
            if not self.output_file.get():
                base = os.path.splitext(os.path.basename(filename))[0]
                self.output_file.set(f"road_map_{base}.svg")
    
    def browse_output(self):
        filename = filedialog.asksaveasfilename(
            title="Save SVG As",
            defaultextension=".svg",
            filetypes=[("SVG files", "*.svg"), ("All files", "*.*")]
        )
        if filename:
            self.output_file.set(filename)
    
    def pick_color(self, which):
        if which == 'from':
            initial = self.from_color.get()
        elif which == 'to':
            initial = self.to_color.get()
        else:
            initial = self.background_color.get() or "#ffffff"
        
        try:
            color = colorchooser.askcolor(color=initial, title="Choose Color")
            if color[1]:
                if which == 'from':
                    self.from_color.set(color[1])
                elif which == 'to':
                    self.to_color.set(color[1])
                else:
                    self.background_color.set(color[1])
                self.update_color_preview(which)
        except:
            pass
    
    def update_color_preview(self, which):
        try:
            if which == 'from':
                color = self.from_color.get()
                # Validate and normalize
                rgb = parse_hex_color(color)
                normalized = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
                self.from_color_preview.configure(bg=normalized)
            elif which == 'to':
                color = self.to_color.get()
                rgb = parse_hex_color(color)
                normalized = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
                self.to_color_preview.configure(bg=normalized)
            elif which == 'bg':
                color = self.background_color.get()
                if color:
                    rgb = parse_hex_color(color)
                    normalized = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
                    self.bg_color_preview.configure(bg=normalized)
        except:
            pass  # Invalid color, ignore
    
    def set_preset(self, from_col, to_col):
        self.from_color.set(from_col)
        self.to_color.set(to_col)
        self.update_color_preview('from')
        self.update_color_preview('to')
    
    def toggle_background(self):
        if self.use_background.get():
            self.bg_color_entry.configure(state='normal')
            self.bg_pick_btn.configure(state='normal')
            if not self.background_color.get():
                self.background_color.set("#ffffff")
                self.update_color_preview('bg')
        else:
            self.bg_color_entry.configure(state='disabled')
            self.bg_pick_btn.configure(state='disabled')
    
    def toggle_clip(self):
        if self.clip_outliers.get():
            self.clip_spin.configure(state='normal')
        else:
            self.clip_spin.configure(state='disabled')
    
    def set_status(self, text, color="gray"):
        self.status_label.configure(text=text, foreground=color)
        self.root.update_idletasks()
    
    def generate(self):
        if self.is_processing:
            return
        
        # Validate inputs
        map_file = self.map_file.get()
        if not map_file:
            messagebox.showerror("Error", "Please select an input map file.")
            return
        
        if not os.path.exists(map_file):
            messagebox.showerror("Error", f"File not found: {map_file}")
            return
        
        try:
            from_color = parse_hex_color(self.from_color.get())
            to_color = parse_hex_color(self.to_color.get())
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid color: {e}")
            return
        
        # Determine output file
        output_file = self.output_file.get()
        if not output_file:
            base = os.path.splitext(os.path.basename(map_file))[0]
            output_file = f"road_map_{base}.svg"
        
        # Start processing in background thread
        self.is_processing = True
        self.generate_btn.configure(state='disabled')
        self.progress.start(10)
        
        thread = threading.Thread(target=self.do_generate, args=(
            map_file, output_file, from_color, to_color
        ))
        thread.daemon = True
        thread.start()
    
    def do_generate(self, map_file, output_file, from_color, to_color):
        try:
            # Parse
            self.set_status("Parsing map file...", "blue")
            nodes, ways = parse_osm_file(map_file)
            
            if not nodes or not ways:
                raise ValueError("No road data found in the map file!")
            
            # Calculate bounds
            self.set_status("Calculating bounds...", "blue")
            if self.clip_outliers.get():
                bounds = get_tight_bounds(nodes, percentile=self.clip_percent.get())
            else:
                bounds = get_bounds(nodes)
            
            # Generate styles
            road_styles = generate_road_styles(from_color, to_color)
            
            # Generate SVG
            self.set_status("Generating SVG...", "blue")
            bg_color = self.background_color.get() if self.use_background.get() else None
            
            generate_svg(
                nodes, ways, bounds, output_file, road_styles,
                width=self.width.get(),
                background_color=bg_color
            )
            
            # Done
            self.set_status(f"✓ Saved to: {output_file}", "green")
            
            # Ask to open
            self.root.after(0, lambda: self.ask_open_file(output_file))
            
        except Exception as e:
            self.set_status(f"Error: {str(e)}", "red")
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
        
        finally:
            self.is_processing = False
            self.root.after(0, self.finish_processing)
    
    def finish_processing(self):
        self.progress.stop()
        self.generate_btn.configure(state='normal', bg="#2563eb")
    
    def ask_open_file(self, filepath):
        if messagebox.askyesno("Success", 
                               f"SVG generated successfully!\n\n{filepath}\n\nOpen the file?"):
            os.startfile(filepath)


def main():
    root = tk.Tk()
    
    # Try to use a modern theme
    try:
        root.tk.call("source", "azure.tcl")
        root.tk.call("set_theme", "light")
    except:
        pass  # Use default theme
    
    # Set icon if available
    try:
        root.iconbitmap("mapmaker.ico")
    except:
        pass
    
    app = MapMakerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
