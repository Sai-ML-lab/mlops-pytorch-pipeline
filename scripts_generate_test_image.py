from pathlib import Path

from PIL import Image, ImageDraw

img = Image.new("RGB", (256, 256), "lightgray")
d = ImageDraw.Draw(img)
d.rounded_rectangle((28, 28, 228, 228), radius=16, fill="white", outline="gray", width=4)
d.ellipse((70, 94, 106, 130), fill="gray")
d.ellipse((150, 94, 186, 130), fill="gray")
d.arc((76, 120, 180, 190), start=20, end=160, fill="gray", width=6)
Path("test_image.png").unlink(missing_ok=True)
img.save("test_image.png")
