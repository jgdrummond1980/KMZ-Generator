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


def annotate_image(image_path, metadata):
    """
    Annotate the image with easting, northing, elevation at the top,
    and date/time at the bottom-left.
    """
    # Open the image
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)

    # Set fonts (use default font if no TTF file is available)
    try:
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font = ImageFont.truetype(font_path, 32)  # Increased font size for better readability
    except IOError:
        font = ImageFont.load_default()

    # Extract metadata
    easting = metadata.get("easting", "Unknown Easting")
    northing = metadata.get("northing", "Unknown Northing")
    elevation = metadata.get("elevation", "Unknown Elevation")
    date_time = metadata.get("date_time", "Unknown Date/Time")

    # Add text at the top (easting, northing, elevation)
    top_text = f"E: {easting:.2f}, N: {northing:.2f}, Elev: {elevation:.2f} m"
    draw.text((10, 10), top_text, fill="white", font=font)

    # Add text at the bottom-left (date/time)
    bottom_text = date_time
    text_bbox = draw.textbbox((0, 0), bottom_text, font=font)
    text_width, text_height = text_bbox[2], text_bbox[3]
    image_width, image_height = image.size
    draw.text((10, image_height - text_height - 10), bottom_text, fill="white", font=font)

    # Save the annotated image
    annotated_image_path = image_path.replace(".jpg", "_annotated.jpg")
    image.save(annotated_image_path)
    return annotated_image_path


def create_kmz_with_fan_overlay(folder_path, output_kmz, fan_image_path):
    """Generate a KMZ file with fan overlays and placemarks."""
    kml = simplekml.Kml()
    image_paths = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    kmz_images = []
    has_data = False

    for image_path in image_paths:
        # Extract GPS metadata
        metadata = get_gps_metadata(image_path)
        if metadata:
            has_data = True
            lat, lon = metadata["latitude"], metadata["longitude"]
            orientation = float(metadata["orientation"])
            easting = lon * 111319.9  # Approximate conversion
            northing = lat * 111319.9  # Approximate conversion
            elevation = metadata.get("elevation", 0)  # Placeholder elevation
            date_time = "14 Feb 2023, 10:41:30"  # Example timestamp, replace with actual if available

            # Annotate the image with metadata
            image_metadata = {
                "easting": easting,
                "northing": northing,
                "elevation": elevation,
                "date_time": date_time,
            }
            annotated_image_path = annotate_image(image_path, image_metadata)

            # Add a placemark
            pnt = kml.newpoint(name=os.path.basename(image_path), coords=[(lon, lat)])
            pnt.description = (
                f"Orientation: {orientation}<br>"
                f'<img src="{os.path.basename(annotated_image_path)}" alt="Image" width="800" />'
            )
            pnt.style.iconstyle.icon.href = "http://maps.google.com/mapfiles/kml/paddle/blu-circle.png"

            # Add a ground overlay using the fan image
            overlay_name = f"Overlay - {os.path.basename(image_path)}"
            ground_overlay = kml.newgroundoverlay(name=overlay_name)
            ground_overlay.icon.href = "Fan.png"  # Refer to the fan image
            ground_overlay.latlonbox.north = lat + 0.00005  # Adjust size to 5px
            ground_overlay.latlonbox.south = lat - 0.00005
            ground_overlay.latlonbox.east = lon + 0.00005
            ground_overlay.latlonbox.west = lon - 0.00005
            ground_overlay.latlonbox.rotation = orientation - 90  # Align orientation to top of rotated Fan.png

            # Add images and fan overlay to KMZ package
            kmz_images.append((os.path.basename(annotated_image_path), annotated_image_path))

    if not has_data:
        raise ValueError("No valid GPS metadata found in the uploaded images.")

    # Add fan image to the temporary folder
    fan_image_dest = os.path.join(folder_path, "Fan.png")
    os.rename(fan_image_path, fan_image_dest)

    # Save KML file
    kml_file = os.path.join(folder_path, "doc.kml")
    kml.save(kml_file)

    # Create KMZ file
    with zipfile.ZipFile(output_kmz, 'w') as kmz:
        kmz.write(kml_file, "doc.kml")
        for img_name, img_path in kmz_images:
            kmz.write(img_path, img_name)
        kmz.write(fan_image_dest, "Fan.png")

    os.remove(kml_file)  # Clean up temporary KML file


# Streamlit App
st.set_page_config(page_title="KMZ Generator", layout="wide")
st.title("JPEG/PNG to KMZ Converter")

uploaded_files = st.file_uploader(
    "Upload geotagged photos (JPG, JPEG, PNG):",
    accept_multiple_files=True,
    type=["jpg", "jpeg", "png"]
)

# GitHub-hosted Fan.png URL
fan_image_url = "https://raw.githubusercontent.com/jgdrummond1980/KMZ-Generator/main/Fan.png"
output_kmz_name = st.text_input("Enter output KMZ file name:", "output.kmz")

if st.button("Generate KMZ"):
    if not uploaded_files:
        st.error("Please upload at least one photo.")
    else:
        # Display loading spinner
        with st.spinner("Generating KMZ file, please wait..."):
            try:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    # Download the fan image into the temporary directory
                    fan_image_path = os.path.join(tmp_dir, "Fan.png")
                    download_fan_image(fan_image_url, fan_image_path)

                    for uploaded_file in uploaded_files:
                        file_path = os.path.join(tmp_dir, uploaded_file.name)
                        with open(file_path, "wb") as f:
                            f.write(uploaded_file.read())

                    output_kmz_path = os.path.join(tmp_dir, output_kmz_name)
                    create_kmz_with_fan_overlay(tmp_dir, output_kmz_path, fan_image_path)

                    with open(output_kmz_path, "rb") as f:
                        st.download_button(
                            label="Download KMZ",
                            data=f,
                            file_name=output_kmz_name,
                            mime="application/vnd.google-earth.kmz"
                        )
                st.success("KMZ file generated successfully!")
            except ValueError as e:
                st.error(str(e))
            except Exception as e:
                st.error(f"An error occurred: {e}")
