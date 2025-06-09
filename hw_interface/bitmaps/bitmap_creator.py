from PIL import Image, ImageDraw, ImageFont

# Create a blank 128x64 1-bit image (black background)
img = Image.new("1", (128, 64), color=0)

# Get drawing context
draw = ImageDraw.Draw(img)
draw.rectangle((0, 0, 127, 63), outline=1, fill=0)
# fontFile = "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
# font = ImageFont.truetype(fontFile, 12)
# draw.text((35, 28), "Setting Up...", font = font, fill=1)
draw.text((35, 28), "Setting Up...", fill=1)

# Save as .bmp
img.save("./bitmaps/boot_splash.bmp")