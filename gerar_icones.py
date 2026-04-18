"""
Gera os ícones PNG necessários para o PWA (192x192 e 512x512).
Requer Pillow: pip install Pillow
"""
import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Instalando Pillow...")
    os.system(f"{sys.executable} -m pip install Pillow")
    from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "static", "icons")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SIZES = [192, 512]
SUBTEXT = "Sistema Cadepa"

# Gradiente de cores do sistema
COLOR_START = (37, 99, 235)   # #2563eb
COLOR_END   = (79, 70, 229)   # #4f46e5
TEXT_COLOR  = (255, 255, 255)


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def gerar_icone(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fundo com gradiente horizontal (simulado linha a linha)
    radius = size // 5
    for x in range(size):
        t = x / (size - 1)
        cor = lerp_color(COLOR_START, COLOR_END, t)
        draw.line([(x, 0), (x, size)], fill=cor + (255,))

    # Máscara de borda arredondada
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([0, 0, size, size], radius=radius, fill=255)
    img.putalpha(mask)

    # Texto "SC"
    draw = ImageDraw.Draw(img)
    font_size_sc = int(size * 0.38)
    font_size_sub = int(size * 0.13)

    try:
        font_sc  = ImageFont.truetype("arialbd.ttf", font_size_sc)
        font_sub = ImageFont.truetype("arial.ttf",   font_size_sub)
    except OSError:
        font_sc  = ImageFont.load_default(size=font_size_sc)
        font_sub = ImageFont.load_default(size=font_size_sub)

    # Posiciona "SC" no centro-alto
    bbox = draw.textbbox((0, 0), "SC", font=font_sc)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - w) // 2 - bbox[0], int(size * 0.18) - bbox[1]),
              "SC", font=font_sc, fill=TEXT_COLOR)

    # Subtexto do sistema
    bbox2 = draw.textbbox((0, 0), SUBTEXT, font=font_sub)
    w2 = bbox2[2] - bbox2[0]
    draw.text(((size - w2) // 2 - bbox2[0], int(size * 0.63) - bbox2[1]),
              SUBTEXT, font=font_sub, fill=(255, 255, 255, 210))

    path = os.path.join(OUTPUT_DIR, f"icon-{size}.png")
    img.save(path, "PNG")
    print(f"  Criado: {path}")


if __name__ == "__main__":
    print("Gerando ícones PWA...")
    for s in SIZES:
        gerar_icone(s)
    print("Concluído!")
