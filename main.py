import os
import sys
import json
import threading
import queue
import appdirs
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from concurrent.futures import ThreadPoolExecutor, as_completed

class ImageStamperGUI:
    def __init__(self, master):
        self.master = master
        master.title("Image Stamper - Batch Logo Adder")
        master.geometry("800x600")
        master.resizable(False, False)

        # Determine the settings directory using appdirs
        self.settings_dir = appdirs.user_config_dir("ImageStamper", "maplenetwork")
        os.makedirs(self.settings_dir, exist_ok=True)

        # Path to settings.json
        self.settings_path = os.path.join(self.settings_dir, "settings.json")

        # Initialize variables
        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.logo_path = tk.StringVar()
        self.position = tk.StringVar(value="bottom-right")
        self.logo_size_ratio = tk.DoubleVar(value=0.15)
        self.opacity = tk.IntVar(value=128)

        # Initialize queue for thread-safe logging
        self.log_queue = queue.Queue()

        # Initialize ThreadPoolExecutor
        self.executor = None
        self.max_workers = 8  # Adjust based on your CPU cores

        # Flag to control processing
        self.processing = False

        # Flag to indicate if settings are being loaded
        self.loading_settings = False  # <--- Added Flag

        # Create GUI components
        self.create_widgets()

        # Load settings if available
        self.load_settings()

        # Start log updater
        self.master.after(100, self.process_log_queue)

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
        size_scale = tk.Scale(
            self.master,
            variable=self.logo_size_ratio,
            from_=0.05,
            to=0.5,
            resolution=0.01,
            orient=tk.HORIZONTAL,
            length=300,
            command=lambda val: self.save_settings()
        )
        size_scale.grid(row=4, column=1, sticky="w", **padding_options)
        tk.Label(self.master, text="Relative to Image Size").grid(row=4, column=1, sticky="e", padx=(310, 10), pady=5)

        # ===== Logo Opacity =====
        tk.Label(self.master, text="Logo Opacity:", font=('Helvetica', 10, 'bold')).grid(row=5, column=0, sticky="e", **padding_options)
        opacity_scale = tk.Scale(
            self.master,
            variable=self.opacity,
            from_=0,
            to=255,
            orient=tk.HORIZONTAL,
            length=300,
            command=lambda val: self.save_settings()
        )
        opacity_scale.grid(row=5, column=1, sticky="w", **padding_options)
        tk.Label(self.master, text="0 (Transparent) to 255 (Opaque)").grid(row=5, column=1, sticky="e", padx=(310, 10), pady=5)

        # ===== Start Processing Button =====
        self.start_button = tk.Button(
            self.master,
            text="Start Processing",
            command=self.start_processing,
            bg="green",
            fg="white",
            font=('Helvetica', 12, 'bold')
        )
        self.start_button.grid(row=6, column=1, pady=20)

        # ===== Progress Bar =====
        tk.Label(self.master, text="Progress:", font=('Helvetica', 10, 'bold')).grid(row=7, column=0, sticky="e", **padding_options)
        self.progress = ttk.Progressbar(self.master, orient='horizontal', length=500, mode='determinate')
        self.progress.grid(row=7, column=1, columnspan=2, padx=10, pady=5)

        # ===== Progress Log =====
        tk.Label(self.master, text="Progress Log:", font=('Helvetica', 10, 'bold')).grid(row=8, column=0, sticky="ne", padx=10, pady=5)
        self.log_text = tk.Text(self.master, height=25, width=80, state='disabled', wrap='word')
        self.log_text.grid(row=8, column=1, columnspan=2, padx=10, pady=5)

        # ===== Scrollbar for Progress Log =====
        scrollbar = tk.Scrollbar(self.master, command=self.log_text.yview)
        scrollbar.grid(row=8, column=3, sticky='nsew', pady=5)
        self.log_text['yscrollcommand'] = scrollbar.set

        # ===== Bind Events to Save Settings =====
        # Set the flag before binding to prevent save_settings during load
        self.loading_settings = True  # <--- Set flag to True before bindings

        self.input_dir.trace_add('write', lambda *args: self.save_settings())
        self.output_dir.trace_add('write', lambda *args: self.save_settings())
        self.logo_path.trace_add('write', lambda *args: self.save_settings())
        self.position.trace_add('write', lambda *args: self.save_settings())

        self.loading_settings = False  # <--- Set flag to False after bindings

    def browse_input_dir(self):
        directory = filedialog.askdirectory(title="Select Input Directory")
        if directory:
            self.input_dir.set(directory)
            self.log(f"Selected Input Directory: {directory}")

    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_dir.set(directory)
            self.log(f"Selected Output Directory: {directory}")

    def browse_logo(self):
        filetypes = [
            ("Image Files", ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.gif")),
            ("All Files", "*.*")
        ]
        file = filedialog.askopenfilename(title="Select Logo Image", filetypes=filetypes)
        if file:
            self.logo_path.set(file)
            self.log(f"Selected Logo File: {file}")


    def start_processing(self):
        if self.processing:
            messagebox.showwarning("Processing", "Image processing is already running.")
            return

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

        # Clear previous logs and reset progress bar
        self.clear_log()
        self.progress['value'] = 0

        # Start processing in a separate thread
        self.processing = True
        threading.Thread(target=self.process_images, daemon=True).start()

    def disable_start_button(self):
        self.start_button.config(state='disabled')

    def enable_start_button(self):
        self.start_button.config(state='normal')

    def log(self, message):
        """
        Thread-safe logging by putting messages into a queue.
        """
        self.log_queue.put(message)

    def process_log_queue(self):
        """
        Process log messages from the queue and update the log_text widget.
        """
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.config(state='normal')
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.see(tk.END)
                self.log_text.config(state='disabled')
        except queue.Empty:
            pass
        finally:
            self.master.after(100, self.process_log_queue)

    def clear_log(self):
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')

    def load_settings(self):
        """
        Loads settings from settings.json and updates the GUI fields.
        """
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r') as f:
                    settings = json.load(f)
                
                # Temporarily set the loading flag to prevent save_settings from being called
                self.loading_settings = True  # <--- Set flag before setting variables

                self.input_dir.set(settings.get('input_dir', ''))
                self.output_dir.set(settings.get('output_dir', ''))
                self.logo_path.set(settings.get('logo_path', ''))
                self.position.set(settings.get('position', 'bottom-right'))
                self.logo_size_ratio.set(settings.get('logo_size_ratio', 0.1))
                self.opacity.set(settings.get('opacity', 128))

                self.log(f"Loaded settings from {self.settings_path}")
            except Exception as e:
                self.log(f"Error loading settings: {e}")
            finally:
                self.loading_settings = False  # <--- Reset flag after loading
        else:
            self.log("No existing settings found. Using default values.")

    def save_settings(self, *args):
        """
        Saves the current settings to settings.json.
        """
        if getattr(self, 'loading_settings', False):
            # Don't save settings while loading to prevent race condition
            return

        settings = {
            'input_dir': self.input_dir.get(),
            'output_dir': self.output_dir.get(),
            'logo_path': self.logo_path.get(),
            'position': self.position.get(),
            'logo_size_ratio': self.logo_size_ratio.get(),
            'opacity': self.opacity.get()
        }

        try:
            with open(self.settings_path, 'w') as f:
                json.dump(settings, f, indent=4)
            # Avoid logging every save to reduce clutter
            # self.log(f"Settings saved to {self.settings_path}")
        except Exception as e:
            self.log(f"Error saving settings: {e}")

    def process_images(self):
        input_dir = self.input_dir.get()
        output_dir = self.output_dir.get()
        logo_path = self.logo_path.get()
        position = self.position.get()
        logo_size_ratio = self.logo_size_ratio.get()
        opacity = self.opacity.get()

        # Ensure output directory exists
        try:
            os.makedirs(output_dir, exist_ok=True)
            self.log(f"Output directory ensured at: {output_dir}")
        except Exception as e:
            self.log(f"Error ensuring output directory: {e}")
            self.enable_start_button()
            self.processing = False
            return

        # Load the logo image
        try:
            logo = Image.open(logo_path).convert("RGBA")
            self.log(f"Loaded logo from: {logo_path}")
        except Exception as e:
            self.log(f"Error loading logo: {e}")
            self.enable_start_button()
            self.processing = False
            return

        supported_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
        all_files = [f for f in os.listdir(input_dir) if f.lower().endswith(supported_extensions) and os.path.isfile(os.path.join(input_dir, f))]
        total_files = len(all_files)

        if total_files == 0:
            self.log("No supported images found in the input directory.")
            self.enable_start_button()
            self.processing = False
            return

        self.log(f"Found {total_files} supported image(s) in the input directory.")
        self.progress['maximum'] = total_files

        # Initialize ThreadPoolExecutor
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        futures = []

        for filename in all_files:
            input_path = os.path.join(input_dir, filename)
            futures.append(self.executor.submit(
                self.process_single_image, input_path, output_dir, logo, position, logo_size_ratio, opacity
            ))

        for future in as_completed(futures):
            try:
                future.result()  # This will re-raise any exception occurred in the thread
            except Exception as e:
                self.log(f"❌ Unexpected error: {e}")

        self.log(f"🎉 Processing completed: {total_files} image(s) processed.")
        self.enable_start_button()
        self.processing = False

    def process_single_image(self, input_path, output_dir, logo, position, logo_size_ratio, opacity):
        filename = os.path.basename(input_path)
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
                composite.save(output_path, format='JPEG', quality=100)  # Adjust quality as needed

                # Update progress bar
                self.master.after(0, lambda: self.progress.step(1))

                # Log success
                self.log(f"✅ Added logo to '{filename}' and saved as '{output_filename}'.")

        except Exception as e:
            # Update progress bar
            self.master.after(0, lambda: self.progress.step(1))

            # Log failure
            self.log(f"❌ Failed to process '{filename}': {e}")

def main():
    root = tk.Tk()
    app = ImageStamperGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
