import os
from pathlib import Path
import signal
import subprocess
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional, Callable, List, Tuple

import customtkinter as ctk
from PIL import Image, ImageTk

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("dark-blue")
ctk.DrawEngine.preferred_drawing_method = "polygon_shapes"

SPLIT_TIME_OFFSET: float = 0.1
MAX_SPLIT_FILES: int = max(1, os.cpu_count() - 2)

# Pipeline configuration constants
PIPELINE_DATA_DIR: str = "/data/nvmDisk/Cornell/data/FullPipeline"
PIPELINE_ENCAL_DIR: str = "/home/sie/sw/process_petsys/encal_files"
PIPELINE_COG_LIMITS_FILE: str = "/home/sie/sw/process_petsys/cog_limits.txt"
PIPELINE_DOI_LIMITS_FILE: str = "/home/sie/sw/process_petsys/doi_limits.txt"


def clean_tmp_and_shm() -> None:
    """Remove temporary socket and shared memory files."""
    sock_path = Path("/tmp/d.sock")
    shm_path = Path("/dev/shm/daqd_shm")

    if sock_path.exists():
        try:
            sock_path.unlink()
        except OSError:
            subprocess.call(["rm", str(sock_path)])

    if shm_path.exists():
        try:
            shm_path.unlink()
        except OSError:
            subprocess.call(["rm", str(shm_path)])


class PETsysGUIApp:
    def __init__(self, root: ctk.CTk) -> None:
        clean_tmp_and_shm()

        self.root = root
        self.root.title("MAGUI Cornell - PETsys Manager - LM file converter")
        self.root.geometry("900x950")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.initialize_variables()
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Create the overall UI structure."""
        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=5)

        tabs = [
            ("System Setup & Acquisition", "setup_tab"),
            ("RAWF to LDAT Conversion", "rawf_to_ldat_tab"),
            ("LDAT Processing", "ldat_proc_tab"),
            ("LM File Generation", "lm_generation_tab"),
            ("System Quality Control", "qc_tab"),
        ]

        for label, attr in tabs:
            self.tabview.add(label)
            setattr(self, attr, self.tabview.tab(label))

        self.setup_acquisition_tab()
        self.setup_rawf_to_ldat_tab()
        self.setup_ldat_proc_tab()
        self.setup_lm_generation_tab()
        self.setup_qc_tab()

        # Output Log area at bottom
        self.output_frame = ctk.CTkFrame(self.root)
        self.output_frame.pack(fill="both", expand=True, padx=10, pady=5)

        ctk.CTkLabel(self.output_frame, text="Output Log:").pack(
            anchor="w", padx=5, pady=(5, 0)
        )
        self.output_text = ctk.CTkTextbox(self.output_frame, width=800, height=150)
        self.output_text.pack(fill="both", expand=True, padx=5, pady=5)

        self.add_logo()

    def log_message(self, message: str) -> None:
        """Log a message to the output text area."""
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END)

    def initialize_variables(self) -> None:
        """Initialize all instance variables."""
        self.petsys_folder: str = ""
        self.output_data_folder: str = ""
        self.acq_file_name: str = "data_file"
        self.acq_time: int = 10
        self.split_files: int = 1
        self.config_file: str = ""
        self.daqd_process: Optional[subprocess.Popen] = None
        self.system_initialized: bool = False

        self.process_petsys_folder: str = ""
        self.process_config_file: str = ""

        self.lm_doi_limits_file: str = ""
        self.current_process: Optional[subprocess.Popen] = None
        self.stop_requested: bool = False

        # QC tab variables
        self.qc_with_source: bool = True
        self.qc_enable_plots: bool = False
        self.qc_enable_slabs: bool = False
        self.qc_acquisition_running: bool = False

    def create_labeled_frame(self, parent: ctk.CTkFrame, title: str) -> ctk.CTkFrame:
        """Create a frame with a bold title label at the top."""
        frame = ctk.CTkFrame(parent)
        label = ctk.CTkLabel(
            frame, text=title, font=ctk.CTkFont(size=14, weight="bold")
        )
        label.grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(5, 0))
        return frame

    def setup_acquisition_tab(self) -> None:
        # --- Settings Frame ---
        self._setup_settings_frame(self.setup_tab)

        # --- Two-column layout: Left (Control) | Right (Pipeline) ---
        columns_container = ctk.CTkFrame(self.setup_tab, fg_color="transparent")
        columns_container.pack(padx=10, pady=5, fill="both", expand=True)
        columns_container.grid_columnconfigure(0, weight=1)
        columns_container.grid_columnconfigure(1, weight=1)

        # LEFT COLUMN
        left_column = ctk.CTkFrame(columns_container, fg_color="transparent")
        left_column.grid(row=0, column=0, padx=(0, 5), sticky="nsew")
        self._setup_left_column(left_column)

        # RIGHT COLUMN
        right_column = ctk.CTkFrame(columns_container, fg_color="transparent")
        right_column.grid(row=0, column=1, padx=(5, 0), sticky="nsew")
        self._setup_right_column(right_column)

    def _setup_settings_frame(self, parent: ctk.CTkFrame) -> None:
        settings_frame = self.create_labeled_frame(parent, "Settings")
        settings_frame.pack(padx=10, pady=5, fill="x")
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

        # Acquisition file name & Time
        ctk.CTkLabel(settings_frame, text="Acquisition File Name:").grid(
            row=4, column=0, sticky="e", padx=5, pady=2
        )
        self.acq_file_entry = ctk.CTkEntry(settings_frame)
        self.acq_file_entry.grid(row=4, column=1, padx=5, pady=2, sticky="ew")
        self.acq_file_entry.insert(0, "data_file")

        ctk.CTkLabel(settings_frame, text="Acq. Time (s):").grid(
            row=5, column=0, sticky="e", padx=5, pady=2
        )
        self.acq_entry = ctk.CTkEntry(settings_frame, width=100)
        self.acq_entry.grid(row=5, column=1, sticky="w", padx=5, pady=2)
        self.acq_entry.insert(0, "10")

        # Nested Process LDAT settings
        self._setup_process_ldat_settings(settings_frame)

    def _setup_process_ldat_settings(self, parent: ctk.CTkFrame) -> None:
        proc_frame = self.create_labeled_frame(parent, "Process LDAT files Settings")
        proc_frame.grid(row=6, column=0, columnspan=3, padx=5, pady=10, sticky="ew")
        proc_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(proc_frame, text="'process_petsys' sw Folder:").grid(
            row=1, column=0, sticky="e", padx=5, pady=2
        )
        self.process_petsys_entry = ctk.CTkEntry(proc_frame)
        self.process_petsys_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        ctk.CTkButton(
            proc_frame,
            text="Browse",
            command=self.browse_process_petsys_folder,
            width=100,
        ).grid(row=1, column=2, padx=5, pady=2)

        ctk.CTkLabel(proc_frame, text="YAML Config File:").grid(
            row=2, column=0, sticky="e", padx=5, pady=2
        )
        self.process_config_entry = ctk.CTkEntry(proc_frame)
        self.process_config_entry.grid(row=2, column=1, padx=5, pady=2, sticky="ew")
        ctk.CTkButton(
            proc_frame,
            text="Browse",
            command=self.browse_process_config_file,
            width=100,
        ).grid(row=2, column=2, padx=5, pady=2)

    def _setup_left_column(self, parent: ctk.CTkFrame) -> None:
        # System Control
        ctrl_frame = self.create_labeled_frame(parent, "System Control")
        ctrl_frame.pack(padx=10, pady=5, fill="x")

        self.daqd_state = tk.BooleanVar(value=False)
        self.daqd_toggle = ctk.CTkCheckBox(
            ctrl_frame,
            text="DAQD OFF",
            variable=self.daqd_state,
            command=self.toggle_daqd,
        )
        self.daqd_toggle.grid(row=1, column=0, padx=20, pady=10)

        self.init_system_button = ctk.CTkButton(
            ctrl_frame, text="Initialize System", command=self.init_system
        )
        self.init_system_button.grid(row=1, column=1, padx=20, pady=10)

        # Data Acquisition
        acq_frame = self.create_labeled_frame(parent, "Data Acquisition")
        acq_frame.pack(padx=10, pady=5, fill="x")

        self.hw_trigger = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            acq_frame, text="Enable Hardware Trigger", variable=self.hw_trigger
        ).grid(row=1, column=0, padx=20, pady=10)

        self.acquire_button = ctk.CTkButton(
            acq_frame, text="Acquire Data", command=self.acquire_data, state="disabled"
        )
        self.acquire_button.grid(row=1, column=1, padx=20, pady=10)

    def _setup_right_column(self, parent: ctk.CTkFrame) -> None:
        pipe_frame = self.create_labeled_frame(parent, "Complete Automated Pipeline")
        pipe_frame.pack(padx=10, pady=5, fill="both", expand=True)
        pipe_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            pipe_frame,
            text="Execute complete workflow:\nAcquire → Convert → Calibrate → Generate LM",
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, padx=20, pady=10)

        self.pipeline_button = ctk.CTkButton(
            pipe_frame,
            text="> RUN COMPLETE PIPELINE",
            command=self.run_complete_pipeline,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            fg_color="#2ecc71",
            hover_color="#27ae60",
            state="disabled",
        )
        self.pipeline_button.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.stop_button = ctk.CTkButton(
            pipe_frame,
            text="STOP",
            command=self.stop_action,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            state="disabled",
        )
        self.stop_button.grid(row=3, column=0, padx=20, pady=5, sticky="ew")

        self.pipeline_status_label = ctk.CTkLabel(
            pipe_frame, text="", font=ctk.CTkFont(size=11), text_color="orange"
        )
        self.pipeline_status_label.grid(
            row=4, column=0, padx=20, pady=(0, 10), sticky="ew"
        )

    def setup_rawf_to_ldat_tab(self) -> None:
        # Data Selection
        file_frame = self.create_labeled_frame(
            self.rawf_to_ldat_tab, "Data File Selection"
        )
        file_frame.pack(padx=10, pady=5, fill="x")
        file_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(file_frame, text="Data File:").grid(
            row=1, column=0, sticky="e", padx=5, pady=2
        )
        self.proc_data_entry = ctk.CTkEntry(file_frame)
        self.proc_data_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        if not self.proc_data_entry.get().strip():
            self.proc_data_entry.insert(0, "rawf_file_basename")
        ctk.CTkButton(
            file_frame, text="Browse", command=self.browse_rawf_file, width=100
        ).grid(row=1, column=2, padx=5, pady=2)

        # Settings
        settings_frame = self.create_labeled_frame(
            self.rawf_to_ldat_tab, "Processing Settings"
        )
        settings_frame.pack(padx=10, pady=5, fill="x")

        ctk.CTkLabel(settings_frame, text="Number of Split Files:").grid(
            row=1, column=0, sticky="e", padx=5, pady=2
        )
        self.split_entry = ctk.CTkEntry(settings_frame, width=100)
        self.split_entry.grid(row=1, column=1, sticky="w", padx=5, pady=2)
        self.split_entry.insert(0, "1")
        ctk.CTkLabel(
            settings_frame,
            text=f"(Max: {MAX_SPLIT_FILES})",
            text_color="red",
            font=ctk.CTkFont(size=10),
        ).grid(row=1, column=2, sticky="w", padx=5, pady=2)

        # Options
        options_frame = self.create_labeled_frame(
            self.rawf_to_ldat_tab, "Conversion Options"
        )
        options_frame.pack(padx=10, pady=5, fill="x")

        self.convert_to_coincidence_button = ctk.CTkButton(
            options_frame,
            text="Convert Raw to Coincidence",
            command=self.convert_raw_to_coincidence,
        )
        self.convert_to_coincidence_button.grid(row=1, column=0, padx=20, pady=10)

        self.convert_to_group_button = ctk.CTkButton(
            options_frame,
            text="Convert Raw to Group",
            command=self.convert_raw_to_group,
        )
        self.convert_to_group_button.grid(row=1, column=1, padx=20, pady=10)

    def setup_ldat_proc_tab(self) -> None:
        frame = self.create_labeled_frame(
            self.ldat_proc_tab, "Energy cal file generation"
        )
        frame.pack(padx=10, pady=5, fill="x")
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Basename LDAT File:").grid(
            row=1, column=0, sticky="e", padx=5, pady=2
        )
        self.ldat_basename_entry = ctk.CTkEntry(frame)
        self.ldat_basename_entry.grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        ctk.CTkButton(
            frame, text="Browse", command=self.browse_ldat_basename, width=100
        ).grid(row=1, column=2, padx=5, pady=2)

        self.process_ldat_button = ctk.CTkButton(
            frame, text="Create Energy cal file", command=self.generate_energy_cal_file
        )
        self.process_ldat_button.grid(row=2, column=0, columnspan=3, padx=20, pady=10)

    def setup_qc_tab(self) -> None:
        """Setup the System Quality Control tab."""
        # Acquisition Settings Frame
        acq_settings_frame = self.create_labeled_frame(
            self.qc_tab, "Acquisition Settings"
        )
        acq_settings_frame.pack(padx=10, pady=5, fill="x")
        acq_settings_frame.grid_columnconfigure(1, weight=1)

        # Source selection
        ctk.CTkLabel(acq_settings_frame, text="Acquisition Mode:").grid(
            row=1, column=0, sticky="e", padx=5, pady=5
        )

        source_frame = ctk.CTkFrame(acq_settings_frame, fg_color="transparent")
        source_frame.grid(row=1, column=1, sticky="w", padx=5, pady=5)

        self.qc_source_var = tk.StringVar(value="with")
        self.qc_with_radio = ctk.CTkRadioButton(
            source_frame,
            text="With Source (1 min)",
            variable=self.qc_source_var,
            value="with",
        )
        self.qc_with_radio.pack(side="left", padx=5)

        self.qc_without_radio = ctk.CTkRadioButton(
            source_frame,
            text="Without Source (3 min)",
            variable=self.qc_source_var,
            value="without",
        )
        self.qc_without_radio.pack(side="left", padx=5)

        # Validation Options Frame
        validation_frame = self.create_labeled_frame(self.qc_tab, "Validation Options")
        validation_frame.pack(padx=10, pady=5, fill="x")
        validation_frame.grid_columnconfigure(1, weight=1)

        # Enable plots checkbox
        self.qc_plots_var = tk.BooleanVar(value=False)
        self.qc_plots_check = ctk.CTkCheckBox(
            validation_frame,
            text="Generate Plots ( no slab analysis, takes ~5 min )",
            variable=self.qc_plots_var,
            command=self.on_qc_plots_toggle,
        )
        self.qc_plots_check.grid(row=1, column=0, sticky="w", padx=20, pady=5)

        # Enable slabs checkbox (dependent on plots)
        self.qc_slabs_var = tk.BooleanVar(value=False)
        self.qc_slabs_check = ctk.CTkCheckBox(
            validation_frame,
            text="Enable Slab Analysis (requires plots, takes ~30 min)",
            variable=self.qc_slabs_var,
            state="disabled",
        )
        self.qc_slabs_check.grid(row=2, column=0, sticky="w", padx=40, pady=5)

        # Control Buttons Frame
        control_frame = self.create_labeled_frame(
            self.qc_tab, "Quality Control Execution"
        )
        control_frame.pack(padx=10, pady=10, fill="x")
        control_frame.grid_columnconfigure(0, weight=1)

        self.qc_run_button = ctk.CTkButton(
            control_frame,
            text="Run Quality Control",
            command=self.run_quality_control,
            width=200,
            height=40,
            fg_color="#2ecc71",
            hover_color="#27ae60",
            state="disabled",
        )
        self.qc_run_button.grid(row=1, column=0, pady=5)

        self.qc_stop_button = ctk.CTkButton(
            control_frame,
            text="STOP",
            command=self.stop_quality_control,
            width=200,
            height=40,
            fg_color="#e74c3c",
            hover_color="#c0392b",
            state="disabled",
        )
        self.qc_stop_button.grid(row=2, column=0, pady=5)

        # Status Frame
        status_frame = self.create_labeled_frame(self.qc_tab, "Status")
        status_frame.pack(padx=10, pady=5, fill="both", expand=True)
        status_frame.grid_columnconfigure(0, weight=1)

        self.qc_status_label = ctk.CTkLabel(
            status_frame, text="Ready to run quality control", font=ctk.CTkFont(size=12)
        )
        self.qc_status_label.grid(row=1, column=0, pady=10)

    def on_qc_plots_toggle(self) -> None:
        """Enable/disable slab checkbox based on plots checkbox."""
        if self.qc_plots_var.get():
            self.qc_slabs_check.configure(state="normal")
        else:
            self.qc_slabs_check.configure(state="disabled")
            self.qc_slabs_var.set(False)

    def run_quality_control(self) -> None:
        """Execute the quality control workflow."""
        # Validate required fields
        if not all(
            [
                self.petsys_folder,
                self.output_data_folder,
                self.config_file,
                self.process_petsys_folder,
                self.process_config_file,
            ]
        ):
            self.log_message(
                "ERROR: Please configure all required fields in 'System Setup & Acquisition' tab first."
            )
            messagebox.showerror(
                "Configuration Error",
                "Please fill in all required fields:\n"
                "- PETsys Folder\n"
                "- Output Data Folder\n"
                "- Config File\n"
                "- process_petsys Folder\n"
                "- YAML Config File",
            )
            return

        if not self.system_initialized:
            self.log_message(
                "ERROR: System not initialized. Please initialize the system first."
            )
            messagebox.showerror(
                "Initialization Error",
                "Please initialize the system in 'System Setup & Acquisition' tab first.",
            )
            return

        # Disable run button, enable stop button
        self.qc_run_button.configure(state="disabled")
        self.qc_stop_button.configure(state="normal")
        self.qc_acquisition_running = True

        # Determine acquisition time based on source selection
        acq_time = 60 if self.qc_source_var.get() == "with" else 180
        source_text = (
            "with source" if self.qc_source_var.get() == "with" else "without source"
        )

        self.log_message(f"\n{'='*60}")
        self.log_message(f"Starting Quality Control - {source_text} ({acq_time}s)")
        self.log_message(f"{'='*60}\n")

        self.qc_status_label.configure(text=f"Acquiring data ({acq_time}s)...")

        # Start acquisition in background thread
        def qc_acquisition_task():
            try:
                # Acquire data
                qc_filename = f"qc_{self.qc_source_var.get()}_source_{int(time.time())}"
                acquire_cmd = self._build_acquire_command(
                    Path(self.output_data_folder) / qc_filename,
                    acq_time,
                    config_flag="--config",
                    mode="qdc",
                    enable_hw_trigger=True,
                )

                self.log_message(f"Executing acquisition: {acquire_cmd}")

                process = subprocess.Popen(
                    acquire_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    shell=True,
                    text=True,
                    preexec_fn=os.setsid if os.name != "nt" else None,
                )
                self.current_process = process

                # Stream output
                for line in iter(process.stdout.readline, ""):
                    if line:
                        self.root.after(
                            0, lambda m=line.rstrip(): self.log_message(f"  {m}")
                        )
                    if not self.qc_acquisition_running:
                        break

                process.wait()

                if not self.qc_acquisition_running:
                    self.root.after(
                        0, lambda: self.log_message("Quality control stopped by user.")
                    )
                    return

                if process.returncode != 0:
                    self.root.after(
                        0,
                        lambda: self.log_message(
                            f"ERROR: Acquisition failed with return code {process.returncode}"
                        ),
                    )
                    return

                self.root.after(
                    0, lambda: self.log_message("Acquisition completed successfully.")
                )
                self.root.after(
                    0,
                    lambda: self.qc_status_label.configure(
                        text="Converting RAW to LDAT..."
                    ),
                )

                # Convert RAW to LDAT (same as RAWF to LDAT tab)
                raw_base_path = Path(self.output_data_folder) / qc_filename
                split_time_param = ""
                if self.split_files > 1:
                    split_time = acq_time / self.split_files + SPLIT_TIME_OFFSET
                    split_time_param = f"--splitTime {split_time} "

                convert_cmd = (
                    f"cd {self.petsys_folder} && "
                    f"./convert_raw_to_coincidence_fixed --config {self.config_file} "
                    f"-i {raw_base_path} -o {raw_base_path}_coincCompact "
                    f"--writeBinaryCompact --writeMultipleHits 16 {split_time_param}"
                )

                self.log_message(f"Executing conversion: {convert_cmd}")

                convert_process = subprocess.Popen(
                    convert_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    shell=True,
                    text=True,
                    preexec_fn=os.setsid if os.name != "nt" else None,
                )
                self.current_process = convert_process

                for line in iter(convert_process.stdout.readline, ""):
                    if line:
                        self.root.after(
                            0, lambda m=line.rstrip(): self.log_message(f"  {m}")
                        )
                    if not self.qc_acquisition_running:
                        break

                convert_process.wait()

                if not self.qc_acquisition_running:
                    return

                if convert_process.returncode != 0:
                    self.root.after(
                        0,
                        lambda: self.log_message(
                            f"ERROR: Conversion failed with return code {convert_process.returncode}"
                        ),
                    )
                    return

                self.cleanup_conversion_files(
                    self.output_data_folder, f"{raw_base_path}_coincCompact"
                )

                self.root.after(
                    0,
                    lambda: self.qc_status_label.configure(
                        text="Running validation..."
                    ),
                )

                # Run validation using converted LDATs
                self.root.after(
                    0, lambda: self.run_system_validation(f"{qc_filename}_coincCompact")
                )

            except Exception as e:
                self.root.after(
                    0, lambda: self.log_message(f"ERROR during acquisition: {e}")
                )
            finally:
                self.current_process = None

        threading.Thread(target=qc_acquisition_task, daemon=True).start()

    def run_system_validation(self, ldat_basename: str) -> None:
        """Run the cornell_system_validation.py script."""
        try:
            # Build command
            plots_flag = "--plots" if self.qc_plots_var.get() else ""
            slabs_flag = (
                "--slabs" if self.qc_slabs_var.get() and self.qc_plots_var.get() else ""
            )

            ldat_files = f"{self.output_data_folder}/{ldat_basename}*.ldat"

            validation_cmd = (
                f"cd {self.process_petsys_folder} && "
                f"conda run -n process_petsys "
                f"python scripts_cornell/cornell_system_validation.py "
                f"{self.process_config_file} "
                f"{ldat_files} "
                f"{plots_flag} {slabs_flag}"
            )

            self.log_message(f"\nExecuting validation: {validation_cmd}\n")

            def validation_task():
                try:
                    process = subprocess.Popen(
                        validation_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        shell=True,
                        text=True,
                        preexec_fn=os.setsid if os.name != "nt" else None,
                    )
                    self.current_process = process

                    # Stream output
                    for line in iter(process.stdout.readline, ""):
                        if line:
                            self.root.after(
                                0, lambda m=line.rstrip(): self.log_message(f"  {m}")
                            )
                        if not self.qc_acquisition_running:
                            break

                    process.wait()

                    if not self.qc_acquisition_running:
                        return

                    if process.returncode == 0:
                        self.root.after(
                            0,
                            lambda: self.log_message(
                                "\nQuality control completed successfully!"
                            ),
                        )
                        self.root.after(
                            0,
                            lambda: self.qc_status_label.configure(
                                text="Quality control completed successfully!"
                            ),
                        )
                        # Find and log the output directory
                        self.root.after(
                            0,
                            lambda: self.log_message(
                                f"Results saved in: {self.process_petsys_folder}/system_verifications/"
                            ),
                        )
                    else:
                        self.root.after(
                            0,
                            lambda: self.log_message(
                                f"ERROR: Validation failed with return code {process.returncode}"
                            ),
                        )
                        self.root.after(
                            0,
                            lambda: self.qc_status_label.configure(
                                text="Quality control failed. Check logs."
                            ),
                        )

                except Exception as e:
                    self.root.after(
                        0, lambda: self.log_message(f"ERROR during validation: {e}")
                    )
                finally:
                    self.current_process = None
                    self.root.after(
                        0, lambda: self.qc_run_button.configure(state="normal")
                    )
                    self.root.after(
                        0, lambda: self.qc_stop_button.configure(state="disabled")
                    )
                    self.qc_acquisition_running = False

            threading.Thread(target=validation_task, daemon=True).start()

        except Exception as e:
            self.log_message(f"ERROR setting up validation: {e}")
            self.qc_run_button.configure(state="normal")
            self.qc_stop_button.configure(state="disabled")
            self.qc_acquisition_running = False

    def stop_quality_control(self) -> None:
        """Stop the currently running quality control process."""
        self.qc_acquisition_running = False

        if self.current_process:
            try:
                if os.name != "nt":
                    os.killpg(os.getpgid(self.current_process.pid), signal.SIGTERM)
                else:
                    self.current_process.terminate()
                self.log_message("Quality control process terminated.")
            except Exception as e:
                self.log_message(f"Error stopping process: {e}")

        self.qc_run_button.configure(state="normal")
        self.qc_stop_button.configure(state="disabled")
        self.qc_status_label.configure(text="Quality control stopped.")
        self.current_process = None

    def setup_lm_generation_tab(self) -> None:
        lm_settings_frame = self.create_labeled_frame(
            self.lm_generation_tab, "LM File Generation Settings"
        )
        lm_settings_frame.pack(padx=10, pady=5, fill="x")
        lm_settings_frame.grid_columnconfigure(1, weight=1)

        # File selections
        fields = [
            (
                "Input LDAT File:",
                "lm_input_entry",
                self.browse_lm_input,
                "ldat_file_basename",
            ),
            ("System Energy cal file:", "lm_encal_entry", self.browse_lm_encal, ""),
            ("COG Limits File:", "lm_cog_limits_entry", self.browse_lm_cog_limits, ""),
            ("DOI Limits File:", "lm_doi_limits_entry", self.browse_lm_doi_limits, ""),
        ]

        for i, (label, attr, cmd, default) in enumerate(fields, 1):
            ctk.CTkLabel(lm_settings_frame, text=label).grid(
                row=i, column=0, sticky="e", padx=5, pady=2
            )
            entry = ctk.CTkEntry(lm_settings_frame)
            entry.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
            if default:
                entry.insert(0, default)
            setattr(self, attr, entry)
            ctk.CTkButton(
                lm_settings_frame, text="Browse", command=cmd, width=100
            ).grid(row=i, column=2, padx=5, pady=2)

        # Generate button
        gen_btn_frame = ctk.CTkFrame(self.lm_generation_tab, fg_color="transparent")
        gen_btn_frame.pack(padx=10, pady=10)
        self.generate_lm_button = ctk.CTkButton(
            gen_btn_frame, text="Generate LM File", command=self.generate_lm_file
        )
        self.generate_lm_button.pack(padx=5, pady=5)

    def add_logo(self) -> None:
        """Add the Onco Vision logo at the bottom of the GUI."""
        try:
            # Try multiple possible paths
            possible_paths = [
                "imgs/onco_logo.jpeg",
                "../imgs/onco_logo.jpeg",
                "/home/sie/sw/gui_cornell/imgs/onco_logo.jpeg",
            ]

            image_path = None
            for path in possible_paths:
                p = Path(path)
                if p.exists():
                    image_path = p
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

    def _browse(
        self,
        entry: ctk.CTkEntry,
        title: str,
        mode: str = "file",
        initialdir: Optional[str] = None,
        filetypes: Optional[List[Tuple[str, str]]] = None,
    ) -> None:
        """Generic helper for file/directory browsing."""
        if filetypes is None:
            filetypes = [("All Files", "*.*")]

        if mode == "file":
            filename = filedialog.askopenfilename(
                title=title, filetypes=filetypes, initialdir=initialdir
            )
        else:
            filename = filedialog.askdirectory(
                title=title, initialdir=initialdir, mustexist=True
            )

        if filename:
            entry.delete(0, tk.END)
            entry.insert(0, filename)

    # All the browse methods for file selection
    def browse_lm_input(self) -> None:
        self._browse(
            self.lm_input_entry,
            "Select LDAT Input File",
            initialdir="/data/nvmDisk/Cornell/data/",
            filetypes=[("LDAT Files", "*.ldat"), ("All Files", "*.*")],
        )

    def browse_lm_encal(self) -> None:
        self._browse(
            self.lm_encal_entry,
            "Select Energy cal File",
            initialdir="/home/sie/sw/process_petsys/encal_files/",
            filetypes=[("Encal Files", "*.encal"), ("All Files", "*.*")],
        )

    def browse_lm_cog_limits(self) -> None:
        self._browse(
            self.lm_cog_limits_entry,
            "Select COG Limits File",
            initialdir="/home/sie/sw/process_petsys/",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )

    def browse_lm_doi_limits(self) -> None:
        self._browse(
            self.lm_doi_limits_entry,
            "Select DOI Limits File",
            initialdir="/home/sie/sw/process_petsys/",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )

    def browse_rawf_file(self) -> None:
        self._browse(
            self.proc_data_entry,
            "Select Rawf File",
            initialdir=self.output_data_folder,
            filetypes=[("Rawf Files", "*.rawf"), ("All Files", "*.*")],
        )

    def browse_petsys_folder(self) -> None:
        self._browse(
            self.petsys_entry,
            "Select PETsys Folder",
            mode="directory",
            initialdir="/home/sie/sw/",
        )

    def browse_output_folder(self) -> None:
        self._browse(
            self.output_entry,
            "Select Output Data Folder",
            mode="directory",
            initialdir="/data/nvmDisk/Cornell/",
        )

    def browse_ldat_basename(self) -> None:
        self._browse(
            self.ldat_basename_entry,
            "Select Basename LDAT File",
            initialdir=self.output_data_folder,
            filetypes=[("LDAT Files", "*.ldat"), ("All Files", "*.*")],
        )

    def browse_process_petsys_folder(self) -> None:
        self._browse(
            self.process_petsys_entry,
            "Select Process PETSYS Folder",
            mode="directory",
            initialdir="/home/sie/sw/",
        )

    def browse_process_config_file(self) -> None:
        self._browse(
            self.process_config_entry,
            "Select Processing Config File",
            initialdir="/home/sie/sw/process_petsys/configs/",
            filetypes=[("YAML Files", "*.yaml"), ("All Files", "*.*")],
        )

    def browse_config_file(self) -> None:
        self._browse(
            self.config_entry,
            "Select Config File",
            initialdir="/data/nvmDisk/Cornell/",
            filetypes=[("INI Files", "*.ini"), ("All Files", "*.*")],
        )

    # Remaining methods (existing functionality)
    def on_close(self) -> None:
        """Cleanup on application exit."""
        self.stop_daqd()
        clean_tmp_and_shm()
        self.root.destroy()

    def update_settings(self) -> None:
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

    def run_command(
        self, command_line: str, callback: Optional[Callable] = None
    ) -> None:
        """Execute a shell command in a background thread and log the output."""
        self.log_message(f"Executing: {command_line}")
        self.stop_button.configure(state="normal")
        self.stop_requested = False

        def task():
            try:
                process = subprocess.Popen(
                    command_line,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # Combine stdout and stderr
                    shell=True,
                    text=True,
                    preexec_fn=os.setsid if os.name != "nt" else None,
                )
                self.current_process = process

                # Stream output line by line for real-time feedback
                for line in iter(process.stdout.readline, ""):
                    if line:
                        self.root.after(
                            0, lambda m=line.rstrip(): self.log_message(f"  {m}")
                        )

                process.wait()
                return_code = process.returncode
                self.log_message(f"Command finished with return code {return_code}")

            except Exception as e:
                self.log_message(f"Execution Error: {e}")
            finally:
                self.current_process = None
                self.root.after(0, lambda: self.stop_button.configure(state="disabled"))
                if callback:
                    self.root.after(0, callback)

        threading.Thread(target=task, daemon=True).start()

    def toggle_daqd(self) -> None:
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

    def init_daqd_window(self) -> None:
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

    def close_daqd_window(self) -> None:
        """Handle manual DAQD window close."""
        self.daqd_state.set(False)
        self.daqd_toggle.configure(text="DAQD OFF")
        self.daqd_toggle.deselect()  # Ensure visual state matches
        self.stop_daqd()
        self.daqd_window.destroy()

    def start_daqd(self) -> None:
        self.petsys_folder = self.petsys_entry.get().strip()
        if not self.petsys_folder:
            self.log_daqd("PETsys Folder not set.")
            return

        # Prefix with stdbuf -oL for line buffering.
        command = f"stdbuf -oL {self.petsys_folder}/daqd --socket-name /tmp/d.sock --daq-type PFP_KX7 --card /dev/psdaq0 --card /dev/psdaq1"
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

    def stop_daqd(self) -> None:
        if self.daqd_process and self.daqd_process.poll() is None:
            try:
                # Kill the entire process group.
                if os.name != "nt":
                    os.killpg(os.getpgid(self.daqd_process.pid), signal.SIGTERM)
                else:
                    self.daqd_process.terminate()
                self.log_daqd("DAQD process terminated.")
            except Exception as e:
                self.log_daqd(f"Error terminating DAQD: {e}")
            self.daqd_process = None

    def stop_action(self) -> None:
        """Interrupt the current process and signal the pipeline to stop."""
        self.stop_requested = True
        self.log_message("[STOP] Stop requested by user.")

        if self.current_process and self.current_process.poll() is None:
            try:
                if os.name != "nt":
                    os.killpg(os.getpgid(self.current_process.pid), signal.SIGTERM)
                else:
                    self.current_process.terminate()
                self.log_message("[STOP] Current process interrupted.")
            except Exception as e:
                self.log_message(f"[STOP] Error interrupting process: {e}")

        self.pipeline_status_label.configure(
            text="[STOP] Extraction/Processing stopped by user.", text_color="red"
        )
        # Re-enable pipeline and other buttons if necessary
        self.pipeline_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.acquire_button.configure(state="normal")

    def log_daqd(self, message: str) -> None:
        def append():
            if hasattr(self, "daqd_output") and self.daqd_output.winfo_exists():
                self.daqd_output.insert(tk.END, message + "\n")
                self.daqd_output.see(tk.END)

        self.root.after(0, append)

    def cleanup_conversion_files(self, output_folder: str, base_file_path: str) -> None:
        """
        Clean up unwanted files generated during RAWF to LDAT conversion.
        Deletes .lidx files and empty 0000.ldat file.

        Args:
            output_folder: The folder containing the converted files
            base_file_path: The base path of the converted files (without extension)
        """
        try:
            folder = Path(output_folder)
            base_name = Path(base_file_path).name

            # Delete .lidx files matching the pattern
            for lidx_file in folder.glob(f"{base_name}*.lidx"):
                try:
                    lidx_file.unlink()
                    self.log_message(f"Deleted: {lidx_file}")
                except Exception as e:
                    self.log_message(f"Warning: Could not delete {lidx_file}: {e}")

            # Delete the empty 0000.ldat file if it exists
            ldat_0000_files = list(folder.glob(f"{base_name}*00000.ldat"))
            if ldat_0000_files:
                for ldat_0000 in ldat_0000_files:
                    try:
                        ldat_0000.unlink()
                        self.log_message(f"Deleted empty LDAT file: {ldat_0000}")
                    except Exception as e:
                        self.log_message(f"Warning: Could not delete {ldat_0000}: {e}")
            else:
                self.log_message("Note: Empty LDAT file not found")

        except Exception as e:
            self.log_message(f"Error during cleanup: {e}")

    def _build_acquire_command(
        self,
        output_path: Path,
        acq_time: int,
        *,
        config_flag: str = "--config",
        mode: Optional[str] = "qdc",
        enable_hw_trigger: bool = True,
    ) -> str:
        hwtrg_flag = (
            "--enable-hw-trigger" if enable_hw_trigger and self.hw_trigger.get() else ""
        )
        mode_flag = f"--mode {mode}" if mode else ""
        return (
            f"cd {self.petsys_folder} && "
            f"./acquire_sipm_data {config_flag} {self.config_file} "
            f"-o {output_path} --time {acq_time} {mode_flag} {hwtrg_flag}"
        ).strip()

    def acquire_data(self) -> None:
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

        file_full_path = Path(self.output_data_folder) / (
            self.acq_file_name + f"_{int(self.acq_time)}s"
        )

        command = self._build_acquire_command(
            file_full_path,
            self.acq_time,
            config_flag="--config",
            mode="qdc",
            enable_hw_trigger=True,
        )
        self.run_command(command)

    def convert_raw_to_coincidence(self) -> None:
        self.update_settings()
        if not all([self.petsys_folder, self.output_data_folder, self.config_file]):
            self.log_message(
                "Please set PETsys Folder, Output Data Folder, and Config File."
            )
            return

        file_full_path = Path(self.output_data_folder) / self.proc_data_entry.get()
        file_full_path = file_full_path.with_suffix("")  # Remove .rawf if present

        # Read the acquisition time from the proc_data_entry
        try:
            acq_time_str = file_full_path.name.split("_")[-1].replace("s", "")
            acq_time_v = int(acq_time_str)
        except (ValueError, IndexError):
            self.log_message(
                "Error: Unable to extract acquisition time or incorrect format. Expected: basename_{time}s"
            )
            return

        # Calculate the split time if needed
        split_time_param = ""
        if self.split_files > 1:
            split_time = acq_time_str / self.split_files + SPLIT_TIME_OFFSET
            split_time_param = f"--splitTime {split_time} "

        command = (
            f"cd {self.petsys_folder} && "
            f"./convert_raw_to_coincidence_fixed --config {self.config_file} -i {file_full_path} "
            f"-o {file_full_path}_coincFixed --writeBinaryFixed --writeMultipleHits 16 {split_time_param}"
        )

        def cleanup_callback():
            self.cleanup_conversion_files(
                self.output_data_folder, file_full_path + "_coincFixed"
            )

        self.run_command(command, callback=cleanup_callback)

    def convert_raw_to_group(self) -> None:
        self.update_settings()
        if not all([self.petsys_folder, self.output_data_folder, self.config_file]):
            self.log_message(
                "Please set PETsys Folder, Output Data Folder, and Config File."
            )
            return

        file_full_path = Path(self.output_data_folder) / self.proc_data_entry.get()
        file_full_path = file_full_path.with_suffix("")

        # Read the acquisition time from the proc_data_entry
        try:
            acq_time_str = file_full_path.name.split("_")[-1].replace("s", "")
            acq_time_v = int(acq_time_str)
        except (ValueError, IndexError):
            self.log_message(
                f"Error: Unable to extract acquisition time or incorrect format. File: {file_full_path}"
            )
            return

        # Calculate the split time if needed
        split_time_param = ""
        if self.split_files > 1:
            split_time = acq_time_v / self.split_files + SPLIT_TIME_OFFSET
            split_time_param = f"--splitTime {split_time} "

        command = (
            f"cd {self.petsys_folder} && "
            f"./convert_raw_to_group_fixed --config {self.config_file} -i {file_full_path} "
            f"-o {file_full_path}_groupFixed --writeBinaryFixed --writeMultipleHits 16 {split_time_param}"
        )

        def cleanup_callback():
            self.cleanup_conversion_files(
                self.output_data_folder, file_full_path + "_groupFixed"
            )

        self.run_command(command, callback=cleanup_callback)

    def generate_lm_file(self) -> None:
        """Generate LM file using the complete pipeline."""
        self.update_settings()
        if not all([self.process_petsys_folder, self.process_config_file]):
            self.log_message("Please set 'process_petsys' Folder and YAML Config File.")
            return

        # Get settings
        input_file = self.lm_input_entry.get().strip()

        if not input_file:
            self.log_message("Please select a Basename LDAT file.")
            return

        # Get the folder and base name
        input_path = Path(input_file)
        basename_folder = input_path.parent
        base_name = input_path.stem
        base_name = "_".join(base_name.split("_")[0:-1])

        ldat_files = list(basename_folder.glob(base_name + "*.ldat"))

        encal_file = self.lm_encal_entry.get().strip()
        cog_limits_file = self.lm_cog_limits_entry.get().strip()
        doi_limits_file = self.lm_doi_limits_entry.get().strip()

        if not all([input_file, encal_file, cog_limits_file, doi_limits_file]):
            self.log_message("Please provide all required files for LM generation.")
            return

        ldat_files_str = " ".join(str(f) for f in ldat_files)

        # Build the command using conda run -n for cleaner conda activation
        command = (
            f"cd {self.process_petsys_folder} && "
            f"conda run -n process_petsys "
            f"python {self.process_petsys_folder}/scripts_gui/cornell_listmode_cog_fixed_position.py "
            f"{self.process_config_file} {encal_file} {cog_limits_file} {doi_limits_file} {' '.join(ldat_files)}"
        )

        self.log_message("Generating LM file...")
        self.run_command(
            command,
            callback=lambda: self.log_message("LM file generation completed."),
        )

    def generate_energy_cal_file(self) -> None:
        self.update_settings()
        if not all([self.process_petsys_folder, self.process_config_file]):
            self.log_message("Please set 'process_petsys' Folder and YAML Config File.")
            return
        basename_file = self.ldat_basename_entry.get().strip()
        if not basename_file:
            self.log_message("Please select a Basename LDAT file.")
            return

        # Get the folder and base name
        input_path = Path(basename_file)
        basename_folder = input_path.parent
        base_name = input_path.stem
        base_name = "_".join(base_name.split("_")[0:-1])

        ldat_files = list(basename_folder.glob(base_name + "*.ldat"))
        cog_limits_file = self.lm_cog_limits_entry.get().strip()

        if not ldat_files:
            self.log_message(
                f"No LDAT files found for base '{base_name}' in {basename_folder}."
            )
            return

        if not cog_limits_file:
            self.log_message(
                "Please provide a COG Limits file for Energy cal generation."
            )
            return

        for f in ldat_files:
            self.log_message(f"Found LDAT file: {f}")

        # Build the command using conda run -n for cleaner conda activation
        command = (
            f"cd {self.process_petsys_folder} && "
            f"conda run -n process_petsys "
            f"python {self.process_petsys_folder}/scripts_gui/cornell_slab_en_cal_fixed_position.py "
            f"{self.process_config_file} {cog_limits_file} {' '.join(ldat_files)} --coinc"
        )
        self.log_message("Generating Energy cal file...")
        self.run_command(
            command,
            callback=lambda: self.log_message("Energy cal file generation completed."),
        )

    def run_complete_pipeline(self) -> None:
        """Execute the complete automated pipeline sequentially:
        1. Acquire data (generates .rawf)
        2. Convert RAWF to LDAT (with MAX_SPLIT_FILES)
        3. Generate Energy Cal file (.encal)
        4. Generate LM file

        Uses fixed pipeline paths and GUI filename for reproducible results.
        """
        self.update_settings()

        # Validate core settings needed for pipeline
        if not all(
            [
                self.petsys_folder,
                self.config_file,
                self.process_petsys_folder,
                self.process_config_file,
            ]
        ):
            self.log_message(
                "[ERROR] Pipeline requires: PETsys Folder, Config File, "
                "process_petsys Folder, and YAML Config File"
            )
            return

        if not self.daqd_state.get():
            self.log_message("[ERROR] DAQD must be ON to run the pipeline!")
            return

        if not self.system_initialized:
            self.log_message("[ERROR] System must be initialized to run the pipeline!")
            return

        # Create pipeline directory if it doesn't exist
        try:
            Path(PIPELINE_DATA_DIR).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.log_message(f"[ERROR] Could not create pipeline directory: {e}")
            return

        # Disable the pipeline button during execution
        self.pipeline_button.configure(state="disabled")

        self.log_message("\n" + "=" * 80)
        self.log_message("[*] STARTING COMPLETE AUTOMATED PIPELINE")
        self.log_message(f"[*] Using pipeline directory: {PIPELINE_DATA_DIR}")
        self.log_message(f"[*] Using filename: {self.acq_file_name}")
        self.log_message("=" * 80 + "\n")
        # Store start time for timing
        self.pipeline_start_time = time.time()
        self.log_message(f"[TIMING] Pipeline started at {time.strftime('%H:%M:%S')}")

        # Set split files to maximum for optimal processing
        self.split_files = MAX_SPLIT_FILES
        self.split_entry.delete(0, tk.END)
        self.split_entry.insert(0, str(MAX_SPLIT_FILES))

        # Update status
        self.pipeline_status_label.configure(
            text=f"[WAIT] Step 1/4: Acquiring data ({self.acq_time}s)...",
            text_color="orange",
        )

        # Step 1: Acquire data
        self.log_message(
            f"[ACQ] STEP 1/4: Acquiring data for {self.acq_time} seconds..."
        )
        self.log_message(
            f"[ACQ] Output will be saved to: {PIPELINE_DATA_DIR}/{self.acq_file_name}_{self.acq_time}s.rawf"
        )

        # Temporarily override output folder for pipeline
        original_output_folder = self.output_data_folder
        self.output_data_folder = PIPELINE_DATA_DIR
        self.output_entry.delete(0, tk.END)
        self.output_entry.insert(0, PIPELINE_DATA_DIR)

        # Store original run_command
        original_run_command = self.run_command

        def run_command_step1_with_step2(
            command_line: str, callback: Optional[Callable] = None
        ) -> None:
            def combined_callback():
                if callback:
                    callback()
                # Check for stop request before proceeding to step 2
                if self.stop_requested:
                    self.log_message("[STOP] Pipeline aborted after Step 1.")
                    return
                # Call step 2 immediately after acquisition completes
                self._pipeline_step2_convert(original_output_folder)

            original_run_command(command_line, callback=combined_callback)

        # Temporarily replace run_command for acquire_data
        self.run_command = run_command_step1_with_step2
        self.acquire_data()
        # Restore original run_command
        self.run_command = original_run_command

        # Schedule step 2 after acquisition completes
        # Wait for the acquisition to finish based on acquisition time
        # self.root.after(
        #     int((self.acq_time + 5) * 1000),
        #     lambda: self._pipeline_step2_convert(original_output_folder),
        # )

    def _pipeline_step2_convert(self, original_output_folder: str) -> None:
        """Pipeline Step 2: Convert RAWF to LDAT"""
        self.pipeline_status_label.configure(
            text=f"[WAIT] Step 2/4: Converting to LDAT ({MAX_SPLIT_FILES} splits)...",
            text_color="orange",
        )

        self.log_message(
            f"\n[CONVERT] STEP 2/4: Converting RAWF to LDAT ({MAX_SPLIT_FILES} splits)..."
        )

        # Set proc_data_entry to the acquired rawf file
        rawf_file = self.acq_file_name + f"_{int(self.acq_time)}s.rawf"
        self.proc_data_entry.delete(0, tk.END)
        self.proc_data_entry.insert(0, rawf_file)

        # Store original run_command
        original_run_command = self.run_command

        def run_command_with_step3(
            command_line: str, callback: Optional[Callable] = None
        ) -> None:
            def combined_callback():
                if callback:
                    callback()
                # Check for stop request before proceeding to step 3
                if self.stop_requested:
                    self.log_message("[STOP] Pipeline aborted after Step 2.")
                    return
                # Schedule step 3 after a short delay
                self.root.after(
                    2000,
                    lambda: self._pipeline_step3_energy_cal(original_output_folder),
                )

            original_run_command(command_line, callback=combined_callback)

        # Temporarily replace run_command
        self.run_command = run_command_with_step3
        self.convert_raw_to_coincidence()
        # Restore original run_command
        self.run_command = original_run_command

    def _pipeline_step3_energy_cal(self, original_output_folder: str) -> None:
        """Pipeline Step 3: Generate Energy Calibration file"""
        self.pipeline_status_label.configure(
            text="[WAIT] Step 3/4: Generating energy calibration...",
            text_color="orange",
        )

        self.log_message(f"\n[CAL] STEP 3/4: Generating Energy Calibration file...")

        # Point to the first ldat file (00000001.ldat)
        ldat_file = (
            self.acq_file_name + f"_{int(self.acq_time)}s_coincFixed_00000001.ldat"
        )
        ldat_path = Path(PIPELINE_DATA_DIR) / ldat_file

        self.ldat_basename_entry.delete(0, tk.END)
        self.ldat_basename_entry.insert(0, ldat_path)

        self.lm_cog_limits_entry.delete(0, tk.END)
        self.lm_cog_limits_entry.insert(0, PIPELINE_COG_LIMITS_FILE)

        # Store original run_command
        original_run_command = self.run_command

        def run_command_with_step4(
            command_line: str, callback: Optional[Callable] = None
        ) -> None:
            def combined_callback():
                if callback:
                    callback()
                # Check for stop request before proceeding to step 4
                if self.stop_requested:
                    self.log_message("[STOP] Pipeline aborted after Step 3.")
                    return
                # Schedule step 4 after a short delay
                self.root.after(
                    2000,
                    lambda: self._pipeline_step4_generate_lm(original_output_folder),
                )

            original_run_command(command_line, callback=combined_callback)

        # Temporarily replace run_command
        self.run_command = run_command_with_step4
        self.generate_energy_cal_file()
        # Restore original run_command
        self.run_command = original_run_command

    def _pipeline_step4_generate_lm(self, original_output_folder: str) -> None:
        """Pipeline Step 4: Generate LM file"""
        self.pipeline_status_label.configure(
            text="[WAIT] Step 4/4: Generating LM file...", text_color="orange"
        )

        self.log_message(f"\n[LM] STEP 4/4: Generating Listmode file...")

        # Use first ldat file as input
        ldat_file = (
            self.acq_file_name + f"_{int(self.acq_time)}s_coincFixed_00000001.ldat"
        )
        ldat_path = Path(PIPELINE_DATA_DIR) / ldat_file

        self.lm_input_entry.delete(0, tk.END)
        self.lm_input_entry.insert(0, str(ldat_path))

        # Set encal file dynamically based on acq_file_name
        encal_file = (
            Path(PIPELINE_ENCAL_DIR)
            / f"{self.acq_file_name}_{int(self.acq_time)}s_coincFixed_position_5regions.encal"
        )
        self.lm_encal_entry.delete(0, tk.END)
        self.lm_encal_entry.insert(0, str(encal_file))

        # Set cog limits file
        self.lm_cog_limits_entry.delete(0, tk.END)
        self.lm_cog_limits_entry.insert(0, PIPELINE_COG_LIMITS_FILE)

        # Set doi limits file
        self.lm_doi_limits_entry.delete(0, tk.END)
        self.lm_doi_limits_entry.insert(0, PIPELINE_DOI_LIMITS_FILE)

        # Store original run_command
        original_run_command = self.run_command

        def run_command_with_completion(
            command_line: str, callback: Optional[Callable] = None
        ) -> None:
            def combined_callback():
                if callback:
                    callback()
                # Check for stop request before final completion
                if self.stop_requested:
                    self.log_message("[STOP] Pipeline aborted after Step 4.")
                    return
                # Pipeline complete
                self.root.after(
                    1000,
                    lambda: self._pipeline_complete(original_output_folder),
                )

            original_run_command(command_line, callback=combined_callback)

        # Temporarily replace run_command
        self.run_command = run_command_with_completion
        self.generate_lm_file()
        # Restore original run_command
        self.run_command = original_run_command

    def _pipeline_complete(self, original_output_folder: str) -> None:
        """Handle pipeline completion"""
        # Calculate and log elapsed time
        if hasattr(self, "pipeline_start_time"):
            elapsed_time = time.time() - self.pipeline_start_time
            elapsed_mins = elapsed_time / 60
            self.log_message(
                f"[TIMING] Pipeline execution time: {elapsed_time:.1f}s ({elapsed_mins:.1f} minutes)"
            )
        # Restore original settings
        self.output_data_folder = original_output_folder
        self.output_entry.delete(0, tk.END)
        self.output_entry.insert(0, original_output_folder)

        self.log_message("\n" + "=" * 80)
        self.log_message("[SUCCESS] COMPLETE PIPELINE FINISHED SUCCESSFULLY!")
        self.log_message(f"[SUCCESS] Results saved to: {PIPELINE_DATA_DIR}")
        self.log_message(f"[SUCCESS] Using filename: {self.acq_file_name}")
        self.log_message(
            f"[SUCCESS] LM file generated in the pipeline directory: /data/nvmDisk/Cornell/data/LM/."
        )
        self.log_message("=" * 80 + "\n")
        self.pipeline_status_label.configure(
            text="[OK] Pipeline completed successfully!", text_color="green"
        )

        # Re-enable the pipeline button
        self.pipeline_button.configure(state="normal")

        # Clear status after 10 seconds
        self.root.after(10000, lambda: self.pipeline_status_label.configure(text=""))

    def init_system(self) -> None:
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
        self.run_command(command, callback=self.after_init)

    def after_init(self) -> None:
        self.system_initialized = True
        self.acquire_button.configure(state="normal")
        self.pipeline_button.configure(state="normal")
        self.qc_run_button.configure(state="normal")

        # Show recommendation message
        recommendation = "[RECOMMENDATION] Wait at least 5 minutes before acquiring data for system stabilization"
        self.log_message("\n" + recommendation + "\n")

        # Highlight the message by changing its appearance
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
