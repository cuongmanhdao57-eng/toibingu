import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageTk


class ImageViewer:
	"""Giao diện chọn, đọc và hiển thị ảnh bằng OpenCV và Pillow."""

	def __init__(self, root):
		self.root = root
		self.root.title("Trình xem ảnh OpenCV + Pillow")
		self.root.geometry("900x650")
		self.root.minsize(500, 400)
		self.photos = []

		toolbar = tk.Frame(root, padx=10, pady=10)
		toolbar.pack(fill=tk.X)

		select_button = tk.Button(
			toolbar,
			text="Chọn ảnh",
			command=self.select_image,
			padx=12,
			pady=6,
		)
		select_button.pack(side=tk.LEFT)

		select_second_button = tk.Button(
			toolbar,
			text="Chọn ảnh 2",
			command=self.select_second_image,
			padx=12,
			pady=6,
		)
		select_second_button.pack(side=tk.LEFT, padx=8)

		save_button = tk.Button(
			toolbar,
			text="Lưu mỗi ảnh một lần",
			command=self.save_in_formats,
			padx=12,
			pady=6,
		)
		save_button.pack(side=tk.LEFT, padx=8)

		show_button = tk.Button(
			toolbar,
			text="Hiển thị hệ màu",
			command=self.show_color_spaces,
			padx=12,
			pady=6,
		)
		show_button.pack(side=tk.LEFT, padx=8)

		brightness_button = tk.Button(
			toolbar,
			text="Tăng sáng +50",
			command=self.enhance_brightness,
			padx=12,
			pady=6,
		)
		brightness_button.pack(side=tk.LEFT, padx=8)

		status_bar = tk.Frame(root, padx=10, pady=4)
		status_bar.pack(fill=tk.X)
		self.status = tk.Label(status_bar, text="Chưa chọn ảnh", anchor=tk.W)
		self.status.pack(fill=tk.X)

		self.page_labels = {}
		self.page_images = {}
		self.notebook = ttk.Notebook(root)
		self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
		self.create_page("Hệ màu", "color", ("Ảnh màu", "Grayscale", "HSV"))
		self.create_page("Bitwise AND", "bitwise", ("Ảnh 1", "Ảnh 2", "Kết quả AND"))
		self.create_page("Tăng sáng", "brightness", ("Ảnh gốc", "Tăng sáng +50"))
		self.create_page(
			"Biến đổi hình học",
			"geometry",
			("Xoay 90 độ", "Dịch phải 50 px", "Thu phóng 1.5x"),
		)

		root.bind("<Configure>", self.refresh_image)
		root.protocol("WM_DELETE_WINDOW", self.close)

	def create_page(self, page_title, page_key, image_titles):
		page = tk.Frame(self.notebook, padx=10, pady=10)
		self.notebook.add(page, text=page_title)
		for column in range(len(image_titles)):
			page.grid_columnconfigure(column, weight=1, uniform=page_key)
		page.grid_rowconfigure(1, weight=1)

		labels = []
		for column, title in enumerate(image_titles):
			title_label = tk.Label(page, text=title, font=("Segoe UI", 11, "bold"))
			title_label.grid(row=0, column=column, padx=5, pady=(0, 5))
			image_label = tk.Label(page, text="Chưa có ảnh", bg="#eeeeee", anchor=tk.CENTER)
			image_label.grid(row=1, column=column, sticky="nsew", padx=5)
			labels.append(image_label)

		self.page_labels[page_key] = labels
		self.page_images[page_key] = []

	def select_image(self):
		file_path = filedialog.askopenfilename(
			title="Chọn ảnh",
			filetypes=[
				("Tệp ảnh", "*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff"),
				("Tất cả tệp", "*.*"),
			],
		)
		if not file_path:
			return

		image = cv2.imread(file_path, cv2.IMREAD_COLOR)
		if image is None:
			messagebox.showerror("Không thể mở ảnh", "OpenCV không đọc được tệp ảnh đã chọn.")
			return

		self.image = image
		self.image_path = file_path
		self.image_two = None
		self.image_two_path = None
		self.status.config(text=f"Ảnh 1: {os.path.basename(file_path)} | Chưa chọn ảnh 2")
		self.show_color_spaces()

	def select_second_image(self):
		if not hasattr(self, "image"):
			messagebox.showinfo("Chưa có ảnh 1", "Hãy chọn ảnh thứ nhất trước.")
			return

		file_path = filedialog.askopenfilename(
			title="Chọn ảnh thứ hai",
			filetypes=[
				("Tệp ảnh", "*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff"),
				("Tất cả tệp", "*.*"),
			],
		)
		if not file_path:
			return

		image = cv2.imread(file_path, cv2.IMREAD_COLOR)
		if image is None:
			messagebox.showerror("Không thể mở ảnh", "OpenCV không đọc được tệp ảnh thứ hai.")
			return

		self.image_two = image
		self.image_two_path = file_path
		self.status.config(
			text=(
				f"Ảnh 1: {os.path.basename(self.image_path)} | "
				f"Ảnh 2: {os.path.basename(file_path)}"
			)
		)
		self.show_color_spaces()

	def save_in_formats(self):
		if not hasattr(self, "image"):
			messagebox.showinfo("Chưa có ảnh", "Hãy chọn một ảnh trước khi lưu.")
			return
		if not self.page_images["color"]:
			self.show_color_spaces()

		output_directory = filedialog.askdirectory(title="Chọn thư mục lưu ảnh")
		if not output_directory:
			return

		base_name = os.path.splitext(os.path.basename(self.image_path))[0]
		saved_files = []
		images_to_save = [
			("mau", self.page_images["color"][0]),
			("grayscale", self.page_images["color"][1]),
			("hsv", self.page_images["color"][2]),
			("bitwise_and", self.page_images["bitwise"][2]),
			("tang_sang", self.page_images["brightness"][1]),
			("xoay_90", self.page_images["geometry"][0]),
			("dich_phai_50", self.page_images["geometry"][1]),
			("thu_phong_1_5x", self.page_images["geometry"][2]),
		]
		for image_name, image in images_to_save:
			if image is None:
				continue

			image_to_save = image
			if len(image.shape) == 3:
				image_to_save = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
			output_name = f"{base_name}_{image_name}.png"
			output_path = os.path.join(output_directory, output_name)
			encoded_image = cv2.imencode(".png", image_to_save)[1]
			encoded_image.tofile(output_path)
			saved_files.append(output_path)

		messagebox.showinfo(
			"Lưu ảnh thành công",
			"Đã lưu mỗi ảnh một tệp PNG:\n" + "\n".join(saved_files),
		)

	def show_color_spaces(self):
		if not hasattr(self, "image"):
			messagebox.showinfo("Chưa có ảnh", "Hãy chọn một ảnh trước.")
			return

		rgb_image = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
		self.page_images["color"] = [
			rgb_image,
			cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY),
			cv2.cvtColor(self.image, cv2.COLOR_BGR2HSV),
		]
		self.page_images["bitwise"] = [rgb_image, None, None]
		if self.image_two is not None:
			height, width = self.image.shape[:2]
			second_image = cv2.resize(self.image_two, (width, height), interpolation=cv2.INTER_AREA)
			and_image = cv2.bitwise_and(self.image, second_image)
			self.page_images["bitwise"] = [
				rgb_image,
				cv2.cvtColor(second_image, cv2.COLOR_BGR2RGB),
				cv2.cvtColor(and_image, cv2.COLOR_BGR2RGB),
			]

		brightness_offset = (50, 50, 50)
		bright_image = cv2.add(self.image, brightness_offset)
		self.page_images["brightness"] = [
			rgb_image,
			cv2.cvtColor(bright_image, cv2.COLOR_BGR2RGB),
		]

		height, width = self.image.shape[:2]
		rotation_image = cv2.rotate(self.image, cv2.ROTATE_90_CLOCKWISE)
		translation_matrix = cv2.getRotationMatrix2D((0, 0), 0, 1)
		translation_matrix[0, 2] = 50
		translation_image = cv2.warpAffine(self.image, translation_matrix, (width, height))
		zoom_image = cv2.resize(self.image, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_LINEAR)
		self.page_images["geometry"] = [
			cv2.cvtColor(rotation_image, cv2.COLOR_BGR2RGB),
			cv2.cvtColor(translation_image, cv2.COLOR_BGR2RGB),
			cv2.cvtColor(zoom_image, cv2.COLOR_BGR2RGB),
		]
		self.refresh_image()
		self.notebook.select(0)

	def enhance_brightness(self):
		if not hasattr(self, "image"):
			messagebox.showinfo("Chưa có ảnh", "Hãy chọn một ảnh trước.")
			return

		self.show_color_spaces()
		self.notebook.select(2)

	def close(self):
		cv2.destroyAllWindows()
		self.root.destroy()

	def refresh_image(self, _event=None):
		if not self.page_images["color"]:
			return

		self.photos = []
		for page_key, image_labels in self.page_labels.items():
			for image_label, image in zip(image_labels, self.page_images[page_key]):
				if image is None:
					placeholder = "Chưa chọn ảnh 2" if page_key == "bitwise" else "Chưa có kết quả"
					image_label.config(image="", text=placeholder)
					continue

				available_width = max(image_label.winfo_width() - 20, 100)
				available_height = max(image_label.winfo_height() - 20, 100)
				height, width = image.shape[:2]
				scale = min(available_width / width, available_height / height, 1)
				display_size = (max(1, int(width * scale)), max(1, int(height * scale)))

				resized = cv2.resize(image, display_size, interpolation=cv2.INTER_AREA)
				pil_image = Image.fromarray(resized)
				photo = ImageTk.PhotoImage(pil_image)
				self.photos.append(photo)
				image_label.config(image=photo, text="")


if __name__ == "__main__":
	window = tk.Tk()
	ImageViewer(window)
	window.mainloop()