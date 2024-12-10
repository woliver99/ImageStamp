import os
import sys
import threading
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

class ImageStamperGUI:
    def __init__(self, master):
        self.master = master
        master.title("Image Stamper - Batch Logo Adder")
        master.geometry("800x700")
        master.resizable(False, False)

        # Determine the script's directory
        self.script_dir = self.get_script_directory()

        # Initialize variables
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.logo_path = tk.StringVar()
        self.position = tk.StringVar(value="bottom-right")
        self.logo_size_ratio = tk.DoubleVar(value=0.1)
        self.opacity = tk.IntVar(value=128)

        # Create GUI components
        self.create_widgets()

    def get_script_directory(self):
        """
        Returns the directory where the script is located.
        Falls back to the current working directory if __file__ is not defined.
        """
        try:
            return os.path.dirname(os.path.abspath(__file__))
        except NameError:
            return os.getcwd()

    def create_widgets(self):
        padding_options = {'padx': 10, 'pady': 5}

        # ===== Input Directory =====
        tk.Label(self.master, text="Input Directory:", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, sticky="e", **padding_options)
        input_entry = tk.Entry(self.master, textvariable=self.input_dir, width=50, state='readonly')
        input_entry.grid(row=0, column=1, **padding_options)
        tk.Button(self.master, text="Browse", command=self.browse_input_dir).grid(row=0, column=2, **padding_options)

        # ===== Output Directory =====
        tk.Label(self.master, text="Output Directory:", font=('Helvetica', 10, 'bold')).grid(row=1, column=0, sticky="e", **padding_options)
        output_entry = tk.Entry(self.master, textvariable=self.output_dir, width=50, state='readonly')
        output_entry.grid(row=1, column=1, **padding_options)
        tk.Button(self.master, text="Browse", command=self.browse_output_dir).grid(row=1, column=2, **padding_options)

        # ===== Logo File =====
        tk.Label(self.master, text="Logo File:", font=('Helvetica', 10, 'bold')).grid(row=2, column=0, sticky="e", **padding_options)
        logo_entry = tk.Entry(self.master, textvariable=self.logo_path, width=50, state='readonly')
        logo_entry.grid(row=2, column=1, **padding_options)
        tk.Button(self.master, text="Browse", command=self.browse_logo).grid(row=2, column=2, **padding_options)

        # ===== Logo Position =====
        tk.Label(self.master, text="Logo Position:", font=('Helvetica', 10, 'bold')).grid(row=3, column=0, sticky="e", **padding_options)
        positions = ['bottom-right', 'bottom-left', 'top-right', 'top-left', 'center']
        position_menu = tk.OptionMenu(self.master, self.position, *positions)
        position_menu.config(width=15)
        position_menu.grid(row=3, column=1, sticky="w", **padding_options)

        # ===== Logo Size Ratio =====
        tk.Label(self.master, text="Logo Size Ratio:", font=('Helvetica', 10, 'bold')).grid(row=4, column=0, sticky="e", **padding_options)
        size_scale = tk.Scale(self.master, variable=self.logo_size_ratio, from_=0.05, to=0.5, resolution=0.01, orient=tk.HORIZONTAL, length=300)
        size_scale.grid(row=4, column=1, sticky="w", **padding_options)
        tk.Label(self.master, text="Relative to Image Size").grid(row=4, column=1, sticky="e", padx=(310, 10), pady=5)

        # ===== Logo Opacity =====
        tk.Label(self.master, text="Logo Opacity:", font=('Helvetica', 10, 'bold')).grid(row=5, column=0, sticky="e", **padding_options)
        opacity_scale = tk.Scale(self.master, variable=self.opacity, from_=0, to=255, orient=tk.HORIZONTAL, length=300)
        opacity_scale.grid(row=5, column=1, sticky="w", **padding_options)
        tk.Label(self.master, text="0 (Transparent) to 255 (Opaque)").grid(row=5, column=1, sticky="e", padx=(310, 10), pady=5)

        # ===== Start Processing Button =====
        tk.Button(self.master, text="Start Processing", command=self.start_processing, bg="green", fg="white", font=('Helvetica', 12, 'bold')).grid(row=6, column=1, pady=20)

        # ===== Progress Log =====
        tk.Label(self.master, text="Progress Log:", font=('Helvetica', 10, 'bold')).grid(row=7, column=0, sticky="ne", padx=10, pady=5)
        self.log_text = tk.Text(self.master, height=20, width=80, state='disabled', wrap='word')
        self.log_text.grid(row=7, column=1, columnspan=2, padx=10, pady=5)

        # ===== Scrollbar for Progress Log =====
        scrollbar = tk.Scrollbar(self.master, command=self.log_text.yview)
        scrollbar.grid(row=7, column=3, sticky='nsew', pady=5)
        self.log_text['yscrollcommand'] = scrollbar.set

    def browse_input_dir(self):
        directory = filedialog.askdirectory(title="Select Input Directory", initialdir=self.script_dir)
        if directory:
            self.input_dir.set(directory)
            self.log(f"Selected Input Directory: {directory}")

    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="Select Output Directory", initialdir=self.script_dir)
        if directory:
            self.output_dir.set(directory)
            self.log(f"Selected Output Directory: {directory}")

    def browse_logo(self):
        filetypes = [("Image Files", "*.png;*.jpg;*.jpeg;*.bmp;*.gif"), ("All Files", "*.*")]
        file = filedialog.askopenfilename(title="Select Logo Image", filetypes=filetypes, initialdir=self.script_dir)
        if file:
            self.logo_path.set(file)
            self.log(f"Selected Logo File: {file}")

    def start_processing(self):
        # Validate inputs
        if not self.input_dir.get():
            messagebox.showerror("Error", "Please select an input directory.")
            return
        if not self.output_dir.get():
            messagebox.showerror("Error", "Please select an output directory.")
            return
        if not self.logo_path.get():
            messagebox.showerror("Error", "Please select a logo image.")
            return

        # Disable the start button to prevent multiple clicks
        self.disable_start_button()

        # Clear previous logs
        self.clear_log()

        # Start processing in a separate thread to keep the GUI responsive
        threading.Thread(target=self.process_images, daemon=True).start()

    def disable_start_button(self):
        for widget in self.master.grid_slaves(row=6, column=1):
            widget.config(state='disabled')

    def enable_start_button(self):
        for widget in self.master.grid_slaves(row=6, column=1):
            widget.config(state='normal')

    def log(self, message):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def clear_log(self):
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')

    def process_images(self):
        input_dir = self.input_dir.get()
        output_dir = self.output_dir.get()
        logo_path = self.logo_path.get()
        position = self.position.get()
        logo_size_ratio = self.logo_size_ratio.get()
        opacity = self.opacity.get()

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        self.log(f"Output directory ensured at: {output_dir}")

        # Load the logo image
        try:
            logo = Image.open(logo_path).convert("RGBA")
            self.log(f"Loaded logo from: {logo_path}")
        except Exception as e:
            self.log(f"Error loading logo: {e}")
            self.enable_start_button()
            return

        supported_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
        total_files = len([f for f in os.listdir(input_dir) if f.lower().endswith(supported_extensions) and os.path.isfile(os.path.join(input_dir, f))])
        processed_files = 0

        self.log(f"Found {total_files} supported image(s) in the input directory.")

        for filename in os.listdir(input_dir):
            input_path = os.path.join(input_dir, filename)

            # Check if it's a file and has a supported image extension
            if os.path.isfile(input_path) and filename.lower().endswith(supported_extensions):
                try:
                    with Image.open(input_path).convert("RGBA") as base_image:
                        base_width, base_height = base_image.size

                        # Calculate logo size
                        logo_size = int(min(base_width, base_height) * logo_size_ratio)
                        logo_ratio = logo.width / logo.height
                        logo_new_size = (logo_size, int(logo_size / logo_ratio))
                        logo_resized = logo.resize(logo_new_size, Image.Resampling.LANCZOS)

                        # Adjust logo opacity
                        if opacity < 255:
                            # Split the alpha channel and adjust opacity
                            alpha = logo_resized.split()[3]
                            alpha = alpha.point(lambda p: p * opacity // 255)
                            logo_resized.putalpha(alpha)

                        # Determine position
                        if position == 'bottom-right':
                            pos = (base_width - logo_resized.width - 10, base_height - logo_resized.height - 10)
                        elif position == 'bottom-left':
                            pos = (10, base_height - logo_resized.height - 10)
                        elif position == 'top-right':
                            pos = (base_width - logo_resized.width - 10, 10)
                        elif position == 'top-left':
                            pos = (10, 10)
                        elif position == 'center':
                            pos = ((base_width - logo_resized.width) // 2, (base_height - logo_resized.height) // 2)
                        else:
                            raise ValueError("Invalid position argument")

                        # Create a new image for compositing
                        composite = Image.new("RGBA", base_image.size)
                        composite.paste(base_image, (0, 0))
                        composite.paste(logo_resized, pos, logo_resized)

                        # Convert to RGB (JPEG does not support alpha channels)
                        composite = composite.convert("RGB")

                        # Prepare output filename with .jpg extension
                        base_filename, _ = os.path.splitext(filename)
                        output_filename = f"{base_filename}.jpg"
                        output_path = os.path.join(output_dir, output_filename)

                        # Save the image as JPEG
                        composite.save(output_path, format='JPEG', quality=95)  # Adjust quality as needed

                        processed_files += 1
                        self.log(f"✅ Added logo to '{filename}' and saved as '{output_filename}'.")

                except Exception as e:
                    self.log(f"❌ Failed to process '{filename}': {e}")

        self.log(f"🎉 Processing completed: {processed_files}/{total_files} image(s) processed.")
        self.enable_start_button()

def main():
    root = tk.Tk()
    app = ImageStamperGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
