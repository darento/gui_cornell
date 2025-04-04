using System.Diagnostics;

namespace gui_petsys
{
    public partial class Form1 : Form
    {
        public Form1()
        {
            InitializeComponent();
        }

        private void Form1_Load(object sender, EventArgs e)
        {

        }

        private void outputBox_TextChanged(object sender, EventArgs e)
        {

        }

        private void Ejecturar_script_Click(object sender, EventArgs e)
        {
            string pythonExe = "C:\\Users\\dsanchez\\AppData\\Local\\anaconda3\\python.exe"; // o pon aquí la ruta completa a python.exe si lo prefieres
            string scriptPath = "C:\\Users\\dsanchez\\Desktop\\Python_scripts\\test_gui.py"; // cambia por la ruta a tu script real

            var psi = new ProcessStartInfo
            {
                FileName = pythonExe,
                Arguments = $"\"{scriptPath}\"",
                RedirectStandardOutput = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            try
            {
                using (var process = Process.Start(psi))
                {
                    string output = process.StandardOutput.ReadToEnd();
                    process.WaitForExit();
                    outputBox.Text = output;
                }
            }
            catch (Exception ex)
            {
                outputBox.Text = $"Error: {ex.Message}";
            }
        }
    }
}