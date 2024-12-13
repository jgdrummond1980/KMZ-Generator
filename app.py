import os
import tempfile
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import simplekml
import zipfile
import streamlit as st

def get_gps_metadata(image_path):
    """Extract GPS metadata from an image."""
    image = Image.open(image_path)
    exif_data = image._getexif()
    if not exif_data:
        return None

    gps_info = {}
    for tag, value in exif_data.items():
        tag_name = TAGS.get(tag, tag)
        if tag_name == "GPSInfo":
            for t, val in value.items():
                gps_tag = GPSTAGS.get(t, t)
                gps_info[gps_tag] = val

    if not gps_info:
        return None

    def convert_to_degrees(value):
        d = value[0][0] / value[0][1]
        m = value[1][0] / value[1][1]
        s = value[2][0] / value[2][1]
        return d + (m / 60.0) + (s / 3600.0)

    if "GPSLatitude" in gps_info and "GPSLongitude" in gps_info:
        lat = convert_to_degrees(gps_info["GPSLatitude"])
        lon = convert_to_degrees(gps_info["GPSLongitude"])
        if gps_info["GPSLatitudeRef"] == "S":
            lat = -lat
        if gps_info["GPSLongitudeRef"] == "W":
            lon = -lon
        return {
            "latitude": lat,
            "longitude": lon,
            "orientation": gps_info.get("GPSImgDirection", None),
        }
    return None


def create_kmz(folder_path, output_kmz):
    """Generate KMZ file from geotagged images."""
    kml = simplekml.Kml()
    image_paths = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    kmz_images = []

    for image_path in image_paths:
