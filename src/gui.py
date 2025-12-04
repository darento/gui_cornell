import glob
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import subprocess
import threading
import os
import signal
from PIL import Image, ImageTk

# Set CustomTkinter appearance
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme(
    "dark-blue"
)  # Themes: "blue" (standard), "green", "dark-blue"
# Force polygon-based drawing instead of font-based
ctk.DrawEngine.preferred_drawing_method = "polygon_shapes"

SPLIT_TIME_OFFSET = 0.1  # seconds
MAX_SPLIT_FILES = max(1, os.cpu_count() - 2)  # CPU cores - 2 for safety


def clean_tmp_and_shm():
    # Remove socket file if exists.
    if os.path.exists("/tmp/d.sock"):
        subprocess.call("rm /tmp/d.sock", shell=True)
    # Remove shared-memory file if exists.
    if os.path.exists("/dev/shm/daqd_shm"):
        subprocess.call("rm /dev/shm/daqd_shm", shell=True)


class PETsysGUIApp:
    def __init__(self, root):
        # Clean at startup
        clean_tmp_and_shm()

        self.root = root
        self.root.title("MAGUI Cornell - PETsys Manager - LM file converter")
        self.root.geometry("900x900")  # Increased size slightly for CTk spacing
        # self.root.maxsize(1400, 900) # Optional
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Initialize variables
        self.initialize_variables()

        # Create Tabview (replaces Notebook)
        self.tabview = ctk.CTkTabview(root)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=5)

        # Create tabs
        self.tabview.add("System Setup & Acquisition")
        self.tabview.add("RAWF to LDAT Conversion")
        self.tabview.add("LDAT Processing")
        self.tabview.add("LM File Generation")

        self.setup_tab = self.tabview.tab("System Setup & Acquisition")
        self.rawf_to_ldat_tab = self.tabview.tab("RAWF to LDAT Conversion")
        self.ldat_proc_tab = self.tabview.tab("LDAT Processing")
        self.lm_generation_tab = self.tabview.tab("LM File Generation")

        # Populate tabs
        self.setup_acquisition_tab()
        self.setup_rawf_to_ldat_tab()
        self.setup_ldat_proc_tab()
        self.setup_lm_generation_tab()

        # Common output text area (shared across tabs)
        self.output_frame = ctk.CTkFrame(root)
        self.output_frame.pack(fill="both", expand=True, padx=10, pady=5)

        ctk.CTkLabel(self.output_frame, text="Output Log:").pack(
            anchor="w", padx=5, pady=(5, 0)
        )
        self.output_text = ctk.CTkTextbox(self.output_frame, width=800, height=150)
        self.output_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Add the logo at the bottom
        self.add_logo()

    def log_message(self, message):
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)  # force scroll to the bottom

    def initialize_variables(self):
        # Common parameters
        self.petsys_folder = ""
        self.output_data_folder = ""
        self.acq_file_name = "data_file"
        self.acq_time = 10
        self.split_files = 1
        self.config_file = ""
        self.daqd_process = None
        self.system_initialized = False

        # Processing parameters (shared by LDAT processing and LM generation)
        self.process_petsys_folder = ""
        self.process_config_file = ""

        # LM file generation parameters
        self.lm_input_file = ""
        self.lm_encal_file = ""
        self.lm_cog_limits_file = ""

    def create_labeled_frame(self, parent, title):
        frame = ctk.CTkFrame(parent)
        label = ctk.CTkLabel(
            frame, text=title, font=ctk.CTkFont(size=14, weight="bold")
        )
        label.grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(5, 0))
        return frame

    def setup_acquisition_tab(self):
        # --- Settings Frame ---
        settings_frame = self.create_labeled_frame(self.setup_tab, "Settings")
        settings_frame.pack(padx=10, pady=5, fill="x")

        # Grid configuration for settings_frame
        settings_frame.grid_columnconfigure(1, weight=1)

        # PETsys Folder
        ctk.CTkLabel(settings_frame, text="PETsys Folder:").grid(
            row=1, column=0, sticky="e", padx=5, pady=2
        )
        self.petsys_entry = ctk.CTkEntry(settings_frame)
        self.petsys_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        ctk.CTkButton(
            settings_frame, text="Browse", command=self.browse_petsys_folder, width=100
        ).grid(row=1, column=2, padx=5, pady=2)

        # Output Data Folder
        ctk.CTkLabel(settings_frame, text="Output Data Folder:").grid(
            row=2, column=0, sticky="e", padx=5, pady=2
        )
        self.output_entry = ctk.CTkEntry(settings_frame)
        self.output_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")
        ctk.CTkButton(
            settings_frame, text="Browse", command=self.browse_output_folder, width=100
        ).grid(row=2, column=2, padx=5, pady=2)

        # Config File
        ctk.CTkLabel(settings_frame, text="Config File:").grid(
            row=3, column=0, sticky="e", padx=5, pady=2
        )
        self.config_entry = ctk.CTkEntry(settings_frame)
        self.config_entry.grid(row=3, column=1, padx=5, pady=2, sticky="ew")
        ctk.CTkButton(
            settings_frame, text="Browse", command=self.browse_config_file, width=100
        ).grid(row=3, column=2, padx=5, pady=2)

        # Acquisition file name
        ctk.CTkLabel(settings_frame, text="Acquisition File Name:").grid(
            row=4, column=0, sticky="e", padx=5, pady=2
        )
        self.acq_file_entry = ctk.CTkEntry(settings_frame)
        self.acq_file_entry.grid(row=4, column=1, padx=5, pady=2, sticky="ew")
        self.acq_file_entry.insert(0, "data_file")

        # Acquisition Time
        ctk.CTkLabel(settings_frame, text="Acq. Time (s):").grid(
            row=5, column=0, sticky="e", padx=5, pady=2
        )
        self.acq_entry = ctk.CTkEntry(settings_frame, width=100)
        self.acq_entry.grid(row=5, column=1, sticky="w", padx=5, pady=2)
        self.acq_entry.insert(0, "10")

        # --- Processing Settings for PETSYS Scripts ---
        proc_settings_frame2 = self.create_labeled_frame(
            settings_frame, "Process LDAT files Settings"
        )
        proc_settings_frame2.grid(
            row=6, column=0, columnspan=3, padx=5, pady=10, sticky="ew"
        )
        proc_settings_frame2.grid_columnconfigure(1, weight=1)

        # Process PETSYS Folder
        ctk.CTkLabel(proc_settings_frame2, text="'process_petsys' sw Folder:").grid(
            row=1, column=0, sticky="e", padx=5, pady=2
        )
        self.process_petsys_entry = ctk.CTkEntry(proc_settings_frame2)
        self.process_petsys_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        ctk.CTkButton(
            proc_settings_frame2,
            text="Browse",
            command=self.browse_process_petsys_folder,
            width=100,
        ).grid(row=1, column=2, padx=5, pady=2)

        # Processing Config File
        ctk.CTkLabel(proc_settings_frame2, text="YAML Config File:").grid(
            row=2, column=0, sticky="e", padx=5, pady=2
        )
        self.process_config_entry = ctk.CTkEntry(proc_settings_frame2)
        self.process_config_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")
        ctk.CTkButton(
            proc_settings_frame2,
            text="Browse",
            command=self.browse_process_config_file,
            width=100,
        ).grid(row=2, column=2, padx=5, pady=2)

        # --- Create two-column layout: Left (System Control + Data Acquisition) | Right (Pipeline) ---
        columns_container = ctk.CTkFrame(self.setup_tab, fg_color="transparent")
        columns_container.pack(padx=10, pady=5, fill="both", expand=True)
        columns_container.grid_columnconfigure(0, weight=1)
        columns_container.grid_columnconfigure(1, weight=1)

        # LEFT COLUMN: System Control and Data Acquisition
        left_column = ctk.CTkFrame(columns_container, fg_color="transparent")
        left_column.grid(row=0, column=0, padx=(0, 5), sticky="nsew")

        # --- System Control Frame ---
        control_frame = self.create_labeled_frame(left_column, "System Control")
        control_frame.pack(padx=10, pady=5, fill="x")

        # DAQD Toggle
        self.daqd_state = tk.BooleanVar(value=False)
        self.daqd_toggle = ctk.CTkCheckBox(
            control_frame,
            text="DAQD OFF",
            variable=self.daqd_state,
            command=self.toggle_daqd,
            onvalue=True,
            offvalue=False,
        )
        self.daqd_toggle.grid(row=1, column=0, padx=20, pady=10)

        # System Initialization
        self.init_system_button = ctk.CTkButton(
            control_frame, text="Initialize System", command=self.init_system
        )
        self.init_system_button.grid(row=1, column=1, padx=20, pady=10)

        # --- Acquisition Frame ---
        acq_frame = self.create_labeled_frame(left_column, "Data Acquisition")
        acq_frame.pack(padx=10, pady=5, fill="x")

        # Hardware Trigger flag (checkbutton)
        self.hw_trigger = tk.BooleanVar(value=False)
        self.hw_trigger_cb = ctk.CTkCheckBox(
            acq_frame,
            text="Enable Hardware Trigger",
            variable=self.hw_trigger,
            onvalue=True,
            offvalue=False,
        )
        self.hw_trigger_cb.grid(row=1, column=0, padx=20, pady=10)

        # Acquire button
        self.acquire_button = ctk.CTkButton(
            acq_frame, text="Acquire Data", command=self.acquire_data, state="disabled"
        )
        self.acquire_button.grid(row=1, column=1, padx=20, pady=10)

        # RIGHT COLUMN: Complete Pipeline
        right_column = ctk.CTkFrame(columns_container, fg_color="transparent")
        right_column.grid(row=0, column=1, padx=(5, 0), sticky="nsew")

        # --- Complete Pipeline Frame (Fancy Automation Button) ---
        pipeline_frame = self.create_labeled_frame(
            right_column, "🚀 Complete Automated Pipeline"
        )
        pipeline_frame.pack(padx=10, pady=5, fill="both", expand=True)

        # Configure grid column to expand
        pipeline_frame.grid_columnconfigure(0, weight=1)

        # Add description
        desc_label = ctk.CTkLabel(
            pipeline_frame,
            text="Execute the complete workflow:\nAcquire → Convert → Calibrate → Generate LM",
            font=ctk.CTkFont(size=12, weight="normal"),
            text_color="gray30",  # Darker gray for better readability
            justify="center",
        )
        desc_label.grid(row=1, column=0, padx=20, pady=(10, 10), sticky="ew")

        # Big fancy pipeline button
        self.pipeline_button = ctk.CTkButton(
            pipeline_frame,
            text="▶ RUN COMPLETE PIPELINE",
            command=self.run_complete_pipeline,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            fg_color="#2ecc71",  # Vibrant green when enabled
            hover_color="#27ae60",  # Darker green on hover
            text_color="white",  # White text for better contrast
            state="disabled",
        )
        self.pipeline_button.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        # Status label for pipeline progress
        self.pipeline_status_label = ctk.CTkLabel(
            pipeline_frame,
            text="",
            font=ctk.CTkFont(size=10),
            text_color="orange",
        )
        self.pipeline_status_label.grid(
            row=3, column=0, padx=20, pady=(0, 10), sticky="ew"
        )

    def setup_rawf_to_ldat_tab(self):
        # --- Data File Selection for Processing ---
        proc_file_frame = self.create_labeled_frame(
            self.rawf_to_ldat_tab, "Data File Selection"
        )
        proc_file_frame.pack(padx=10, pady=5, fill="x")
        proc_file_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(proc_file_frame, text="Data File:").grid(
            row=1, column=0, sticky="e", padx=5, pady=2
        )
        self.proc_data_entry = ctk.CTkEntry(proc_file_frame)
        self.proc_data_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        # Set default to acquisition file
        if not self.proc_data_entry.get().strip():
            self.proc_data_entry.insert(0, "rawf_file_basename")
        ctk.CTkButton(
            proc_file_frame, text="Browse", command=self.browse_rawf_file, width=100
        ).grid(row=1, column=2, padx=5, pady=2)

        # --- Processing Settings Frame ---
        proc_settings_frame = self.create_labeled_frame(
            self.rawf_to_ldat_tab, "Processing Settings"
        )
        proc_settings_frame.pack(padx=10, pady=5, fill="x")

        # Number of Split Files
        ctk.CTkLabel(proc_settings_frame, text="Number of Split Files:").grid(
            row=1, column=0, sticky="e", padx=5, pady=2
        )
        self.split_entry = ctk.CTkEntry(proc_settings_frame, width=100)
        self.split_entry.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        self.split_entry.insert(0, "1")

        # Warning label for max split files
        ctk.CTkLabel(
            proc_settings_frame,
            text=f"(Max: {MAX_SPLIT_FILES} = CPU cores - 2)",
            text_color="red",
            font=ctk.CTkFont(size=10),
        ).grid(row=1, column=2, sticky="w", padx=5, pady=2)

        # --- Conversion Buttons Frame ---
        conversion_frame = self.create_labeled_frame(
            self.rawf_to_ldat_tab, "Conversion Options"
        )
        conversion_frame.pack(padx=10, pady=5, fill="x")

        # Convert buttons
        self.convert_to_coincidence_button = ctk.CTkButton(
            conversion_frame,
            text="Convert Raw to Coincidence",
            command=self.convert_raw_to_coincidence,
        )
        self.convert_to_coincidence_button.grid(row=1, column=0, padx=20, pady=10)

        self.convert_to_group_button = ctk.CTkButton(
            conversion_frame,
            text="Convert Raw to Group",
            command=self.convert_raw_to_group,
        )
        self.convert_to_group_button.grid(row=1, column=1, padx=20, pady=10)

    def setup_ldat_proc_tab(self):
        # --- Energy cal file generation Section ---
        proc_frame = self.create_labeled_frame(
            self.ldat_proc_tab, "Energy cal file generation"
        )
        proc_frame.pack(padx=10, pady=5, fill="x")
        proc_frame.grid_columnconfigure(1, weight=1)

        # Label and entry for Basename LDAT File selection
        ctk.CTkLabel(proc_frame, text="Basename LDAT File:").grid(
            row=1, column=0, sticky="e", padx=5, pady=2
        )
        self.ldat_basename_entry = ctk.CTkEntry(proc_frame)
        self.ldat_basename_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        ctk.CTkButton(
            proc_frame, text="Browse", command=self.browse_ldat_basename, width=100
        ).grid(row=1, column=2, padx=5, pady=2)

        # Button to launch the energy cal generation python script
        self.process_ldat_button = ctk.CTkButton(
            proc_frame,
            text="Create Energy cal file",
            command=self.generate_energy_cal_file,
        )
        self.process_ldat_button.grid(row=2, column=0, columnspan=3, padx=20, pady=10)

    def setup_lm_generation_tab(self):
        # --- LM Generation Settings Frame ---
        lm_settings_frame = self.create_labeled_frame(
            self.lm_generation_tab, "LM File Generation Settings"
        )
        lm_settings_frame.pack(padx=10, pady=5, fill="x")
        lm_settings_frame.grid_columnconfigure(1, weight=1)

        # Input LDAT file (default is the acquisition file)
        ctk.CTkLabel(lm_settings_frame, text="Input LDAT File:").grid(
            row=1, column=0, sticky="e", padx=5, pady=2
        )
        self.lm_input_entry = ctk.CTkEntry(lm_settings_frame)
        self.lm_input_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        # Set default to acquisition file if empty
        if not self.lm_input_entry.get().strip():
            self.lm_input_entry.insert(0, "ldat_file_basename")
        ctk.CTkButton(
            lm_settings_frame, text="Browse", command=self.browse_lm_input, width=100
        ).grid(row=1, column=2, padx=5, pady=2)

        # LM Configuration file
        ctk.CTkLabel(lm_settings_frame, text="System Energy cal file:").grid(
            row=2, column=0, sticky="e", padx=5, pady=2
        )
        self.lm_encal_entry = ctk.CTkEntry(lm_settings_frame)
        self.lm_encal_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")
        ctk.CTkButton(
            lm_settings_frame, text="Browse", command=self.browse_lm_encal, width=100
        ).grid(row=2, column=2, padx=5, pady=2)

        # COG limits file
        ctk.CTkLabel(lm_settings_frame, text="COG Limits File:").grid(
            row=3, column=0, sticky="e", padx=5, pady=2
        )
        self.lm_cog_limits_entry = ctk.CTkEntry(lm_settings_frame)
        self.lm_cog_limits_entry.grid(row=3, column=1, padx=5, pady=2, sticky="ew")
        ctk.CTkButton(
            lm_settings_frame,
            text="Browse",
            command=self.browse_lm_cog_limits,
            width=100,
        ).grid(row=3, column=2, padx=5, pady=2)

        # Generate button
        generate_frame = ctk.CTkFrame(self.lm_generation_tab, fg_color="transparent")
        generate_frame.pack(padx=10, pady=10)

        self.generate_lm_button = ctk.CTkButton(
            generate_frame,
            text="Generate LM File",
            command=self.generate_lm_file,
        )
        self.generate_lm_button.pack(padx=5, pady=5)

    def add_logo(self):
        # Add the onco_logo.jpeg image at the bottom of the GUI.
        try:
            # Try multiple possible paths
            possible_paths = [
                "imgs/onco_logo.jpeg",
                "../imgs/onco_logo.jpeg",
                "/home/sie/sw/gui_cornell/imgs/onco_logo.jpeg",
            ]

            image_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    image_path = path
                    break

            if image_path is None:
                self.log_message("Logo file not found in any of the expected locations")
                return

            # Use CTkImage for better scaling
            image = Image.open(image_path)
            width, height = image.size
            new_width = 150
            new_height = int(height * new_width / width)

            # CTkImage requires size argument
            ctk_image = ctk.CTkImage(
                light_image=image, dark_image=image, size=(new_width, new_height)
            )

            # Create a frame specifically for the logo at the bottom
            logo_frame = ctk.CTkFrame(self.root, fg_color="transparent")
            logo_frame.pack(side=tk.BOTTOM, fill="x", pady=5)

            logo_label = ctk.CTkLabel(logo_frame, image=ctk_image, text="")
            logo_label.pack()  # Pack in center of the frame

        except Exception as e:
            self.log_message(f"Error loading onco_logo.jpeg: {e}")

    # All the browse methods for file selection
    def browse_lm_input(self):
        filename = filedialog.askopenfilename(
            title="Select LDAT Input File",
            filetypes=[("LDAT Files", "*.ldat"), ("All Files", "*.*")],
        )
        if filename:
            self.lm_input_entry.delete(0, tk.END)
            self.lm_input_entry.insert(0, filename)

    def browse_lm_encal(self):
        filename = filedialog.askopenfilename(
            title="Select Energy cal File",
            filetypes=[("Encal Files", "*.encal"), ("All Files", "*.*")],
        )
        if filename:
            self.lm_encal_entry.delete(0, tk.END)
            self.lm_encal_entry.insert(0, filename)

    def browse_lm_cog_limits(self):
        filename = filedialog.askopenfilename(
            title="Select COG Limits File",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if filename:
            self.lm_cog_limits_entry.delete(0, tk.END)
            self.lm_cog_limits_entry.insert(0, filename)

    def browse_rawf_file(self):
        filename = filedialog.askopenfilename(
            title="Select Rawf File",
            filetypes=[("Rawf Files", "*.rawf"), ("All Files", "*.*")],
            initialdir=self.output_data_folder,
        )
        if filename:
            self.proc_data_entry.delete(0, tk.END)
            self.proc_data_entry.insert(0, filename)

    def browse_petsys_folder(self):
        folder = filedialog.askdirectory(
            title="Select PETsys Folder", initialdir="/home/sie/sw/", mustexist=True
        )
        if folder:
            self.petsys_entry.delete(0, tk.END)
            self.petsys_entry.insert(0, folder)

    def browse_output_folder(self):
        folder = filedialog.askdirectory(
            title="Select Output Data Folder",
            initialdir="/home/sie/Cornell/data/",
            mustexist=True,
        )
        if folder:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, folder)

    def browse_ldat_basename(self):
        filename = filedialog.askopenfilename(
            title="Select Basename LDAT File",
            filetypes=[("LDAT Files", "*.ldat"), ("All Files", "*.*")],
            initialdir=self.output_data_folder,
        )
        if filename:
            self.ldat_basename_entry.delete(0, tk.END)
            self.ldat_basename_entry.insert(0, filename)

    def browse_process_petsys_folder(self):
        folder = filedialog.askdirectory(
            title="Select Process PETSYS Folder",
            initialdir="/home/sie/sw/",
            mustexist=True,
        )
        if folder:
            self.process_petsys_entry.delete(0, tk.END)
            self.process_petsys_entry.insert(0, folder)

    def browse_process_config_file(self):
        filename = filedialog.askopenfilename(
            title="Select Processing Config File",
            filetypes=[
                ("YAML Files", "*.yaml"),
                ("All Files", "*.*"),
            ],
            initialdir="/home/sie/sw/process_petsys/configs/",
        )
        if filename:
            self.process_config_entry.delete(0, tk.END)
            self.process_config_entry.insert(0, filename)

    def browse_config_file(self):
        filename = filedialog.askopenfilename(
            title="Select Config File",
            filetypes=[("INI Files", "*.ini"), ("All Files", "*.*")],
            initialdir="/home/sie/Cornell/",
        )
        if filename:
            self.config_entry.delete(0, tk.END)
            self.config_entry.insert(0, filename)

    # Remaining methods (existing functionality)
    def on_close(self):
        # Stop DAQD if running and clean files before exit.
        self.stop_daqd()
        clean_tmp_and_shm()
        self.root.destroy()

    def update_settings(self):
        self.petsys_folder = self.petsys_entry.get().strip()
        self.output_data_folder = self.output_entry.get().strip()
        self.config_file = self.config_entry.get().strip()
        self.acq_file_name = self.acq_file_entry.get().strip()
        if not self.acq_file_name:
            self.acq_file_name = "data_file"
            self.acq_file_entry.delete(0, tk.END)
            self.acq_file_entry.insert(0, "data_file")
            self.log_message("Empty acquisition file name. Using default 'data_file'.")
        try:
            self.acq_time = int(self.acq_entry.get().strip())
        except ValueError:
            self.acq_time = 10
            self.acq_entry.delete(0, tk.END)
            self.acq_entry.insert(0, "10")
            self.log_message("Invalid acquisition time entered. Reset to 10.")
        try:
            self.split_files = int(self.split_entry.get().strip())
            if self.split_files < 1:
                self.split_files = 1
                self.split_entry.delete(0, tk.END)
                self.split_entry.insert(0, "1")
                self.log_message(
                    "Number of split files must be at least 1. Reset to 1."
                )
            elif self.split_files > MAX_SPLIT_FILES:
                self.split_files = MAX_SPLIT_FILES
                self.split_entry.delete(0, tk.END)
                self.split_entry.insert(0, str(MAX_SPLIT_FILES))
                self.log_message(
                    f"Number of split files exceeds maximum ({MAX_SPLIT_FILES} = CPU cores - 2). Reset to {MAX_SPLIT_FILES}."
                )
        except ValueError:
            self.split_files = 1
            self.split_entry.delete(0, tk.END)
            self.split_entry.insert(0, "1")
            self.log_message("Invalid number of split files entered. Reset to 1.")

        if hasattr(self, "proc_data_entry"):
            curr = self.proc_data_entry.get().strip()
            if not curr:
                self.proc_data_entry.delete(0, tk.END)
                self.proc_data_entry.insert(0, self.acq_file_name)

        if hasattr(self, "lm_input_entry"):
            curr_lm = self.lm_input_entry.get().strip()
            if not curr_lm:
                self.lm_input_entry.delete(0, tk.END)
                self.lm_input_entry.insert(0, self.acq_file_name)

        # New settings for processing
        self.process_petsys_folder = self.process_petsys_entry.get().strip()
        self.process_config_file = self.process_config_entry.get().strip()

    def run_command(self, command_line, callback=None):
        self.log_message("Executing: " + command_line)

        def task():
            try:
                process = subprocess.Popen(
                    command_line,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    text=True,
                )
                output, error = process.communicate()
                full_output = output + "\n" + error
            except Exception as e:
                full_output = f"Error: {e}"
            self.root.after(
                0, lambda: self.output_text.insert(tk.END, full_output + "\n")
            )
            self.root.after(0, lambda: self.output_text.see(tk.END))
            if callback:
                self.root.after(0, callback)

        threading.Thread(target=task, daemon=True).start()

    def toggle_daqd(self):
        if self.daqd_state.get():
            # Toggle turned on: update text and launch DAQD window
            self.daqd_toggle.configure(text="DAQD ON")
            self.init_daqd_window()
        else:
            # Toggle turned off: update text and stop DAQD process and close window
            self.daqd_toggle.configure(text="DAQD OFF")
            self.stop_daqd()
            if hasattr(self, "daqd_window") and self.daqd_window.winfo_exists():
                self.daqd_window.destroy()

            # Reset initialization state and disable acquire button when DAQD is turned off
            self.system_initialized = False
            self.acquire_button.configure(state="disabled")
            self.pipeline_button.configure(state="disabled")

    def init_daqd_window(self):
        # Create DAQD window only if it doesn't already exist.
        if hasattr(self, "daqd_window") and self.daqd_window.winfo_exists():
            return
        self.daqd_window = ctk.CTkToplevel(self.root)
        self.daqd_window.title("DAQD Initialization")
        self.daqd_window.geometry("600x400")
        # Make sure that closing the window updates the toggle.
        self.daqd_window.protocol("WM_DELETE_WINDOW", self.close_daqd_window)
        self.daqd_output = ctk.CTkTextbox(self.daqd_window, width=580, height=380)
        self.daqd_output.pack(padx=10, pady=10, fill="both", expand=True)
        # Start DAQD in a background thread.
        threading.Thread(target=self.start_daqd, daemon=True).start()

    def close_daqd_window(self):
        # Called when the DAQD window is closed manually.
        self.daqd_state.set(False)
        self.daqd_toggle.configure(text="DAQD OFF")
        self.daqd_toggle.deselect()  # Ensure visual state matches
        self.stop_daqd()
        self.daqd_window.destroy()

    def start_daqd(self):
        self.petsys_folder = self.petsys_entry.get().strip()
        if not self.petsys_folder:
            self.log_daqd("PETsys Folder not set.")
            return

        # Prefix with stdbuf -oL for line buffering.
        command = f"stdbuf -oL {self.petsys_folder}/daqd --daq-type PFP_KX7"
        self.log_daqd("Starting DAQD with command: " + command)
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
                text=True,
                preexec_fn=os.setsid,  # so that we can kill the entire process group later
            )
            self.daqd_process = process
            # Read stdout line by line.
            for line in iter(process.stdout.readline, ""):
                if line:
                    self.log_daqd(line.rstrip())
                else:
                    break
            process.stdout.close()
            process.wait()
            self.log_daqd(
                "DAQD process ended with return code " + str(process.returncode)
            )
        except Exception as e:
            self.log_daqd(f"Error starting DAQD: {e}")
        finally:
            self.daqd_process = None
            # Reset the toggle if the process ended unexpectedly.
            self.root.after(0, lambda: self.daqd_state.set(False))
            self.root.after(0, lambda: self.daqd_toggle.configure(text="DAQD OFF"))
            self.root.after(0, lambda: self.daqd_toggle.deselect())

    def stop_daqd(self):
        if self.daqd_process and self.daqd_process.poll() is None:
            try:
                # Kill the entire process group.
                os.killpg(os.getpgid(self.daqd_process.pid), signal.SIGTERM)
                self.log_daqd("DAQD process terminated.")
            except Exception as e:
                self.log_daqd(f"Error terminating DAQD: {e}")
            self.daqd_process = None

    def log_daqd(self, message):
        def append():
            if hasattr(self, "daqd_output") and self.daqd_output.winfo_exists():
                self.daqd_output.insert(tk.END, message + "\n")
                self.daqd_output.see(tk.END)

        self.root.after(0, append)

    def acquire_data(self):
        self.update_settings()

        # Check if DAQD is running
        if not self.daqd_state.get():
            self.log_message(
                "ERROR: DAQD must be ON before acquiring data. Please toggle DAQD ON first."
            )
            return

        if not all([self.petsys_folder, self.output_data_folder, self.config_file]):
            self.log_message(
                "Please set PETsys Folder, Output Data Folder, and Config File."
            )
            return
        file_full_path = os.path.join(
            self.output_data_folder, self.acq_file_name + f"_{int(self.acq_time)}s"
        )

        # HW trigger flag
        hwtrg_flag = "--enable-hw-trigger" if self.hw_trigger.get() else ""

        command = (
            f"cd {self.petsys_folder} && "
            f"./acquire_sipm_data --config {self.config_file} -o {file_full_path} "
            f"--time {self.acq_time} --mode qdc {hwtrg_flag}"
        )
        self.run_command(command)

    def convert_raw_to_coincidence(self):
        self.update_settings()
        if not all([self.petsys_folder, self.output_data_folder, self.config_file]):
            self.log_message(
                "Please set PETsys Folder, Output Data Folder, and Config File."
            )
            return
        file_full_path = os.path.join(
            self.output_data_folder, self.proc_data_entry.get()
        )

        # Read the acquisition time from the proc_data_entry which has
        # the format of "rawf_file_basename_{acq_time}s"
        try:
            acq_time_str = file_full_path.split("_")[-1].replace("s", "")
            acq_time_str = int(acq_time_str) + SPLIT_TIME_OFFSET
        except ValueError:
            self.log_message(
                "Error: Unable to extract acquisition time from the file name."
            )
            return
        except IndexError:
            self.log_message(
                "Error: File name format is incorrect. Expected format: rawf_file_basename_{acq_time}s"
            )
            return

        # Calculate the split time if needed
        split_time_param = ""
        if self.split_files > 1:
            split_time = acq_time_str / self.split_files
            split_time_param = f"--splitTime {split_time} "

        command = (
            f"cd {self.petsys_folder} && "
            f"./convert_raw_to_coincidence --config {self.config_file} -i {file_full_path} "
            f"-o {file_full_path}_coincFixed --writeBinaryFixed --writeMultipleHits 16 {split_time_param}"
        )
        self.run_command(command)

    def convert_raw_to_group(self):
        self.update_settings()
        if not all([self.petsys_folder, self.output_data_folder, self.config_file]):
            self.log_message(
                "Please set PETsys Folder, Output Data Folder, and Config File."
            )
            return
        file_full_path = os.path.join(
            self.output_data_folder, self.proc_data_entry.get()
        )

        file_full_path = file_full_path.split(".")[0]

        # Read the acquisition time from the proc_data_entry which has
        # the format of "rawf_file_basename_{acq_time}s"
        try:
            acq_time_str = file_full_path.split("_")[-1].replace("s", "")
            acq_time_str = int(acq_time_str) + SPLIT_TIME_OFFSET
        except ValueError:
            self.log_message(
                f"Error: Unable to extract acquisition time from the file name. Current file name is {file_full_path}"
            )
            return
        except IndexError:
            self.log_message(
                "Error: File name format is incorrect. Expected format: rawf_file_basename_(acq_time)s"
            )
            return

        # Calculate the split time if needed
        split_time_param = ""
        if self.split_files > 1:
            split_time = acq_time_str / self.split_files
            split_time_param = f"--splitTime {split_time} "

        command = (
            f"cd {self.petsys_folder} && "
            f"./convert_raw_to_group --config {self.config_file} -i {file_full_path} "
            f"-o {file_full_path}_groupFixed --writeBinaryFixed --writeMultipleHits 16 {split_time_param}"
        )
        self.run_command(command)

    def generate_lm_file(self):
        self.update_settings()
        if not all([self.process_petsys_folder, self.process_config_file]):
            self.log_message("Please set 'process_petsys' Folder and YAML Config File.")
            return

        # Get settings
        input_file = self.lm_input_entry.get().strip()
        encal_file = self.lm_encal_entry.get().strip()
        cog_limits_file = self.lm_cog_limits_entry.get().strip()

        if not all([input_file, encal_file, cog_limits_file]):
            self.log_message("Please provide all required files for LM generation.")
            return

        # Build the command using conda run -n for cleaner conda activation
        command = (
            f"conda run -n process_petsys "
            f"python {self.process_petsys_folder}/scripts_cornell/cornell_listmode_cog_fixed.py "
            f"{self.process_config_file} {encal_file} {cog_limits_file} {input_file}"
        )

        self.log_message("Generating LM file...")
        self.run_command(
            command,
            callback=lambda: self.log_message("LM file generation completed."),
        )

    def generate_energy_cal_file(self):
        self.update_settings()
        if not all([self.process_petsys_folder, self.process_config_file]):
            self.log_message("Please set 'process_petsys' Folder and YAML Config File.")
            return
        basename_file = self.ldat_basename_entry.get().strip()
        if not basename_file:
            self.log_message("Please select a Basename LDAT file.")
            return
        # Get the folder and base name (remove extension and acquisition time part)
        basename_folder = os.path.dirname(basename_file)
        base_name = os.path.basename(basename_file).split(".")[0]
        base_name = "_".join(base_name.split("_")[0:-1])
        pattern = os.path.join(basename_folder, base_name + "*.ldat")
        ldat_files = glob.glob(pattern)

        if not ldat_files:
            self.log_message(f"No LDAT files found matching pattern '{pattern}'.")
            return

        for f in ldat_files:
            self.log_message(f"Found LDAT file: {f}")

        # Build the command using conda run -n for cleaner conda activation
        command = (
            f"conda run -n process_petsys "
            f"python {self.process_petsys_folder}/scripts_cornell/cornell_slab_en_cal.py "
            f"{self.process_config_file} {' '.join(ldat_files)}"
        )
        self.log_message("Generating Energy cal file...")
        self.run_command(
            command,
            callback=lambda: self.log_message("Energy cal file generation completed."),
        )

    def run_complete_pipeline(self):
        """Execute the complete automated pipeline:
        1. Acquire data (generates .rawf)
        2. Convert RAWF to LDAT (with MAX_SPLIT_FILES)
        3. Generate Energy Cal file (.encal)
        4. Generate LM file
        """
        self.update_settings()

        # Validate all required settings
        cog_limits_file = self.lm_cog_limits_entry.get().strip()

        if not all(
            [
                self.petsys_folder,
                self.output_data_folder,
                self.config_file,
                self.process_petsys_folder,
                self.process_config_file,
                cog_limits_file,
            ]
        ):
            self.log_message(
                "⚠️ ERROR: Please configure all required settings before running the pipeline!"
            )
            self.log_message(
                "   Required: PETsys Folder, Output Data Folder, Config File, "
                "process_petsys Folder, YAML Config File, and COG Limits File"
            )
            return

        if not self.daqd_state.get():
            self.log_message("⚠️ ERROR: DAQD must be ON to run the pipeline!")
            return

        if not self.system_initialized:
            self.log_message("⚠️ ERROR: System must be initialized to run the pipeline!")
            return

        # Disable the pipeline button during execution
        self.pipeline_button.configure(state="disabled")

        self.log_message("\n" + "=" * 80)
        self.log_message("🚀 STARTING COMPLETE AUTOMATED PIPELINE")
        self.log_message("=" * 80 + "\n")

        # Calculate file paths
        file_basename = self.acq_file_name + f"_{int(self.acq_time)}s"
        rawf_file = os.path.join(self.output_data_folder, file_basename + ".rawf")

        # Set split files to maximum for optimal processing
        self.split_files = MAX_SPLIT_FILES
        self.split_entry.delete(0, tk.END)
        self.split_entry.insert(0, str(MAX_SPLIT_FILES))

        # Update status
        self.pipeline_status_label.configure(
            text=f"⏳ Step 1/4: Acquiring data ({self.acq_time}s)...",
            text_color="orange",
        )

        # Step 1: Acquire data
        self.log_message(f"📡 STEP 1/4: Acquiring data for {self.acq_time} seconds...")
        self.acquire_data()

        # Schedule the next steps with delays to allow commands to complete
        # We'll use a polling approach to check if files exist
        def step2_convert_to_ldat():
            # Wait for rawf file to exist
            if not os.path.exists(rawf_file):
                self.log_message("⏳ Waiting for acquisition to complete...")
                self.root.after(2000, step2_convert_to_ldat)
                return

            self.log_message(f"\n✅ Acquisition completed! Found: {rawf_file}")
            self.log_message(
                f"🔄 STEP 2/4: Converting RAWF to LDAT (splitting into {MAX_SPLIT_FILES} files)..."
            )

            self.pipeline_status_label.configure(
                text=f"⏳ Step 2/4: Converting to LDAT ({MAX_SPLIT_FILES} splits)...",
                text_color="orange",
            )

            # Update the proc_data_entry to point to the acquired file
            self.proc_data_entry.delete(0, tk.END)
            self.proc_data_entry.insert(0, file_basename + ".rawf")

            # Convert to coincidence format
            self.convert_raw_to_coincidence()

            # Schedule next step
            self.root.after(5000, step3_generate_energy_cal)

        def step3_generate_energy_cal():
            # Look for the generated ldat files
            ldat_pattern = os.path.join(
                self.output_data_folder, file_basename + "_coincFixed*.ldat"
            )
            ldat_files = glob.glob(ldat_pattern)

            if not ldat_files:
                self.log_message("⏳ Waiting for LDAT conversion to complete...")
                self.root.after(3000, step3_generate_energy_cal)
                return

            self.log_message(
                f"\n✅ LDAT conversion completed! Found {len(ldat_files)} files"
            )
            self.log_message("📊 STEP 3/4: Generating Energy Calibration file...")

            self.pipeline_status_label.configure(
                text="⏳ Step 3/4: Generating energy calibration...",
                text_color="orange",
            )

            # Update the ldat_basename_entry to point to one of the ldat files
            self.ldat_basename_entry.delete(0, tk.END)
            self.ldat_basename_entry.insert(0, ldat_files[0])

            # Generate energy cal
            self.generate_energy_cal_file()

            # Schedule next step
            self.root.after(5000, step4_generate_lm)

        def step4_generate_lm():
            # Look for the generated encal file
            encal_pattern = os.path.join(self.output_data_folder, "*.encal")
            encal_files = glob.glob(encal_pattern)

            # Find the most recent encal file
            if not encal_files:
                self.log_message("⏳ Waiting for Energy Cal generation to complete...")
                self.root.after(3000, step4_generate_lm)
                return

            # Get the most recent encal file
            encal_file = max(encal_files, key=os.path.getmtime)

            # Find the first ldat file for LM generation
            ldat_pattern = os.path.join(
                self.output_data_folder, file_basename + "_coincFixed_00000000.ldat"
            )
            ldat_file = glob.glob(ldat_pattern)

            if not ldat_file:
                self.log_message("⚠️ ERROR: Could not find LDAT file for LM generation!")
                pipeline_complete(False)
                return

            self.log_message(f"\n✅ Energy Cal completed! Using: {encal_file}")
            self.log_message("📄 STEP 4/4: Generating Listmode file...")

            self.pipeline_status_label.configure(
                text="⏳ Step 4/4: Generating LM file...", text_color="orange"
            )

            # Update LM generation entries
            self.lm_input_entry.delete(0, tk.END)
            self.lm_input_entry.insert(0, ldat_file[0])

            self.lm_encal_entry.delete(0, tk.END)
            self.lm_encal_entry.insert(0, encal_file)

            # Generate LM file
            self.generate_lm_file()

            # Schedule completion check
            self.root.after(5000, lambda: pipeline_complete(True))

        def pipeline_complete(success):
            if success:
                self.log_message("\n" + "=" * 80)
                self.log_message("✅ COMPLETE PIPELINE FINISHED SUCCESSFULLY!")
                self.log_message("=" * 80 + "\n")
                self.pipeline_status_label.configure(
                    text="✅ Pipeline completed successfully!", text_color="green"
                )
            else:
                self.log_message("\n" + "=" * 80)
                self.log_message("❌ PIPELINE ENCOUNTERED AN ERROR")
                self.log_message("=" * 80 + "\n")
                self.pipeline_status_label.configure(
                    text="❌ Pipeline failed - check logs", text_color="red"
                )

            # Re-enable the pipeline button
            self.pipeline_button.configure(state="normal")

            # Clear status after 10 seconds
            self.root.after(
                10000, lambda: self.pipeline_status_label.configure(text="")
            )

        # Start the pipeline chain
        # Wait a bit for acquire to start, then begin monitoring
        self.root.after(int(self.acq_time * 1000) + 3000, step2_convert_to_ldat)

    def init_system(self):
        self.update_settings()

        # Check if DAQD is running - initialization requires DAQD
        if not self.daqd_state.get():
            self.log_message(
                "ERROR: DAQD must be ON before initializing system. Please toggle DAQD ON first."
            )
            return

        if not self.petsys_folder:
            self.log_message("Please set PETsys Folder first.")
            return

        command = f"cd {self.petsys_folder} && ./init_system"
        self.log_message("Initializing system...")

        def task():
            try:
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    text=True,
                )
                output, error = process.communicate()
                full_output = output + "\n" + error

                # Enable the acquire button and show initialization message
                self.root.after(0, self.after_init)

            except Exception as e:
                full_output = f"Error during initialization: {e}"

            self.root.after(
                0, lambda: self.output_text.insert(tk.END, full_output + "\n")
            )

        threading.Thread(target=task, daemon=True).start()

    def after_init(self):
        self.system_initialized = True
        self.acquire_button.configure(state="normal")
        self.pipeline_button.configure(state="normal")

        # Show recommendation message
        recommendation = "⚠️ RECOMMENDATION: Wait at least 5 minutes before acquiring data for system stabilization ⚠️"
        self.log_message("\n" + recommendation + "\n")

        # Highlight the message by changing its appearance
        # CTkTextbox does not support tag_configure in the same way as tk.Text easily for colors without internal access
        # But we can try using standard tkinter tags if CTkTextbox exposes the underlying widget or supports it.
        # CTkTextbox is a wrapper around tk.Text.
        # We can access the underlying text widget via self.output_text._textbox

        try:
            self.output_text._textbox.tag_configure(
                "warning", foreground="red", font=("Helvetica", 10, "bold")
            )

            # Find the position of the message and tag it
            start_pos = self.output_text._textbox.search(recommendation, "1.0", tk.END)
            if start_pos:
                line_end = start_pos + " lineend"
                self.output_text._textbox.tag_add("warning", start_pos, line_end)
        except Exception:
            pass  # If internal API changes, just ignore highlighting


if __name__ == "__main__":
    root = ctk.CTk()
    app = PETsysGUIApp(root)
    root.mainloop()
