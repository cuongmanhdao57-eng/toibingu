import os
import tkinter as tk
from tkinter import filedialog, messagebox

import cv2
from PIL import Image, ImageTk


root = tk.Tk()
root.title("Face detector")
root.geometry("1050x820")
root.minsize(720, 560)
root.resizable(True, True)

haar_directory = cv2.data.haarcascades
frontal_detector = cv2.CascadeClassifier(
	os.path.join(haar_directory, "haarcascade_frontalface_alt2.xml")
)
profile_detector = cv2.CascadeClassifier(
	os.path.join(haar_directory, "haarcascade_profileface.xml")
)
capture = None
preview_active = False
current_frame = None
current_faces = []
source_directory = None
source_kind = "webcam"
frame_delay = 15
video_fps = 30
video_duration = 0.0
video_position = 0.0
playback_speed = 1.0
video_paused = False
timeline_dragging = False
timeline = None
play_button = None
playback_widgets = []
speed_text = tk.StringVar(value="1x")
time_text = tk.StringVar(value="00:00 / 00:00")
status_text = tk.StringVar(value="Choose an image/video file or start the webcam.")
display_image = None
preview_label = None


def detect_and_show(frame):
	global current_frame, current_faces, display_image

	current_frame = frame.copy()
	frame_height, frame_width = frame.shape[:2]
	detection_scale = min(1.0, 900 / frame_width)
	if detection_scale < 1.0:
		detection_frame = cv2.resize(
			frame,
			None,
			fx=detection_scale,
			fy=detection_scale,
			interpolation=cv2.INTER_AREA,
		)
	else:
		detection_frame = frame

	gray_frame = cv2.equalizeHist(cv2.cvtColor(detection_frame, cv2.COLOR_BGR2GRAY))
	frontal_faces = frontal_detector.detectMultiScale(
		gray_frame, scaleFactor=1.08, minNeighbors=6, minSize=(30, 30)
	)
	profile_faces = list(
		profile_detector.detectMultiScale(
			gray_frame, scaleFactor=1.08, minNeighbors=5, minSize=(30, 30)
		)
	)
	flipped_faces = profile_detector.detectMultiScale(
		cv2.flip(gray_frame, 1), scaleFactor=1.08, minNeighbors=5, minSize=(30, 30)
	)
	profile_faces.extend(
		(detection_frame.shape[1] - x - width, y, width, height)
		for x, y, width, height in flipped_faces
	)

	if detection_scale < 1.0:
		frontal_faces = [tuple(round(value / detection_scale) for value in face) for face in frontal_faces]
		profile_faces = [tuple(round(value / detection_scale) for value in face) for face in profile_faces]

	current_faces = []
	for face in list(frontal_faces) + profile_faces:
		x, y, width, height = face
		face_area = width * height
		is_duplicate = False
		for other_x, other_y, other_width, other_height in current_faces:
			left = max(x, other_x)
			top = max(y, other_y)
			right = min(x + width, other_x + other_width)
			bottom = min(y + height, other_y + other_height)
			intersection = max(0, right - left) * max(0, bottom - top)
			other_area = other_width * other_height
			if intersection / max(1, face_area + other_area - intersection) > 0.35:
				is_duplicate = True
				break
		if not is_duplicate:
			current_faces.append((x, y, width, height))

	display_frame = frame.copy()
	for x, y, width, height in current_faces:
		cv2.rectangle(display_frame, (x, y), (x + width, y + height), (0, 255, 0), 2)

	cv2.putText(
		display_frame,
		f"Faces: {len(current_faces)}",
		(20, 35),
		cv2.FONT_HERSHEY_SIMPLEX,
		1,
		(0, 255, 0),
		2,
	)
	rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
	image = Image.fromarray(rgb_frame)
	image.thumbnail((1000, 560))
	display_image = ImageTk.PhotoImage(image)
	preview_label.configure(image=display_image, text="")
	status_text.set(f"Detected faces: {len(current_faces)}. Press S to save crops.")


def stop_preview():
	global capture, current_faces, current_frame, display_image, preview_active, video_duration
	global video_paused, video_position

	preview_active = False
	video_paused = False
	if capture is not None:
		capture.release()
		capture = None
	current_frame = None
	current_faces = []
	video_position = 0.0
	video_duration = 0.0
	set_video_controls(False)
	update_timeline()
	if preview_label is not None:
		display_image = None
		preview_label.configure(image="", text="Choose an image/video or start the webcam")
	if play_button is not None:
		play_button.configure(text="Pause")


def format_time(seconds):
	seconds = max(0, int(seconds))
	hours, remainder = divmod(seconds, 3600)
	minutes, seconds = divmod(remainder, 60)
	if hours:
		return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
	return f"{minutes:02d}:{seconds:02d}"


def set_video_controls(enabled):
	state = tk.NORMAL if enabled else tk.DISABLED
	for widget in playback_widgets:
		widget.configure(state=state)


def update_timeline():
	if timeline is None:
		return

	timeline.configure(to=max(video_duration, 0.1))
	if not timeline_dragging:
		timeline.set(min(video_position, video_duration))
	time_text.set(f"{format_time(video_position)} / {format_time(video_duration)}")


def preview_timeline_value(value):
	if source_kind == "video":
		time_text.set(f"{format_time(float(value))} / {format_time(video_duration)}")


def start_timeline_drag(event):
	global timeline_dragging
	timeline_dragging = True


def finish_timeline_drag(event):
	global timeline_dragging
	timeline_dragging = False
	seek_video(timeline.get())


def seek_video(seconds):
	global video_position

	if source_kind != "video" or capture is None:
		return

	video_position = min(max(0.0, float(seconds)), video_duration)
	capture.set(cv2.CAP_PROP_POS_MSEC, video_position * 1000)
	success, frame = capture.read()
	if success:
		detect_and_show(frame)
		position_ms = capture.get(cv2.CAP_PROP_POS_MSEC)
		if position_ms > 0:
			video_position = min(position_ms / 1000, video_duration)
	update_timeline()


def skip_video(seconds):
	seek_video(video_position + seconds)


def toggle_video_playback():
	global video_paused

	if source_kind != "video":
		return
	video_paused = not video_paused
	play_button.configure(text="Play" if video_paused else "Pause")


def set_playback_speed(value):
	global frame_delay, playback_speed

	playback_speed = float(value.rstrip("x"))
	frame_delay = max(1, round(1000 / (video_fps * playback_speed)))


def save_faces(event=None):
	if current_frame is None:
		return
	if len(current_faces) == 0:
		status_text.set("No faces to save.")
		return

	output_directory = os.path.join(source_directory or os.getcwd(), "faces")
	os.makedirs(output_directory, exist_ok=True)
	saved_count = 0
	for index, (x, y, width, height) in enumerate(current_faces):
		face_image = current_frame[y:y + height, x:x + width]
		output_path = os.path.join(output_directory, f"{index}.png")
		if cv2.imwrite(output_path, face_image):
			saved_count += 1

	status_text.set(f"Saved {saved_count} face(s) to: {output_directory}")


def poll_preview():
	global video_position

	if not preview_active:
		return

	if capture is not None and (source_kind != "video" or not video_paused):
		success, frame = capture.read()
		if not success:
			ended_video = source_kind == "video"
			stop_preview()
			status_text.set("Video finished." if ended_video else "Could not read a frame from the webcam.")
			return
		detect_and_show(frame)
		if source_kind == "video":
			position_ms = capture.get(cv2.CAP_PROP_POS_MSEC)
			if position_ms > 0:
				video_position = min(position_ms / 1000, video_duration)
			if not timeline_dragging:
				update_timeline()

	root.after(frame_delay, poll_preview)


def open_media():
	global capture, frame_delay, source_directory, source_kind, preview_active
	global video_duration, video_fps, video_paused, video_position

	media_path = filedialog.askopenfilename(
		parent=root,
		title="Choose an image or video",
		filetypes=[
			("Image and video files", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.mp4 *.avi *.mov *.mkv *.wmv *.m4v *.webm *.mpg *.mpeg"),
			("All files", "*.*"),
		],
	)
	if not media_path:
		return

	stop_preview()
	source_directory = os.path.dirname(media_path)
	extension = os.path.splitext(media_path)[1].lower()
	video_extensions = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".m4v", ".webm", ".mpg", ".mpeg"}

	if extension in video_extensions:
		source_kind = "video"
		capture = cv2.VideoCapture(media_path)
		if not capture.isOpened():
			capture.release()
			capture = None
			messagebox.showerror("Video error", "Could not open the selected video.", parent=root)
			return
		fps = capture.get(cv2.CAP_PROP_FPS)
		video_fps = fps if fps > 0 else 30
		frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
		video_duration = frame_count / video_fps if frame_count > 0 else 0
		video_position = 0.0
		video_paused = False
		frame_delay = max(1, round(1000 / (video_fps * playback_speed)))
		play_button.configure(text="Pause")
		set_video_controls(True)
		update_timeline()
	else:
		source_kind = "image"
		set_video_controls(False)
		frame = cv2.imread(media_path)
		if frame is None:
			messagebox.showerror("Image error", "Could not read the selected image.", parent=root)
			return
		frame_delay = 15
		preview_active = True
		detect_and_show(frame)
		root.after(frame_delay, poll_preview)
		return

	preview_active = True
	root.after(0, poll_preview)


def start_webcam():
	global capture, frame_delay, source_directory, source_kind, preview_active

	stop_preview()
	source_directory = None
	source_kind = "webcam"
	frame_delay = 15
	set_video_controls(False)
	capture = cv2.VideoCapture(0)
	if not capture.isOpened():
		capture.release()
		capture = None
		messagebox.showerror("Webcam error", "Could not open the webcam.", parent=root)
		return

	preview_active = True
	root.after(0, poll_preview)


def close_application():
	stop_preview()
	root.destroy()


def handle_preview_key(event):
	key = event.keysym.lower()
	if key == "s":
		save_faces()
	elif key in ("q", "escape"):
		stop_preview()
		status_text.set("Preview closed.")


source_row = tk.Frame(root)
source_row.pack(pady=(10, 4))
tk.Button(source_row, text="Choose image/video", width=22, command=open_media).pack(
	side=tk.LEFT, padx=6
)
tk.Button(source_row, text="Start webcam", width=22, command=start_webcam).pack(
	side=tk.LEFT, padx=6
)
preview_label = tk.Label(
	root,
	text="Choose an image/video or start the webcam",
	background="#202020",
	foreground="white",
)
preview_label.pack(expand=True, fill="both", padx=12, pady=8)
time_label = tk.Label(root, textvariable=time_text)
time_label.pack(padx=16, pady=(8, 0))
timeline = tk.Scale(
	root,
	from_=0,
	to=1,
	orient=tk.HORIZONTAL,
	showvalue=False,
	length=820,
	resolution=0.1,
	command=preview_timeline_value,
)
timeline.pack(padx=16, fill="x")
timeline.bind("<ButtonPress-1>", start_timeline_drag)
timeline.bind("<ButtonRelease-1>", finish_timeline_drag)

playback_row = tk.Frame(root)
playback_row.pack(pady=4)
rewind_button = tk.Button(playback_row, text="-5 s", command=lambda: skip_video(-5))
rewind_button.pack(side=tk.LEFT, padx=4)
play_button = tk.Button(playback_row, text="Pause", command=toggle_video_playback)
play_button.pack(side=tk.LEFT, padx=4)
forward_button = tk.Button(playback_row, text="+5 s", command=lambda: skip_video(5))
forward_button.pack(side=tk.LEFT, padx=4)
speed_menu = tk.OptionMenu(
	playback_row,
	speed_text,
	"0.25x",
	"0.5x",
	"1x",
	"1.5x",
	"2x",
	command=set_playback_speed,
)
speed_menu.pack(side=tk.LEFT, padx=8)
playback_widgets = [timeline, rewind_button, play_button, forward_button, speed_menu]
set_video_controls(False)
tk.Label(root, textvariable=status_text, wraplength=360, justify="left").pack(
	padx=16, pady=(8, 16)
)

root.bind_all("<KeyPress>", handle_preview_key)
root.protocol("WM_DELETE_WINDOW", close_application)
root.mainloop()