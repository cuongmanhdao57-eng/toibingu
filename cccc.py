import tkinter as tk
from tkinter import filedialog, messagebox

from PIL import Image, ImageOps, ImageTk


root = tk.Tk()
root.title("Chuyen anh sang mau xam")
root.geometry("800x600")
root.minsize(400, 300)

status_text = tk.StringVar(value="Hay chon mot anh tu may tinh.")
image_preview = None


def open_image():
	global image_preview

	image_path = filedialog.askopenfilename(
		parent=root,
		title="Chon mot tep anh",
		filetypes=[
			("Tep hinh anh", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.gif"),
			("Tat ca tep", "*.*"),
		],
	)
	if not image_path:
		return

	try:
		with Image.open(image_path) as source_image:
			gray_image = ImageOps.grayscale(source_image)
	except (OSError, Image.DecompressionBombError) as error:
		messagebox.showerror("Loi doc anh", str(error), parent=root)
		return

	gray_image.thumbnail((1000, 700))
	image_preview = ImageTk.PhotoImage(gray_image)
	preview_label.configure(image=image_preview)
	status_text.set(f"Anh xam: {gray_image.width} x {gray_image.height}")


tk.Button(root, text="Chon anh tu may tinh", width=24, command=open_image).pack(
	padx=16, pady=(16, 8)
)
tk.Label(root, textvariable=status_text).pack(padx=16, pady=8)
preview_label = tk.Label(root)
preview_label.pack(expand=True, padx=16, pady=(8, 16))

root.mainloop()
