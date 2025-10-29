# ai_module.py
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageDraw
import os

def analyze_image(image_path, max_colors=5):
    """Return simple dominant colors (hex) and placeholder objects list."""
    img = Image.open(image_path).convert('RGBA').resize((200,200))
    palette_img = img.convert('P', palette=Image.ADAPTIVE, colors=max_colors)
    palette = palette_img.getpalette()
    color_counts = sorted(palette_img.getcolors(), reverse=True)
    colors = []
    for count, idx in color_counts[:max_colors]:
        r,g,b = palette[idx*3:idx*3+3]
        colors.append('#%02x%02x%02x' % (r,g,b))
    # placeholder object detection
    objects = ['sofa','table','lamp'] if img.size[0] > img.size[1] else ['bed','wardrobe','lamp']
    return {'colors': colors, 'objects': objects}

def generate_design(original_path, style='Aesthetic', output_dir='static/generated'):
    """Simple stylization: color overlay, contrast/blur tweaks. Returns output path."""
    os.makedirs(output_dir, exist_ok=True)
    base = Image.open(original_path).convert('RGBA')
    w,h = base.size

    # pick overlay color by style
    style_map = {
        'Aesthetic': (236, 200, 160, 48),
        'Modern': (64, 160, 185, 48),
        'Cozy': (210, 150, 120, 80),
        'Vintage': (120, 90, 60, 70),
        'Minimalist': (240,240,240,40)
    }
    overlay_color = style_map.get(style, (200,160,120,48))

    # gentle resize for speed
    if max(w,h) > 1600:
        base = base.resize((int(w*0.6), int(h*0.6)), Image.LANCZOS)
    # enhance
    base = ImageEnhance.Color(base).enhance(1.05)
    base = ImageEnhance.Contrast(base).enhance(1.07)

    # overlay
    overlay = Image.new('RGBA', base.size, overlay_color)
    out = Image.alpha_composite(base, overlay)

    # style-specific post effects
    if style == 'Aesthetic':
        out = out.filter(ImageFilter.SMOOTH_MORE)
    elif style == 'Modern':
        out = ImageOps.autocontrast(out)
        out = out.filter(ImageFilter.SHARPEN)
    elif style == 'Cozy':
        out = out.filter(ImageFilter.GaussianBlur(radius=0.8))
    elif style == 'Vintage':
        out = ImageOps.colorize(ImageOps.grayscale(out), black="#2b1b12", white="#e7d8c8")

    # add subtle vignette
    vign = Image.new('L', out.size, 0)
    draw = ImageDraw.Draw(vign)
    draw.ellipse((-int(out.size[0]*0.3), -int(out.size[1]*0.3),
                  int(out.size[0]*1.3), int(out.size[1]*1.3)), fill=255)
    vign = vign.filter(ImageFilter.GaussianBlur(radius=int(min(out.size)/4)))
    out = Image.composite(out, Image.new('RGBA', out.size, (8,8,10,255)), vign.convert('L').point(lambda p: 255 - p))

    # save
    name = os.path.splitext(os.path.basename(original_path))[0]
    out_path = os.path.join(output_dir, f"{name}_{style.lower()}.jpg")
    out.convert('RGB').save(out_path, quality=90)
    return out_path
