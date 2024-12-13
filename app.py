import os
import tempfile
from simplekml import Kml
import streamlit as st
import subprocess
import shutil


def check_exiftool():
    """Verify if ExifTool is installed and accessible."""
    if not shutil.which("exiftool"):
        st.error("ExifTool is not installed or cannot be found in the environment. Please check your deployment setup.")
        return False
    return True


def extract_metadata_with_exiftool(file_path):
    """Extract metadata (Exif or XMP) using ExifTool."""
    if not check_exiftool():
        return None
    try:
        result = subprocess.run(
            ["exiftool", "-gpslatitude", "-gpslongitude", "-gpsimgdirection", file_path],
            stdout=subprocess.PIPE,
            text=True,
            check=True,
        )
        metadata = result.stdout.strip().splitlines()
        gps_data = {}
        for line in metadata:
            key, value = line.split(":", 1)
            key = key.strip().lower().replace(" ", "_")
            value = value.strip()
            gps_data[key] = value

        if "gps_latitude" in gps_data and "gps_longitude" in gps_data:
            return {
                "latitude": convert_to_decimal(gps_data["gps_latitude"]),
                "longitude": convert_to_decimal(gps_data["gps_longitude"]),
                "orientation": gps_data.get("gps_img_direction", "Unknown"),
            }
        return None
    except FileNotFoundError:
        st.error("ExifTool is not installed or cannot be found in the environment.")
        return None
    except Exception as e:
        st.error(f"Metadata extraction failed: {e}")
        return None


def convert_to_decimal(coord):
    """Convert GPS coordinates from DMS to decimal format."""
    parts = coord.split()
    degrees = float(parts[0].replace("°", ""))
    minutes = float(parts[1].replace("'", ""))
    seconds = float(parts[2].replace('"', "")) if len(parts) > 2 else 0
    direction = parts[-1]
    decimal = degrees + (minutes / 60) + (seconds / 3600)
    if direction in ["S", "W"]:
        decimal = -decimal
    return decimal


def create_kmz(folder_path, output_kmz):
    """Generate a KMZ file from geotagged images."""
    kml = Kml()
    image_paths = [os.path.join(folder_path, f) for f in os.listdir(folder_path)]
    has_data = False

    for image_path in image_paths:
        metadata = extract_metadata_with_exiftool(image_path)
        if metadata:
            has_data = True
            lat, lon = metadata["latitude"], metadata["longitude"]
            orientation = metadata.get("orientation", "Unknown")
            image_name = os.path.basename(image_path)

            # Create a placemark
            pnt = kml.newpoint(name=image_name, coords=[(lon, lat)])
            pnt.description = f"Orientation: {orientation}"
            pnt.style.iconstyle.icon.href = image_name

            # Add the image to KMZ
            kml.addfile(image_path)

    if not has_data:
        raise ValueError("No valid GPS metadata found in the uploaded images.")

    # Save KMZ
    kml.savekmz(output_kmz)


# Streamlit App
st.set_page_config(page_title="KMZ Generator", layout="wide")
st.title("HEIC, Exif, and XMP to KMZ Converter")

uploaded_files = st.file_uploader(
    "Upload images (HEIC, JPG, PNG):",
    accept_multiple_files=True,
    type=["heic", "jpg", "jpeg", "png"]
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
