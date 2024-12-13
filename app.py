import os
import tempfile
import zipfile
import requests
from PIL import Image, ImageDraw, ImageFont, ExifTags
import simplekml
import streamlit as st
from fractions import Fraction as IFDRational


def download_fan_image(fan_image_url, destination):
    """Download the fan image from GitHub and rotate it by -90 degrees."""
    response = requests.get(fan_image_url, stream=True)
    if response.status_code == 200:
        with open(destination, "wb") as f:
            f.write(response.content)
        
        # Open the downloaded image and rotate it by -90 degrees
        with Image.open(destination) as img:
            rotated_img = img.rotate(-90, expand=True)
            rotated_img.save(destination)
    else:
        raise ValueError(f"Failed to download fan image from {fan_image_url}")


def correct_image_orientation(image):
    """Correct image orientation based on Exif data."""
    try:
        for orientation in ExifTags.TAGS.keys():
            if ExifTags.TAGS[orientation] == "Orientation":
                break

        exif = image._getexif()
        if exif and orientation in exif:
            if exif[orientation] == 3:
                image = image.rotate(180, expand=True)
            elif exif[orientation] == 6:
                image = image.rotate(270, expand=True)
            elif exif[orientation] == 8:
                image = image.rotate(90, expand=True)
    except Exception as e:
        st.warning(f"Could not adjust image orientation: {e}")
    return image


def convert_to_degrees(value):
    """Convert GPS coordinates to degrees."""
    try:
        if isinstance(value, list) or isinstance(value, tuple):
            d = float(value[0].numerator) / float(value[0].denominator) if isinstance(value[0], IFDRational) else float(value[0])
            m = float(value[1].numerator) / float(value[1].denominator) if isinstance(value[1], IFDRational) else float(value[1])
            s = float(value[2].numerator) / float(value[2].denominator) if isinstance(value[2], IFDRational) else float(value[2])
            return d + (m / 60.0) + (s / 3600.0)
        return None
    except Exception as e:
        st.warning(f"Error converting GPS value to degrees: {e}")
        return None


def get_gps_metadata(image_path):
    """Extract GPS metadata from a JPEG/PNG image."""
    try:
        image = Image.open(image_path)
        exif_data = image._getexif()
        if not exif_data:
            return None

        gps_info = {}
        for tag, value in exif_data.items():
            tag_name = ExifTags.TAGS.get(tag, tag)
            if tag_name == "GPSInfo":
                for t, val in value.items():
                    gps_tag = ExifTags.GPSTAGS.get(t, t)
                    gps_info[gps_tag] = val

        if not gps_info:
            return None

        if "GPSLatitude" in gps_info and "GPSLongitude" in gps_info:
            lat = convert_to_degrees(gps_info["GPSLatitude"])
            lon = convert_to_degrees(gps_info["GPSLongitude"])
            if gps_info.get("GPSLatitudeRef", "N") == "S":
                lat = -lat
            if gps_info.get("GPSLongitudeRef", "E") == "W":
                lon = -lon

            elevation = gps_info.get("GPSAltitude", (0, 1))
            elevation = float(elevation[0]) / float(elevation[1]) if isinstance(elevation, tuple) else 0

            orientation = gps_info.get("GPSImgDirection", 0)
            orientation = float(orientation[0]) / float(orientation[1]) if isinstance(orientation, tuple) else orientation

            return {
                "latitude": lat,
                "longitude": lon,
                "elevation": elevation,
                "orientation": orientation,
            }
        return None
    except Exception as e:
        st.error(f"Error extracting metadata from {image_path}: {e}")
        return None


# Other functions (annotate_image, create_kmz_with_fan_overlay) remain unchanged...
# Append them here as they are already provided.
