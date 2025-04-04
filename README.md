# gui_petsys

**A Windows Forms GUI built in C# to execute Python scripts from a desktop application.**

This project serves as a lightweight interface between systems built in C# (e.g., for instrumentation or data acquisition) and Python scripts used for processing or analysis. It is especially useful in research or medical imaging contexts such as PET systems.

---

## 🖥️ Features

- Execute `.py` scripts directly from a GUI
- Display the script's output in a multi-line textbox
- Built in Visual Studio 2022 (.NET 6 or later)
- Compatible with Anaconda or any Python 3.x installation

---

## 🚀 How to Use

1. **Clone the repository**:
   ```bash
   git clone https://github.com/darento/gui_petsys.git
   ```

2. **Open the solution**:  
   Open `gui_petsys.sln` in Visual Studio

3. **Set the path to your Python interpreter** in `Form1.cs`:
   ```csharp
   string pythonExe = @"C:\Path\To\python.exe";
   ```

4. **Run the application** and click the button to execute a Python script.

---

## 📁 Project Structure

```
gui_petsys/
├── gui_petsys.sln              # Visual Studio Solution
├── gui_petsys/                 # Main project folder
│   ├── Form1.cs                # Main GUI logic
│   ├── Form1.Designer.cs       # Auto-generated UI layout
│   └── Program.cs              # App entry point
└── .gitignore                  # Ignored files and folders
```

---

## 🛠️ Technologies

- C# (.NET 6+)
- Windows Forms
- Python 3.x
- Visual Studio 2022

---

## 📜 License

This project is licensed under the **MIT License**.

---

## 🧪 Project Status

💡 Early-stage tool — open for expansion, features and contributions.

---

## 🙌 Author

David Sanchez ([@darento](https://github.com/darento))
