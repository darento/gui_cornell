import glob
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import subprocess
import threading
import os
import signal
from PIL import Image, ImageTk


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
        root.title("MAGUI Cornell - PETsys Manager - LM file converter")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Initialize variables
        self.initialize_variables()

        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        # Create tabs
        self.setup_tab = ttk.Frame(self.notebook)
        self.rawf_to_ldat_tab = ttk.Frame(self.notebook)
        self.ldat_proc_tab = ttk.Frame(self.notebook)
        self.lm_generation_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.setup_tab, text="System Setup & Acquisition")
        self.notebook.add(self.rawf_to_ldat_tab, text="RAWF to LDAT Conversion")
        self.notebook.add(self.ldat_proc_tab, text="LDAT Processing")
        self.notebook.add(self.lm_generation_tab, text="LM File Generation")

        # Populate tabs
        self.setup_acquisition_tab()
        self.setup_rawf_to_ldat_tab()
        self.setup_ldat_proc_tab()
        self.setup_lm_generation_tab()

        # Common output text area (shared across tabs)
        self.output_frame = ttk.Frame(root)
        self.output_frame.pack(fill="both", expand=True, padx=10, pady=5)

        ttk.Label(self.output_frame, text="Output Log:").pack(anchor="w")
        self.output_text = scrolledtext.ScrolledText(
            self.output_frame, width=80, height=15
        )
        self.output_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Add the logo at the bottom
        self.add_logo()

    def log_message(self, message):
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.yview_moveto(1.0)  # force scroll to the bottom

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
        self.lm_calibration_file = ""
        self.lm_output_file = ""

    def setup_acquisition_tab(self):
        # --- Settings Frame ---
        settings_frame = ttk.LabelFrame(
            self.setup_tab, text="Settings", padding=(10, 5)
        )
        settings_frame.pack(padx=10, pady=5, fill="x")

        # PETsys Folder
        ttk.Label(settings_frame, text="PETsys Folder:").grid(
            row=0, column=0, sticky="e", padx=5, pady=2
        )
        self.petsys_entry = ttk.Entry(settings_frame, width=50)
        self.petsys_entry.grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(
            settings_frame, text="Browse", command=self.browse_petsys_folder
        ).grid(row=0, column=2, padx=5, pady=2)

        # Output Data Folder
        ttk.Label(settings_frame, text="Output Data Folder:").grid(
            row=1, column=0, sticky="e", padx=5, pady=2
        )
        self.output_entry = ttk.Entry(settings_frame, width=50)
        self.output_entry.grid(row=1, column=1, padx=5, pady=2)
        ttk.Button(
            settings_frame, text="Browse", command=self.browse_output_folder
        ).grid(row=1, column=2, padx=5, pady=2)

        # Config File
        ttk.Label(settings_frame, text="Config File:").grid(
            row=2, column=0, sticky="e", padx=5, pady=2
        )
        self.config_entry = ttk.Entry(settings_frame, width=50)
        self.config_entry.grid(row=2, column=1, padx=5, pady=2)
        ttk.Button(settings_frame, text="Choose", command=self.choose_config_file).grid(
            row=2, column=2, padx=5, pady=2
        )

        # Acquisition file name
        ttk.Label(settings_frame, text="Acquisition File Name:").grid(
            row=3, column=0, sticky="e", padx=5, pady=2
        )
        self.acq_file_entry = ttk.Entry(settings_frame, width=50)
        self.acq_file_entry.grid(row=3, column=1, padx=5, pady=2)
        self.acq_file_entry.insert(0, "data_file")

        # Acquisition Time
        ttk.Label(settings_frame, text="Acq. Time (s):").grid(
            row=4, column=0, sticky="e", padx=5, pady=2
        )
        self.acq_entry = ttk.Entry(settings_frame, width=10)
        self.acq_entry.grid(row=4, column=1, sticky="w", padx=5, pady=2)
        self.acq_entry.insert(0, "10")

        # --- Processing Settings for PETSYS Scripts ---
        proc_settings_frame2 = ttk.LabelFrame(
            settings_frame, text="Process LDAT files Settings", padding=(10, 5)
        )
        proc_settings_frame2.grid(
            row=5, column=0, columnspan=3, padx=5, pady=5, sticky="ew"
        )

        # Process PETSYS Folder
        ttk.Label(proc_settings_frame2, text="'process_petsys' sw Folder:").grid(
            row=0, column=0, sticky="e", padx=5, pady=2
        )
        self.process_petsys_entry = ttk.Entry(proc_settings_frame2, width=50)
        self.process_petsys_entry.grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(
            proc_settings_frame2,
            text="Browse",
            command=self.browse_process_petsys_folder,
        ).grid(row=0, column=2, padx=5, pady=2)

        # Processing Config File
        ttk.Label(proc_settings_frame2, text="YAML Config File:").grid(
            row=1, column=0, sticky="e", padx=5, pady=2
        )
        self.process_config_entry = ttk.Entry(proc_settings_frame2, width=50)
        self.process_config_entry.grid(row=1, column=1, padx=5, pady=2)
        ttk.Button(
            proc_settings_frame2, text="Choose", command=self.choose_process_config_file
        ).grid(row=1, column=2, padx=5, pady=2)

        # --- System Control Frame ---
        control_frame = ttk.LabelFrame(
            self.setup_tab, text="System Control", padding=(10, 5)
        )
        control_frame.pack(padx=10, pady=5, fill="x")

        # DAQD Toggle
        self.daqd_state = tk.BooleanVar(value=False)
        self.daqd_toggle = ttk.Checkbutton(
            control_frame,
            text="DAQD OFF",
            variable=self.daqd_state,
            command=self.toggle_daqd,
        )
        self.daqd_toggle.grid(row=0, column=0, padx=5, pady=5)

        # System Initialization
        self.init_system_button = ttk.Button(
            control_frame, text="Initialize System", command=self.init_system
        )
        self.init_system_button.grid(row=0, column=1, padx=5, pady=5)

        # --- Acquisition Frame ---
        acq_frame = ttk.LabelFrame(
            self.setup_tab, text="Data Acquisition", padding=(10, 5)
        )
        acq_frame.pack(padx=10, pady=5, fill="x")

        # Acquire button
        self.acquire_button = ttk.Button(
            acq_frame, text="Acquire Data", command=self.acquire_data
        )
        self.acquire_button.grid(row=0, column=1, padx=5, pady=5)
        self.acquire_button.config(state=tk.DISABLED)

        # Hardware Trigger flag (checkbutton)
        self.hw_trigger = tk.BooleanVar(value=False)
        self.hw_trigger_cb = ttk.Checkbutton(
            acq_frame, text="Enable Hardware Trigger", variable=self.hw_trigger
        )
        self.hw_trigger_cb.grid(row=0, column=0, padx=5, pady=5)

    def setup_rawf_to_ldat_tab(self):
        # --- Data File Selection for Processing ---
        proc_file_frame = ttk.LabelFrame(
            self.rawf_to_ldat_tab, text="Data File Selection", padding=(10, 5)
        )
        proc_file_frame.pack(padx=10, pady=5, fill="x")
        ttk.Label(proc_file_frame, text="Data File:").grid(
            row=0, column=0, sticky="e", padx=5, pady=2
        )
        self.proc_data_entry = ttk.Entry(proc_file_frame, width=50)
        self.proc_data_entry.grid(row=0, column=1, padx=5, pady=2)
        # Set default to acquisition file
        if not self.proc_data_entry.get().strip():
            self.proc_data_entry.insert(0, "rawf_file_basename")
        ttk.Button(proc_file_frame, text="Browse", command=self.browse_rawf_file).grid(
            row=0, column=2, padx=5, pady=2
        )

        # --- Processing Settings Frame ---
        proc_settings_frame = ttk.LabelFrame(
            self.rawf_to_ldat_tab, text="Processing Settings", padding=(10, 5)
        )
        proc_settings_frame.pack(padx=10, pady=5, fill="x")

        # Number of Split Files
        ttk.Label(proc_settings_frame, text="Number of Split Files:").grid(
            row=0, column=0, sticky="e", padx=5, pady=2
        )
        self.split_entry = ttk.Entry(proc_settings_frame, width=10)
        self.split_entry.grid(row=0, column=1, sticky="w", padx=5, pady=2)
        self.split_entry.insert(0, "1")

        # --- Conversion Buttons Frame ---
        conversion_frame = ttk.LabelFrame(
            self.rawf_to_ldat_tab, text="Conversion Options", padding=(10, 5)
        )
        conversion_frame.pack(padx=10, pady=5, fill="x")

        # Convert buttons
        self.convert_to_coincidence_button = ttk.Button(
            conversion_frame,
            text="Convert Raw to Coincidence",
            command=self.convert_raw_to_coincidence,
        )
        self.convert_to_coincidence_button.grid(row=0, column=0, padx=5, pady=5)

        self.convert_to_group_button = ttk.Button(
            conversion_frame,
            text="Convert Raw to Group",
            command=self.convert_raw_to_group,
        )
        self.convert_to_group_button.grid(row=0, column=1, padx=5, pady=5)

    def setup_ldat_proc_tab(self):
        # --- Energy cal file generation Section ---
        proc_frame = ttk.LabelFrame(
            self.ldat_proc_tab, text="Energy cal file generation", padding=(10, 5)
        )
        proc_frame.pack(padx=10, pady=5, fill="x")

        # Label and entry for Basename LDAT File selection
        ttk.Label(proc_frame, text="Basename LDAT File:").grid(
            row=0, column=0, sticky="e", padx=5, pady=2
        )
        self.ldat_basename_entry = ttk.Entry(proc_frame, width=50)
        self.ldat_basename_entry.grid(row=0, column=1, padx=5, pady=2)
        ttk.Button(proc_frame, text="Browse", command=self.browse_ldat_basename).grid(
            row=0, column=2, padx=5, pady=2
        )

        # Button to launch the energy cal generation python script
        self.process_ldat_button = ttk.Button(
            proc_frame,
            text="Create Energy cal file",
            command=self.generate_energy_cal_file,
        )
        self.process_ldat_button.grid(row=1, column=0, columnspan=3, padx=5, pady=5)

    def setup_lm_generation_tab(self):
        # --- LM Generation Settings Frame ---
        lm_settings_frame = ttk.LabelFrame(
            self.lm_generation_tab, text="LM File Generation Settings", padding=(10, 5)
        )
        lm_settings_frame.pack(padx=10, pady=5, fill="x")
        # Input LDAT file (default is the acquisition file)
        ttk.Label(lm_settings_frame, text="Input LDAT File:").grid(
            row=0, column=0, sticky="e", padx=5, pady=2
        )
        self.lm_input_entry = ttk.Entry(lm_settings_frame, width=50)
        self.lm_input_entry.grid(row=0, column=1, padx=5, pady=2)
        # Set default to acquisition file if empty
        if not self.lm_input_entry.get().strip():
            self.lm_input_entry.insert(0, "ldat_file_basename")
        ttk.Button(lm_settings_frame, text="Browse", command=self.browse_lm_input).grid(
            row=0, column=2, padx=5, pady=2
        )

        # LM Configuration file
        ttk.Label(lm_settings_frame, text="System Energy cal file:").grid(
            row=1, column=0, sticky="e", padx=5, pady=2
        )
        self.lm_encal_entry = ttk.Entry(lm_settings_frame, width=50)
        self.lm_encal_entry.grid(row=1, column=1, padx=5, pady=2)
        ttk.Button(lm_settings_frame, text="Browse", command=self.browse_lm_encal).grid(
            row=1, column=2, padx=5, pady=2
        )

        # Calibration file
        ttk.Label(lm_settings_frame, text="Calibration File:").grid(
            row=2, column=0, sticky="e", padx=5, pady=2
        )
        self.lm_calib_entry = ttk.Entry(lm_settings_frame, width=50)
        self.lm_calib_entry.grid(row=2, column=1, padx=5, pady=2)
        ttk.Button(lm_settings_frame, text="Browse", command=self.browse_lm_calib).grid(
            row=2, column=2, padx=5, pady=2
        )

        # Output LM file
        ttk.Label(lm_settings_frame, text="Output LM Folder:").grid(
            row=3, column=0, sticky="e", padx=5, pady=2
        )
        self.lm_output_entry = ttk.Entry(lm_settings_frame, width=50)
        self.lm_output_entry.grid(row=3, column=1, padx=5, pady=2)
        ttk.Button(
            lm_settings_frame, text="Set Output", command=self.browse_lm_output_folder
        ).grid(row=3, column=2, padx=5, pady=2)

        # Generate button
        generate_frame = ttk.Frame(self.lm_generation_tab)
        generate_frame.pack(padx=10, pady=10)

        self.generate_lm_button = ttk.Button(
            generate_frame,
            text="Generate LM File",
            command=self.generate_lm_file,
        )
        self.generate_lm_button.pack(padx=5, pady=5)

    def add_logo(self):
        # Add the onco_logo.jpeg image at the bottom of the GUI.
        try:
            image = Image.open("/home/sie/sw/gui_cornell/imgs/onco_logo.jpeg")
            width, height = image.size
            new_width = 200
            new_height = int(height * new_width / width)
            resized_image = image.resize((new_width, new_height), Image.LANCZOS)
            photo = ImageTk.PhotoImage(resized_image)
            logo_label = tk.Label(self.root, image=photo)
            # Keep a reference so the image is not garbage-collected.
            logo_label.image = photo
            logo_label.pack(side=tk.BOTTOM, pady=10)
        except Exception as e:
            print("Error loading onco_logo.jpeg:", e)

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

    def browse_rawf_file(self):
        filename = filedialog.askopenfilename(
            title="Select Rawf File",
            filetypes=[("Rawf Files", "*.rawf"), ("All Files", "*.*")],
        )
        if filename:
            self.proc_data_entry.delete(0, tk.END)
            self.proc_data_entry.insert(0, filename)

    def browse_lm_calib(self):
        filename = filedialog.askopenfilename(
            title="Select Calibration File",
            filetypes=[("Calibration Files", "*.cal *.json"), ("All Files", "*.*")],
        )
        if filename:
            self.lm_calib_entry.delete(0, tk.END)
            self.lm_calib_entry.insert(0, filename)

    def browse_lm_output_folder(self):
        folder = filedialog.askdirectory(title="Select Output LM Folder")
        if folder:
            self.lm_output_entry.delete(0, tk.END)
            self.lm_output_entry.insert(0, folder)

    def browse_petsys_folder(self):
        folder = filedialog.askdirectory(title="Select PETsys Folder")
        if folder:
            self.petsys_entry.delete(0, tk.END)
            self.petsys_entry.insert(0, folder)

    def browse_output_folder(self):
        folder = filedialog.askdirectory(title="Select Output Data Folder")
        if folder:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, folder)

    def browse_ldat_basename(self):
        filename = filedialog.askopenfilename(
            title="Select Basename LDAT File",
            filetypes=[("LDAT Files", "*.ldat"), ("All Files", "*.*")],
        )
        if filename:
            self.ldat_basename_entry.delete(0, tk.END)
            self.ldat_basename_entry.insert(0, filename)

    def browse_process_petsys_folder(self):
        folder = filedialog.askdirectory(title="Select Process PETSYS Folder")
        if folder:
            self.process_petsys_entry.delete(0, tk.END)
            self.process_petsys_entry.insert(0, folder)

    def choose_process_config_file(self):
        filename = filedialog.askopenfilename(
            title="Select Processing Config File",
            filetypes=[
                ("YAML Files", "*.yaml"),
                ("All Files", "*.*"),
            ],
        )
        if filename:
            self.process_config_entry.delete(0, tk.END)
            self.process_config_entry.insert(0, filename)

    # Remaining methods (existing functionality)
    def on_close(self):
        # Stop DAQD if running and clean files before exit.
        self.stop_daqd()
        clean_tmp_and_shm()
        self.root.destroy()

    def choose_config_file(self):
        filename = filedialog.askopenfilename(
            title="Select Config File",
            filetypes=[("INI Files", "*.ini"), ("All Files", "*.*")],
        )
        if filename:
            self.config_entry.delete(0, tk.END)
            self.config_entry.insert(0, filename)

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
            self.root.after(0, lambda: self.output_text.yview_moveto(1.0))
            if callback:
                self.root.after(0, callback)

        threading.Thread(target=task, daemon=True).start()

    def toggle_daqd(self):
        if self.daqd_state.get():
            # Toggle turned on: update text and launch DAQD window
            self.daqd_toggle.config(text="DAQD ON")
            self.init_daqd_window()
        else:
            # Toggle turned off: update text and stop DAQD process and close window
            self.daqd_toggle.config(text="DAQD OFF")
            self.stop_daqd()
            if hasattr(self, "daqd_window") and self.daqd_window.winfo_exists():
                self.daqd_window.destroy()

            # Reset initialization state and disable acquire button when DAQD is turned off
            self.system_initialized = False
            self.acquire_button.config(state=tk.DISABLED)

    def init_daqd_window(self):
        # Create DAQD window only if it doesn't already exist.
        if hasattr(self, "daqd_window") and self.daqd_window.winfo_exists():
            return
        self.daqd_window = tk.Toplevel(self.root)
        self.daqd_window.title("DAQD Initialization")
        self.daqd_window.geometry("500x300")
        # Make sure that closing the window updates the toggle.
        self.daqd_window.protocol("WM_DELETE_WINDOW", self.close_daqd_window)
        self.daqd_output = scrolledtext.ScrolledText(
            self.daqd_window, width=60, height=15
        )
        self.daqd_output.pack(padx=10, pady=10)
        # Start DAQD in a background thread.
        threading.Thread(target=self.start_daqd, daemon=True).start()

    def close_daqd_window(self):
        # Called when the DAQD window is closed manually.
        self.daqd_state.set(False)
        self.daqd_toggle.config(text="DAQD OFF")
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
            self.root.after(0, lambda: self.daqd_toggle.config(text="DAQD OFF"))

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
            acq_time_str = int(acq_time_str)
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
            f"-o {file_full_path}_coincCompact --writeBinaryCompact --writeMultipleHits 64 {split_time_param}"
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

        # Read the acquisition time from the proc_data_entry which has
        # the format of "rawf_file_basename_{acq_time}s"
        try:
            acq_time_str = file_full_path.split("_")[-1].replace("s", "")
            acq_time_str = int(acq_time_str)
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
            f"-o {file_full_path}_groupCompact --writeBinaryCompact --writeMultipleHits 64 {split_time_param}"
        )
        self.run_command(command)

    def generate_lm_file(self):
        # Get settings
        input_file = self.lm_input_entry.get().strip()
        encal_file = self.lm_encal_entry.get().strip()
        calib_file = self.lm_calib_entry.get().strip()
        output_file = self.lm_output_entry.get().strip()

        if not all([input_file, encal_file, calib_file, output_file]):
            self.log_message("Please provide all required files for LM generation.")
            return

        # Example command for LM file generation
        # Replace with your actual script/command
        command = (
            f"python /path/to/lm_converter.py "
            f"--input {input_file} "
            f"--config {encal_file} "
            f"--calibration {calib_file} "
            f"--output {output_file}"
        )

        self.log_message("Generating LM file...")
        self.run_command(command)

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

        # Build the command wrapped in a bash call to source conda and run the script.
        command = (
            "bash -c 'source /home/sie/miniconda3/etc/profile.d/conda.sh && "
            "conda activate process_petsys && "
            f"cd {self.process_petsys_folder} && "
            f"python scripts_cornell/cornell_slab_en_cal.py "
            f"{self.process_config_file} {' '.join(ldat_files)} && "
            "conda deactivate'"
        )
        self.log_message("Generating Energy cal file...")
        self.run_command(
            command,
            callback=lambda: self.log_message("Energy cal file generation completed."),
        )

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
        self.acquire_button.config(state=tk.NORMAL)

        # Show recommendation message
        recommendation = "⚠️ RECOMMENDATION: Wait at least 2 minutes before acquiring data for system stabilization ⚠️"
        self.log_message("\n" + recommendation + "\n")

        # Highlight the message by changing its appearance
        self.output_text.tag_configure(
            "warning", foreground="red", font=("Helvetica", 10, "bold")
        )

        # Find the position of the message and tag it
        start_pos = self.output_text.search(recommendation, "1.0", tk.END)
        if start_pos:
            line_end = start_pos + " lineend"
            self.output_text.tag_add("warning", start_pos, line_end)


if __name__ == "__main__":
    root = tk.Tk()
    app = PETsysGUIApp(root)
    root.mainloop()
