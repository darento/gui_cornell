namespace gui_petsys
{
    partial class Form1
    {
        /// <summary>
        ///  Required designer variable.
        /// </summary>
        private System.ComponentModel.IContainer components = null;

        /// <summary>
        ///  Clean up any resources being used.
        /// </summary>
        /// <param name="disposing">true if managed resources should be disposed; otherwise, false.</param>
        protected override void Dispose(bool disposing)
        {
            if (disposing && (components != null))
            {
                components.Dispose();
            }
            base.Dispose(disposing);
        }

        #region Windows Form Designer generated code

        /// <summary>
        ///  Required method for Designer support - do not modify
        ///  the contents of this method with the code editor.
        /// </summary>
        private void InitializeComponent()
        {
            outputBox = new TextBox();
            Ejecturar_script = new Button();
            SuspendLayout();
            // 
            // outputBox
            // 
            outputBox.Location = new Point(43, 28);
            outputBox.Multiline = true;
            outputBox.Name = "outputBox";
            outputBox.ScrollBars = ScrollBars.Vertical;
            outputBox.Size = new Size(100, 23);
            outputBox.TabIndex = 0;
            outputBox.TextChanged += outputBox_TextChanged;
            // 
            // Ejecturar_script
            // 
            Ejecturar_script.Location = new Point(81, 96);
            Ejecturar_script.Name = "Ejecturar_script";
            Ejecturar_script.Size = new Size(75, 23);
            Ejecturar_script.TabIndex = 1;
            Ejecturar_script.Text = "button1";
            Ejecturar_script.UseVisualStyleBackColor = true;
            Ejecturar_script.Click += Ejecturar_script_Click;
            // 
            // Form1
            // 
            AutoScaleDimensions = new SizeF(7F, 15F);
            AutoScaleMode = AutoScaleMode.Font;
            ClientSize = new Size(800, 450);
            Controls.Add(Ejecturar_script);
            Controls.Add(outputBox);
            Name = "Form1";
            Text = "MAGI";
            Load += Form1_Load;
            ResumeLayout(false);
            PerformLayout();
        }

        #endregion

        private TextBox outputBox;
        private Button Ejecturar_script;
    }
}