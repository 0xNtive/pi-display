from inky.phat import InkyPHAT
from PIL import Image, ImageDraw, ImageFont

d = InkyPHAT("black")
d.set_border(d.BLACK)

img = Image.new("P", (d.width, d.height), d.WHITE)
draw = ImageDraw.Draw(img)
draw.rectangle((0, 0, d.width, d.height), fill=d.WHITE)
draw.text((20, 40), "HELLO PI", fill=d.BLACK)

d.set_image(img)
d.show()
print("width:", d.width, "height:", d.height)
print("sent to display - wait 15 seconds for refresh")
