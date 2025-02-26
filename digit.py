import streamlit as st

##################################################
# 1) MONKEY-PATCH THE REMOVED FUNCTION
#    (Needed for Streamlit 1.20+)
##################################################
import streamlit.elements.image as st_image
from io import BytesIO
import base64

def image_to_url(
    image, width=None, clamp=False, channels="RGB", output_format="auto", image_id=None
):
    """
    Replacement for the removed `streamlit.elements.image.image_to_url`.
    Converts a PIL image to a data URL so st_canvas can display it internally.
    """
    if output_format == "auto":
        output_format = "PNG"
    buf = BytesIO()
    image.save(buf, format=output_format)
    b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
    mime_type = f"image/{output_format.lower()}"
    return f"data:{mime_type};base64,{b64_str}"

# Patch image_to_url BEFORE importing st_canvas
st_image.image_to_url = image_to_url

##################################################
# 2) IMPORTS
##################################################
# We'll also monkey-patch `_resize_img` to disable resizing checks.
import streamlit_drawable_canvas as sdc
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import numpy as np

# Monkey-patch the internal resize function so if
# background_image is a PIL image, it won't crash or resize incorrectly.
def _dummy_resize_img(img, new_height, new_width):
    # Return the image unmodified
    return img

sdc._resize_img = _dummy_resize_img

##################################################
# 3) STREAMLIT APP
##################################################
st.set_page_config(page_title="Digitize Graph (3 Points)", layout="wide")
st.title("Digitize a Graph from an Image (3 Reference Points)")

uploaded_file = st.file_uploader(
    "Upload a graph image (PNG/JPG)",
    type=["png", "jpg", "jpeg"]
)

if uploaded_file:
    # Load the image in RGBA mode
    image_pil = Image.open(uploaded_file).convert("RGBA")

    # Show the raw PIL image as a preview
    st.image(image_pil, caption="Preview of uploaded image")

    orig_width, orig_height = image_pil.size

    st.write(f"Image Mode: {image_pil.mode}, Size: {image_pil.size}")

    # Decide canvas size
    canvas_width = min(orig_width, 1000)
    canvas_height = min(orig_height, 800)

    st.write("**Instructions**:")
    st.markdown("""
    1. **Click 3 points** on the image to define your coordinate system:
       - **First click** → Real coords **(0, 0)**
       - **Second click** → Real coords **(maxX, 0)**
       - **Third click** → Real coords **(0, maxY)**  
    2. Enter your numeric **maxX** and **maxY** below.  
    3. **Click** as many additional points (circles) as you want to digitize.  
    4. Press **Digitize** to see the transformed coordinates.
    """)

    col1, col2 = st.columns(2)
    with col1:
        max_x = st.number_input("maxX (second reference corner)", value=10.0)
    with col2:
        max_y = st.number_input("maxY (third reference corner)", value=5.0)

    ##################################################
    # 4) DRAWABLE CANVAS
    ##################################################
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",
        stroke_width=5,
        stroke_color="#FF0000",
        background_color="#FFFFFF",  # White behind the PIL image
        background_image=image_pil,  # Pass our PIL image
        update_streamlit=True,
        width=canvas_width,
        height=canvas_height,
        drawing_mode="point",
        point_display_radius=5,
        key="canvas",
    )

    # DIGITIZE BUTTON
    if st.button("Digitize"):
        if canvas_result.json_data is None:
            st.error("No canvas data. Please click on the image first.")
        else:
            objects = canvas_result.json_data.get("objects", [])
            circles = [obj for obj in objects if obj["type"] == "circle"]

            if len(circles) < 3:
                st.error("You need at least 3 points for reference!")
            else:
                def circle_center(c):
                    # center = (left + radius, top + radius)
                    return (c["left"] + c["radius"], c["top"] + c["radius"])

                # First 3 circles → reference corners
                ref1, ref2, ref3 = circles[:3]
                p1 = np.array(circle_center(ref1))  # (0,0)
                p2 = np.array(circle_center(ref2))  # (maxX,0)
                p3 = np.array(circle_center(ref3))  # (0,maxY)

                # We want an affine transform M so that:
                #  M*(p2-p1) = (max_x, 0)
                #  M*(p3-p1) = (0, max_y)
                v12 = p2 - p1
                v13 = p3 - p1

                pixel_mat = np.array([
                    [v12[0], v13[0]],
                    [v12[1], v13[1]]
                ])
                real_mat = np.array([
                    [max_x, 0],
                    [0,     max_y]
                ])

                try:
                    inv_pixel_mat = np.linalg.inv(pixel_mat)
                    M = real_mat @ inv_pixel_mat
                except np.linalg.LinAlgError:
                    st.error("Reference points appear collinear or invalid. Cannot invert matrix.")
                    st.stop()

                # Transform subsequent circles
                digitized_points = []
                for c in circles[3:]:
                    cx, cy = circle_center(c)
                    p = np.array([cx, cy])
                    real_xy = M @ (p - p1)
                    digitized_points.append(real_xy)

                st.success("Digitization complete!")
                st.write("**Transformed Points (x, y):**")
                rows = [
                    f"| {i+1} | {pt[0]:.3f} | {pt[1]:.3f} |"
                    for i, pt in enumerate(digitized_points)
                ]
                st.markdown(
                    "| Index |    X    |    Y    |\n"
                    "|-------|---------|---------|\n"
                    + "\n".join(rows)
                )
