from PIL import Image
img = Image.open("Image1.png")
img.save("icon1.ico", format="ICO", sizes=[(200, 200)])
