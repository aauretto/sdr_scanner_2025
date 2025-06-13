from PIL import Image, ImageDraw, ImageFont

fonts = [
"FreeMonoBoldOblique.ttf",
"FreeMonoBold.ttf",
"FreeMonoOblique.ttf",
"FreeMono.ttf",
"FreeSansBoldOblique.ttf",
"FreeSansBold.ttf",
"FreeSansOblique.ttf",
"FreeSans.ttf",
"FreeSerifBoldItalic.ttf",
"FreeSerifBold.ttf",
"FreeSerifItalic.ttf",
"FreeSerif.ttf",
]

# for i, fontName in enumerate(fonts):
#     # Create a blank 128x64 1-bit image (black background)
#     img = Image.new("1", (128, 64), color=0)

#     # Get drawing context
#     draw = ImageDraw.Draw(img)
#     draw.rectangle((0, 0, 127, 63), outline=1, fill=0)
#     fontFile = f"/usr/share/fonts/truetype/freefont/{fontName}"
#     font = ImageFont.truetype(fontFile, 18)
#     draw.text((5, 28), "12345.67890", fill=1, font = font)

#     # Save as .bmp
#     img.save(f"./font_test_{fontName}.bmp")
# Create a blank 128x64 1-bit image (black background)
img = Image.new("1", (128, 64), color=0)

# Get drawing context
fontName = "7-segments-display"
fontFile = f"./{fontName}.ttf"
draw = ImageDraw.Draw(img)
draw.rectangle((0, 0, 127, 63), outline=1, fill=0)
font = ImageFont.truetype(fontFile, 18)
draw.text((5, 28), "12345.67890", fill=1, font = font)

# Save as .bmp
img.save(f"./font_test_{fontName}.bmp")