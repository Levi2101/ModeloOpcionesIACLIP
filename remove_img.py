from rembg import remove
from PIL import Image

# Para imagen local:
input_image = Image.open('image.png')
output_image = remove(input_image)
output_image.save('resultado_prueba.png') # Siempre guardar en formato PNG para mantener transparencia

print("Prueba finalizada.")
