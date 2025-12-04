# gui_cornell

**A Python-based GUI to acquire using PETsys software.**

This project provides a modern graphical interface built with **CustomTkinter** to simplify running PETsys commands. It was developed to bridge existing PETsys command-line workflows (such as data acquisition, conversion, and DAQD activation) with an easy-to-use GUI. This is particularly useful in research or instrumentation environments where quick, interactive control is desired.

---

## 🖥️ Features

- **Modern UI:**
  Built with CustomTkinter for a sleek, modern look with.

- **Command Buttons:**
  Execute specific PETsys commands like:
  - Activate DAQD
  - Acquire Data
  - Convert Raw Data to Coincidence Format

- **Configuration Management:**
  Choose the configuration file through a file dialog and display its current path.

- **Live Output Display:**
  View the command outputs (stdout and stderr) in a scrollable text area.

- **Simple and Extendable:**
  Written in Python, allowing easy modifications and expansion.

---

## 🚀 How to Use

1. **Clone the repository:**
   ```bash
   git clone https://github.com/darento/gui_cornell.git
   ```

2. **Navigate to the project directory:**
   ```bash
   cd gui_cornell
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application:**
   ```bash
   python src/gui.py
   ```

5. **Configure and use:**
   - Choose the configuration file using the "Choose Config File" button.
   - Use the dedicated buttons to execute PETsys commands.

## 📁 Project Structure

```
gui_cornell/
├── src/
│   └── gui.py                # Main GUI entry point
├── .gitignore                 # Files and folders to ignore in Git
├── README.md                  # Project documentation
└── requirements.txt           # Python dependencies
```

## 🛠️ **Technologies**
   - Python 3.x
   - **CustomTkinter** (for the GUI)
   - **Pillow** (for image handling)
   - Standard libraries: subprocess, threading, etc.

---

📜 **License:**
   This project is licensed under the MIT License.

🧪 **Project Status:**
   💡 Early-stage tool — open for expansion, additional features, and community contributions.

🙌 **Author:**
   David Sanchez (@darento)
