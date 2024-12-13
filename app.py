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
        metadata = get_gps_metadata(image_path)
        if metadata:
            lat, lon = metadata["latitude"], metadata["longitude"]
            orientation = metadata.get("orientation", "Unknown")
            image_name = os.path.basename(image_path)

            # Create a placemark
            pnt = kml.newpoint(name=image_name, coords=[(lon, lat)])
            pnt.description = f"Orientation: {orientation}"
            pnt.style.iconstyle.icon.href = image_name  # Link to the image in KMZ

            # Add image to KMZ package
            kmz_images.append((image_name, image_path))

    # Save KML file
    kml_file = os.path.join(folder_path, "doc.kml")
    kml.save(kml_file)

    # Create KMZ file
    with zipfile.ZipFile(output_kmz, 'w') as kmz:
        kmz.write(kml_file, "doc.kml")
        for img_name, img_path in kmz_images:
            kmz.write(img_path, img_name)

    os.remove(kml_file)  # Clean up temporary KML file


# Streamlit App
st.title("Geotagged Photos to KMZ Converter")

uploaded_files = st.file_uploader(
    "Upload geotagged photos (JPG, PNG):",
    accept_multiple_files=True,
    type=["jpg", "jpeg", "png"]
)

output_kmz_name = st.text_input("Enter output KMZ file name:", "output.kmz")

if st.button("Generate KMZ"):
    if not uploaded_files:
        st.error("Please upload at least one photo.")
    else:
        with tempfile.TemporaryDirectory() as tmp_dir:
            for uploaded_file in uploaded_files:
                file_path = os.path.join(tmp_dir, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.read())

            output_kmz_path = os.path.join(tmp_dir, output_kmz_name)
            create_kmz(tmp_dir, output_kmz_path)

            with open(output_kmz_path, "rb") as f:
                st.download_button(
                    label="Download KMZ",
                    data=f,
                    file_name=output_kmz_name,
                    mime="application/vnd.google-earth.kmz"
                )
