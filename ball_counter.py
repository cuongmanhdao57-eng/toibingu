from pathlib import Path
import runpy


if __name__ == "__main__":
	plate_cropper = Path(__file__).with_name("plate_character_cropper.py")
	runpy.run_path(str(plate_cropper), run_name="__main__")