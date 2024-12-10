import os
from PIL import Image

def add_logo_to_images(
    input_dir,
    output_dir,
    logo_path,
    position='bottom-right',
    logo_size_ratio=0.1,
    opacity=128
):
    """
    Adds a logo to all images in the input directory and saves them as JPEGs to the output directory.

    :param input_dir: Path to the directory containing input images.
    :param output_dir: Path to the directory where output images will be saved.
    :param logo_path: Path to the logo image (preferably PNG with transparency).
    :param position: Position to place the logo ('bottom-right', 'bottom-left', 'top-right', 'top-left', 'center').
    :param logo_size_ratio: The logo size relative to the target image's smaller dimension (0 < ratio < 1).
    :param opacity: Opacity of the logo (0 transparent - 255 opaque).
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Load the logo image
    logo = Image.open(logo_path).convert("RGBA")

    # Iterate over all files in the input directory
    for filename in os.listdir(input_dir):
        # Construct full file path
        input_path = os.path.join(input_dir, filename)

        # Check if it's a file and has an image extension
        if os.path.isfile(input_path) and filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
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

                    print(f"Added logo to {filename} and saved to {output_path}")

            except Exception as e:
                print(f"Failed to process {filename}: {e}")

if __name__ == "__main__":
    # Example usage
    INPUT_DIR = "input_images"          # Replace with your input directory
    OUTPUT_DIR = "output_images"        # Replace with your output directory
    LOGO_PATH = "logo.png"              # Replace with your logo path
    POSITION = "bottom-right"           # Options: bottom-right, bottom-left, top-right, top-left, center
    LOGO_SIZE_RATIO = 0.1               # Logo size relative to image size
    OPACITY = 128                        # 0-255 where 255 is fully opaque

    add_logo_to_images(
        input_dir=INPUT_DIR,
        output_dir=OUTPUT_DIR,
        logo_path=LOGO_PATH,
        position=POSITION,
        logo_size_ratio=LOGO_SIZE_RATIO,
        opacity=OPACITY
    )
