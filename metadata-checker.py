from exiftool import ExifToolHelper

with ExifToolHelper() as et:
    metadata = et.get_metadata("test-image.jpg")
    for d in metadata:
        for k, v in d.items():
            print(f"{k}: {v}")