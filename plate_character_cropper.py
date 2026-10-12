import os
import statistics
import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
import numpy as np
from PIL import Image, ImageTk

cv2.ocl.setUseOpenCL(False)


root = tk.Tk()
root.title("Tach ky tu bien so xe")
root.geometry("1000x760")
root.minsize(640, 480)

source_image = None
preview_photo = None
status_text = tk.StringVar(value="Chon anh chup gan bien so xe de bat dau.")
plate_detector = cv2.CascadeClassifier(
	os.path.join(cv2.data.haarcascades, "haarcascade_russian_plate_number.xml")
)


def group_into_rows(boxes):
	rows = []
	for box in sorted(boxes, key=lambda item: item[1] + item[3] / 2):
		x, y, width, height = box
		center_y = y + height / 2
		matching_row = None
		for row in rows:
			row_center = statistics.mean(item[1] + item[3] / 2 for item in row)
			row_height = statistics.mean(item[3] for item in row)
			if abs(center_y - row_center) <= max(height, row_height) * 0.45:
				matching_row = row
				break
		if matching_row is None:
			rows.append([box])
		else:
			matching_row.append(box)

	rows.sort(key=lambda row: statistics.mean(item[1] + item[3] / 2 for item in row))
	return [sorted(row, key=lambda item: item[0]) for row in rows]


def find_character_boxes(image):
	height, width = image.shape[:2]
	if min(height, width) < 12:
		return []

	gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
	gray_image = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray_image)
	gray_image = cv2.GaussianBlur(gray_image, (3, 3), 0)
	block_size = min(51, min(height, width) // 2 * 2 - 1)
	block_size = max(11, block_size if block_size % 2 else block_size - 1)
	min_char_height = max(10, round(height * 0.18))
	min_small_height = max(3, round(height * 0.04))
	max_char_width = max(12, round(width * 0.24))
	min_char_width = max(3, round(width * 0.012))
	min_area = max(20, round(width * height * 0.0004))

	best_boxes = []
	best_small_boxes = []
	for threshold_type in (cv2.THRESH_BINARY_INV, cv2.THRESH_BINARY):
		binary = cv2.adaptiveThreshold(
			gray_image,
			255,
			cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
			threshold_type,
			block_size,
			9,
		)
		contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
		boxes = []
		small_boxes = []
		for contour in contours:
			x, y, char_width, char_height = cv2.boundingRect(contour)
			area = cv2.contourArea(contour)
			aspect_ratio = char_width / max(1, char_height)
			if (
				min_small_height <= char_height <= height * 0.95
				and min_char_width <= char_width <= max_char_width
				and min_area <= area
			):
				box = (x, y, char_width, char_height)
				if char_height >= min_char_height and 0.08 <= aspect_ratio <= 1.1:
					boxes.append(box)
				elif aspect_ratio <= 3.5:
					small_boxes.append(box)
		if len(boxes) > len(best_boxes):
			best_boxes = boxes
			best_small_boxes = small_boxes

	if not best_boxes:
		return []

	median_height = statistics.median(box[3] for box in best_boxes)
	row_center = statistics.median(box[1] + box[3] / 2 for box in best_boxes)
	row_baseline = statistics.median(box[1] + box[3] for box in best_boxes)
	merged_boxes = [list(box) for box in best_boxes]
	punctuation_boxes = []
	merge_distance = max(2, round(median_height * 0.12))

	for x, y, char_width, char_height in best_small_boxes:
		aspect_ratio = char_width / max(1, char_height)
		box_center_y = y + char_height / 2
		box_bottom = y + char_height
		is_period = (
			0.07 * median_height <= char_height <= 0.22 * median_height
			and aspect_ratio <= 1.7
			and abs(box_bottom - row_baseline) <= 0.18 * median_height
		)
		if is_period:
			punctuation_boxes.append((x, y, char_width, char_height))
			continue

		near_character = False
		for character in merged_boxes:
			char_x, char_y, main_width, main_height = character
			horizontally_close = (
				x <= char_x + main_width + merge_distance
				and x + char_width >= char_x - merge_distance
			)
			vertically_close = (
				y <= char_y + main_height + merge_distance
				and y + char_height >= char_y - merge_distance
			)
			if horizontally_close and vertically_close:
				left = min(char_x, x)
				top = min(char_y, y)
				right = max(char_x + main_width, x + char_width)
				bottom = max(char_y + main_height, y + char_height)
				character[:] = [left, top, right - left, bottom - top]
				near_character = True
				break
		if near_character:
			continue

		is_hyphen = (
			0.08 * median_height <= char_height <= 0.22 * median_height
			and 1.2 <= aspect_ratio <= 3.2
			and abs(box_center_y - row_center) <= 0.17 * median_height
		)
		if is_hyphen:
			punctuation_boxes.append((x, y, char_width, char_height))

	all_boxes = [tuple(box) for box in merged_boxes] + punctuation_boxes
	rows = group_into_rows(all_boxes)
	return [box for row in rows for box in row]


def find_plate_regions(image):
	height, width = image.shape[:2]
	scale = min(1.0, 1200 / max(height, width))
	if scale < 1.0:
		search_image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
	else:
		search_image = image

	gray_image = cv2.equalizeHist(cv2.cvtColor(search_image, cv2.COLOR_BGR2GRAY))
	regions = plate_detector.detectMultiScale(
		gray_image,
		scaleFactor=1.05,
		minNeighbors=3,
		minSize=(max(40, round(search_image.shape[1] * 0.2)), max(15, round(search_image.shape[0] * 0.08))),
	)
	candidates = []
	for x, y, region_width, region_height in regions:
		aspect_ratio = region_width / max(1, region_height)
		if 1.8 <= aspect_ratio <= 7.5 and region_width >= search_image.shape[1] * 0.2:
			candidates.append(
				(
					round(x / scale),
					round(y / scale),
					round(region_width / scale),
					round(region_height / scale),
				)
			)

	height, width = gray_image.shape[:2]
	kernel = cv2.getStructuringElement(
		cv2.MORPH_RECT,
		(max(9, width // 80), max(5, height // 60)),
	)
	otsu_level = cv2.threshold(
		gray_image, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
	)[0]
	for threshold in {90, 120, 150, round(otsu_level)}:
		binary = cv2.threshold(gray_image, threshold, 255, cv2.THRESH_BINARY_INV)[1]
		closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
		contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
		for contour in contours:
			x, y, region_width, region_height = cv2.boundingRect(contour)
			aspect_ratio = region_width / max(1, region_height)
			if (
				1.8 <= aspect_ratio <= 7.5
				and region_width >= width * 0.2
				and region_height >= height * 0.08
				and cv2.contourArea(contour) >= width * height * 0.03
			):
				candidates.append(
					(
						round(x / scale),
						round(y / scale),
						round(region_width / scale),
						round(region_height / scale),
					)
				)
	return sorted(candidates, key=lambda box: box[2] * box[3], reverse=True)


def read_image(image_path):
	try:
		image_data = np.fromfile(image_path, dtype=np.uint8)
		if image_data.size == 0:
			return None
		return cv2.imdecode(image_data, cv2.IMREAD_COLOR)
	except OSError:
		return None


def choose_image():
	global source_image

	image_path = filedialog.askopenfilename(
		parent=root,
		title="Chon anh bien so xe",
		filetypes=[
			("Image files", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp"),
			("All files", "*.*"),
		],
	)
	if not image_path:
		return

	source_image = read_image(image_path)
	if source_image is None:
		messagebox.showerror("Loi doc anh", "Khong the doc tep anh da chon.", parent=root)
		return

	status_text.set("Da mo anh. Dang tim bien so va tach ky tu...")
	show_result(source_image)
	root.after(50, process_image, image_path, source_image)


def process_image(image_path, image):
	image_height, image_width = image.shape[:2]
	full_image_region = (0, 0, image_width, image_height)
	regions = find_plate_regions(image)
	if full_image_region not in regions:
		regions.append(full_image_region)

	best_region = None
	boxes = []
	for region in regions:
		x, y, region_width, region_height = region
		plate_image = image[y:y + region_height, x:x + region_width]
		candidate_boxes = find_character_boxes(plate_image)
		if len(candidate_boxes) > len(boxes):
			best_region = region
			boxes = candidate_boxes

	if not boxes or best_region is None:
		status_text.set("Khong tim thay ky tu. Hay crop sat bien so, ro net va chinh dien.")
		show_result(image)
		return

	output_directory = os.path.join(os.path.dirname(image_path), "plate_characters")
	os.makedirs(output_directory, exist_ok=True)
	annotated_image = image.copy()
	region_x, region_y, region_width, region_height = best_region
	padding = max(2, round(min(region_width, region_height) * 0.008))
	saved_count = 0

	for index, (char_x, char_y, width, height) in enumerate(boxes):
		x = region_x + char_x
		y = region_y + char_y
		left = max(0, x - padding)
		top = max(0, y - padding)
		right = min(image_width, x + width + padding)
		bottom = min(image_height, y + height + padding)
		character_crop = image[top:bottom, left:right]
		encoded_image = cv2.imencode(".png", character_crop)[1]
		encoded_image.tofile(os.path.join(output_directory, f"{index}.png"))
		saved_count += 1
		cv2.rectangle(annotated_image, (x, y), (x + width, y + height), (0, 255, 0), 2)
		cv2.putText(
			annotated_image,
			str(index),
			(x, max(18, y - 5)),
			cv2.FONT_HERSHEY_SIMPLEX,
			0.6,
			(0, 0, 255),
			2,
		)

	print(f"So ky tu da tach: {saved_count}")
	print(f"Thu muc luu: {output_directory}")
	status_text.set(f"Da tach {saved_count} ky tu. Anh duoc luu tai: {output_directory}")
	show_result(annotated_image)


def show_result(image):
	global preview_photo

	max_width = max(320, root.winfo_width() - 40)
	max_height = max(240, root.winfo_height() - 150)
	rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
	display_image = Image.fromarray(rgb_image)
	display_image.thumbnail((max_width, max_height))
	preview_photo = ImageTk.PhotoImage(display_image)
	preview_label.configure(image=preview_photo, text="")


tk.Button(root, text="Chon anh bien so", width=22, command=choose_image).pack(pady=(14, 8))
tk.Label(root, textvariable=status_text, wraplength=940).pack(pady=6)
preview_label = tk.Label(root, text="Anh ket qua se hien thi o day")
preview_label.pack(expand=True, fill="both", padx=16, pady=(4, 14))

root.mainloop()