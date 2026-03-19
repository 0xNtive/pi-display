from inky import InkyPHAT
from PIL import Image
d = InkyPHAT("black")
img = Image.new("P", (212, 104), 1)
img.putpalette([0, 0, 0, 255, 255, 255] + [0, 0, 0] * 254)
d.set_image(img)
d.show()
print("sent to display")
