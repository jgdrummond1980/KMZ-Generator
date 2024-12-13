import os
import tempfile
import zipfile
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import simplekml
import streamlit as st


def get_gps_metadata(image_path):
    """Extract GPS metadata from a JPEG/PNG image."""
    try:
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
            if isinstance(value, tuple):
                d = float(value[0])
                m = float(value[1])
                s = float(value[2])
            else:
                d = float(value[0].numerator) / float(value[0].denominator)
                m = float(value[1].numerator) / float(value[1].denominator)
                s = float(value[2].numerator) / float(value[2].denominator)
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
    except Exception as e:
        st.error(f"Error extracting metadata: {e}")
        return None


def create_kmz(folder_path, output_kmz):
    """Generate a KMZ file from geotagged JPEG/PNG images."""
    kml = simplekml.Kml()
    image_paths = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    kmz_images = []
    has_data = False

    for image_path in image_paths:
        metadata = get_gps_metadata(image_path)
        if metadata:
            has_data = True
            lat, lon = metadata["latitude"], metadata["longitude"]
            orientation = metadata.get("orientation", "Unknown")
            image_name = os.path.basename(image_path)

            # Create a placemark
            pnt = kml.newpoint(name=image_name, coords=[(lon, lat)])
            # Embed the image in the description with a larger size and a download link
            pnt.description = (
                f"Orientation: {orientation}<br>"
                f'<img src="{image_name}" alt="Image" width="600" /><br>'
                f'<a href="{image_name}" download="{image_name}">Download Image</a>'
            )
            # Set the placemark to a blue dot
            pnt.style.iconstyle.icon.href = "http://maps.google.com/mapfiles/kml/paddle/blu-circle.png"

            # Add image to KMZ package
            kmz_images.append((image_name, image_path))

    if not has_data:
        raise ValueError("No valid GPS metadata found in the uploaded images.")

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
st.set_page_config(page_title="KMZ Generator", layout="wide")
st.title("JPEG/PNG to KMZ Converter")

uploaded_files = st.file_uploader(
    "Upload geotagged photos (JPG, JPEG, PNG):",
    accept_multiple_files=True,
    type=["jpg", "jpeg", "png"]
)

output_kmz_name = st.text_input("Enter output KMZ file name:", "output.kmz")

if st.button("Generate KMZ"):
    if not uploaded_files:
        st.error("Please upload at least one photo.")
    else:
        try:
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
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"An error occurred: {e}")
