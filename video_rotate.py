import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

import imageio.v2 as imageio
from PIL import Image, ImageTk


root = tk.Tk()
root.title("Video rotator")
root.geometry("900x700")
root.minsize(400, 300)

video_fps = 30
rotation_degrees = 0
video_running = False
image_preview = None
current_frame = None
decode_stop = threading.Event()
frame_queue = queue.Queue(maxsize=1)
event_queue = queue.Queue()
status_text = tk.StringVar(value="Choose a video file to start.")


def stop_video():
	global video_running

	video_running = False
	decode_stop.set()


def render_current_frame():
	global image_preview

	if current_frame is None:
		return

	image = Image.fromarray(current_frame)
	max_size = (650, 1000) if rotation_degrees % 180 else (1000, 650)
	image.thumbnail(max_size)
	if rotation_degrees:
		image = image.rotate(rotation_degrees, expand=True)
	image_preview = ImageTk.PhotoImage(image)
	preview_label.configure(image=image_preview)


def decode_video(video_path, stop_event, frames, events):
	reader = None
	try:
		reader = imageio.get_reader(video_path, format="ffmpeg")
		fps = reader.get_meta_data().get("fps", 30) or 30
		fps = fps if fps > 0 else 30
		events.put(("fps", fps))

		while not stop_event.is_set():
			frame_started = time.perf_counter()
			try:
				frame = reader.get_next_data()
			except (IndexError, StopIteration):
				events.put(("finished", None))
				return

			while not stop_event.is_set():
				try:
					frames.put(frame, timeout=0.05)
					break
				except queue.Full:
					continue

			frame_time = time.perf_counter() - frame_started
			stop_event.wait(max(0, 1 / fps - frame_time))
	except Exception as error:
		events.put(("error", str(error)))
	finally:
		if reader is not None:
			reader.close()


def poll_video():
	global current_frame, video_fps, video_running

	while True:
		try:
			event, value = event_queue.get_nowait()
		except queue.Empty:
			break

		if event == "fps":
			video_fps = value
		elif event == "finished":
			video_running = False
			status_text.set("Video finished.")
		elif event == "error":
			video_running = False
			status_text.set("Could not read video.")
			messagebox.showerror("Video error", value, parent=root)

	try:
		current_frame = frame_queue.get_nowait()
		render_current_frame()
	except queue.Empty:
		pass

	root.after(10, poll_video)


def open_video():
	global decode_stop, event_queue, frame_queue, rotation_degrees, video_running

	video_path = filedialog.askopenfilename(
		parent=root,
		title="Select a video",
		filetypes=[
			("Video files", "*.mp4 *.avi *.mov *.mkv *.wmv *.m4v"),
			("All files", "*.*"),
		],
	)
	if not video_path:
		return

	stop_video()
	decode_stop = threading.Event()
	frame_queue = queue.Queue(maxsize=1)
	event_queue = queue.Queue()
	rotation_degrees = 0
	video_running = True
	status_text.set("A: rotate left 90 degrees | D: rotate right 90 degrees | Esc: stop")
	threading.Thread(
		target=decode_video,
		args=(video_path, decode_stop, frame_queue, event_queue),
		daemon=True,
	).start()


def handle_key(event):
	global rotation_degrees

	if event.keysym.lower() == "a":
		rotation_degrees = (rotation_degrees + 90) % 360
		render_current_frame()
	elif event.keysym.lower() == "d":
		rotation_degrees = (rotation_degrees - 90) % 360
		render_current_frame()
	elif event.keysym == "Escape":
		stop_video()
		status_text.set("Video stopped.")


def close_application():
	stop_video()
	root.destroy()


def main():
	tk.Button(root, text="Choose video", command=open_video).pack(pady=(12, 4))
	tk.Label(root, textvariable=status_text).pack(pady=4)
	preview_label.pack(expand=True, padx=12, pady=12)
	root.bind_all("<KeyPress>", handle_key)
	root.protocol("WM_DELETE_WINDOW", close_application)
	root.after(10, poll_video)
	root.mainloop()


preview_label = tk.Label(root)


if __name__ == "__main__":
	main()