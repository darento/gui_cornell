import os
import time
import tkinter as tk
from tkinter import ttk, messagebox


class CustomFileBrowser:
    def __init__(self, parent, title, callback, initial_dir=None):
        """
        Create a custom file browser dialog.

        Args:
            parent: Parent tkinter window
            title: Dialog title
            callback: Function to call with selected path
            initial_dir: Starting directory (defaults to home)
        """
        self.callback = callback
        self.browser = tk.Toplevel(parent)
        self.browser.title(title)
        self.browser.geometry("700x500")
        self.browser.transient(parent)
        self.browser.grab_set()  # Make dialog modal

        if initial_dir is None or not os.path.isdir(initial_dir):
            initial_dir = os.path.expanduser("~")

        # Current path display
        path_frame = tk.Frame(self.browser)
        path_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(path_frame, text="Path:").pack(side=tk.LEFT, padx=5)
        self.path_var = tk.StringVar(value=initial_dir)
        path_entry = tk.Entry(path_frame, textvariable=self.path_var, width=60)
        path_entry.pack(side=tk.LEFT, padx=5, fill="x", expand=True)

        # Files and directories list with Treeview
        tree_frame = tk.Frame(self.browser)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Create Treeview with scrollbars
        self.tree = ttk.Treeview(
            tree_frame, columns=("type", "modified"), selectmode="browse"
        )
        self.tree.heading("#0", text="Name")
        self.tree.heading("type", text="Type")
        self.tree.heading("modified", text="Modified")
        self.tree.column("#0", width=300)
        self.tree.column("type", width=100)
        self.tree.column("modified", width=200)

        # Add scrollbars
        yscroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(
            tree_frame, orient="horizontal", command=self.tree.xview
        )
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)

        # Grid layout for tree and scrollbars
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Buttons
        btn_frame = tk.Frame(self.browser)
        btn_frame.pack(fill="x", padx=10, pady=10)

        home_btn = tk.Button(
            btn_frame,
            text="Home",
            command=lambda: self.refresh_list(os.path.expanduser("~")),
        )
        home_btn.pack(side=tk.LEFT, padx=5)

        up_btn = tk.Button(
            btn_frame,
            text="Up",
            command=lambda: self.refresh_list(os.path.dirname(self.path_var.get())),
        )
        up_btn.pack(side=tk.LEFT, padx=5)

        select_btn = tk.Button(btn_frame, text="Select", command=self.select_directory)
        select_btn.pack(side=tk.RIGHT, padx=5)

        cancel_btn = tk.Button(btn_frame, text="Cancel", command=self.browser.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=5)

        # Bind double-click event
        self.tree.bind("<Double-1>", self.on_item_double_click)

        # Initial directory listing
        self.refresh_list(initial_dir)

    def refresh_list(self, path):
        if not os.path.isdir(path):
            return

        self.tree.delete(*self.tree.get_children())
        self.path_var.set(path)

        try:
            # Add parent directory
            self.tree.insert(
                "", "end", text="..", values=("Parent Directory", ""), tags=("dir",)
            )

            # List files and directories
            items = os.listdir(path)
            for item in sorted(items):
                full_path = os.path.join(path, item)

                try:
                    modified = time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(full_path))
                    )

                    if os.path.isdir(full_path):
                        self.tree.insert(
                            "",
                            "end",
                            text=item,
                            values=("Directory", modified),
                            tags=("dir",),
                        )
                    else:
                        size = os.path.getsize(full_path)
                        size_str = (
                            f"{size / 1024:.1f} KB" if size > 1024 else f"{size} bytes"
                        )
                        self.tree.insert(
                            "",
                            "end",
                            text=item,
                            values=(size_str, modified),
                            tags=("file",),
                        )
                except (PermissionError, OSError):
                    # Skip files that can't be accessed
                    continue

        except PermissionError:
            messagebox.showerror(
                "Error", "Permission denied: Cannot access this directory"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Error accessing directory: {e}")

    def on_item_double_click(self, event):
        selection = self.tree.selection()
        if not selection:
            return

        item = selection[0]
        item_text = self.tree.item(item, "text")
        current_path = self.path_var.get()

        if item_text == "..":
            # Go up one directory
            new_path = os.path.dirname(current_path)
        else:
            # Navigate to selected directory
            new_path = os.path.join(current_path, item_text)

        if os.path.isdir(new_path):
            self.refresh_list(new_path)

    def select_directory(self):
        selected_path = self.path_var.get()
        if os.path.isdir(selected_path):
            self.callback(selected_path)
            self.browser.destroy()
        else:
            messagebox.showerror("Error", "Invalid directory selected")


def open_folder_browser(parent, title, callback, initial_dir=None):
    """Helper function to create and show a folder browser dialog"""
    CustomFileBrowser(parent, title, callback, initial_dir)
