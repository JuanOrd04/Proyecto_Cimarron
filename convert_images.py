import os
from PIL import Image

images = [
    'cimarron_boca_cerrada.png',
    'logo_steam.png',
    'cimarron_boca_abierta.png',
    'cimarron_pensando.png',
    'Cimarron_Pensandoo.png'
]

public_dir = os.path.join('frontend', 'public')

for img_name in images:
    try:
        png_path = os.path.join(public_dir, img_name)
        if os.path.exists(png_path):
            webp_name = img_name.rsplit('.', 1)[0] + '.webp'
            webp_path = os.path.join(public_dir, webp_name)
            
            img = Image.open(png_path)
            img.save(webp_path, 'WEBP')
            print(f"Convertido: {img_name} -> {webp_name}")
        else:
            print(f"No encontrado: {png_path}")
    except Exception as e:
        print(f"Error al convertir {img_name}: {e}")
