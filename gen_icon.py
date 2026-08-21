from PIL import Image, ImageDraw
img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.ellipse([16, 16, 240, 240], fill='#2196F3', outline='#FFFFFF', width=4)
draw.text((80, 55), 'D', fill='#FFFFFF')
img.save('app.ico', format='ICO', sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])
print('DONE: app.ico created')
