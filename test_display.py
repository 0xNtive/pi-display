from inky.auto import auto
from PIL import Image, ImageDraw

d = auto()
d.set_border(d.BLACK)

img = Image.new("P", (d.width, d.height), d.WHITE)
draw = ImageDraw.Draw(img)
draw.text((20, 40), "HELLO PI", fill=d.BLACK)

d.set_image(img)
d.show()
print("resolution:", d.width, "x", d.height)
print("sent to display - wait 15 seconds for refresh")
