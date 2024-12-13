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
            image_name = os.path.basename(image_path)

            # Open image, correct orientation, and save corrected copy
            image = Image.open(image_path)
            corrected_image = correct_image_orientation(image)
            corrected_image_path = os.path.join(folder_path, image_name)
            corrected_image.save(corrected_image_path)

            # Add a placemark
            pnt = kml.newpoint(name=image_name, coords=[(lon, lat)])
            pnt.description = (
                f"Orientation: {orientation}<br>"
                f'<img src="{image_name}" alt="Image" width="800" />'
            )
            pnt.style.iconstyle.icon.href = "http://maps.google.com/mapfiles/kml/paddle/blu-circle.png"

            # Add a ground overlay using the fan image
            overlay_name = f"Overlay - {image_name}"
            ground_overlay = kml.newgroundoverlay(name=overlay_name)
            ground_overlay.icon.href = "Fan.png"  # Refer to the fan image
            ground_overlay.latlonbox.north = lat + 0.0002  # Adjust size to 20px
            ground_overlay.latlonbox.south = lat - 0.0002
            ground_overlay.latlonbox.east = lon + 0.0002
            ground_overlay.latlonbox.west = lon - 0.0002
            ground_overlay.latlonbox.rotation = orientation - 90  # Align orientation to top of Fan.png

            # Add images and fan overlay to KMZ package
            kmz_images.append((image_name, corrected_image_path))

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
