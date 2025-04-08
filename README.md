# gui_cornell

**A Python-based GUI to manage PETsys commands for module validation.**

This project provides a lightweight graphical interface built with Tkinter to simplify running PETsys commands. It was developed to bridge existing PETsys command-line workflows (such as data acquisition, conversion, and DAQD activation) with an easy-to-use GUI. This is particularly useful in research or instrumentation environments where quick, interactive control is desired.

---

## 🖥️ Features

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
  Written in Python using Tkinter, allowing easy modifications and expansion.

---

## 🚀 How to Use

1. **Clone the repository:**
   ```bash
   git clone https://github.com/darento/gui_cornell.git

2. **Navigate to the project directory:**
   cd gui_cornell

3. **Install dependencies: If you have a requirements.txt, run:**
   pip install -r requirements.txt

4. **Run the application:**
   python gui.py

5. **Configure and use:**
   - Choose the configuration file using the "Choose Config File" button.
   - Use the dedicated buttons to execute PETsys commands.

📁 Project Structure
gui_cornell/
├── src/
│   └── gui.py                # Main GUI entry point
├── .gitignore                 # Files and folders to ignore in Git
├── README.md                  # Project documentation
└── requirements.txt           # (Optional) Python dependencies

🛠️ **Technologies**
   - Python 3.x
   - Tkinter (for the GUI)
   - Standard libraries: subprocess, threading, etc.

📜 **License:**
   This project is licensed under the MIT License.

🧪 **Project Status:**
   💡 Early-stage tool — open for expansion, additional features, and community contributions.

🙌 **Author:**
   David Sanchez (@darento)
