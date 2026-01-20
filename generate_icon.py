from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

def create_icon(size=256):
    # Create a new image with transparent background
    image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Define colors
    bg_color_start = (0, 122, 255)  # Tech Blue
    bg_color_end = (0, 80, 180)    # Darker Blue
    text_color = (255, 255, 255)   # White

    # Draw rounded rectangle (simulated gradient)
    padding = size // 8
    rect_coords = [padding, padding, size - padding, size - padding]
    radius = size // 4
    
    # Simple vertical gradient
    for y in range(padding, size - padding):
        ratio = (y - padding) / (size - 2 * padding)
        r = int(bg_color_start[0] * (1 - ratio) + bg_color_end[0] * ratio)
        g = int(bg_color_start[1] * (1 - ratio) + bg_color_end[1] * ratio)
        b = int(bg_color_start[2] * (1 - ratio) + bg_color_end[2] * ratio)
        
        # Draw horizontal lines, masked by rounded rect shape? 
        # Easier way: Draw solid rounded rect, then overlay? 
        # PIL doesn't support gradient fill natively easily on shapes.
        # Let's stick to a solid color with a slight shine or just solid for clarity.
        pass
    
    # Draw solid rounded rectangle
    draw.rounded_rectangle(rect_coords, radius=radius, fill=bg_color_start)
    
    # Draw "T" or "Bridge"
    # Let's draw a stylized "T"
    
    # Font handling - try to load a system font or fallback to default
    try:
        # Try Arial or Segoe UI on Windows
        font_size = int(size * 0.5)
        font = ImageFont.truetype("arial.ttf", font_size)
    except IOError:
        font = ImageFont.load_default()
    
    # Calculate text position
    text = "T"
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - (size // 16) # Slightly adjust up
    
    draw.text((x, y), text, font=font, fill=text_color)
    
    # Add a slight border
    draw.rounded_rectangle(rect_coords, radius=radius, outline=(255, 255, 255, 100), width=size//32)

    return image

if __name__ == "__main__":
    if not os.path.exists("assets"):
        os.makedirs("assets")
        
    img = create_icon(256)
    
    # Save as PNG
    png_path = os.path.join("assets", "app_icon.png")
    img.save(png_path, "PNG")
    print(f"Saved {png_path}")
    
    # Save as ICO (contain multiple sizes)
    ico_path = os.path.join("assets", "app_icon.ico")
    img.save(ico_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"Saved {ico_path}")

    # Save extension icons
    extension_dir = "trae-extension"
    if not os.path.exists(extension_dir):
        os.makedirs(extension_dir)

    for size in [16, 48, 128]:
        # Generate fresh icon for each size to ensure crisp rendering
        icon = create_icon(size)
        icon.save(os.path.join(extension_dir, f"icon{size}.png"), "PNG")
    print(f"Saved extension icons to {extension_dir}")
