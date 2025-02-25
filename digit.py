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
    Replacement for the removed `streamlit.elements.image.image_to_url` function.
    Converts a PIL image to a data URL so it can be displayed as a background in st_canvas.
    """
    if output_format == "auto":
        output_format = "PNG"  # Default to PNG if unspecified

    buffered = BytesIO()
    image.save(buffered, format=output_format)
    b64_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    mime_type = f"image/{output_format.lower()}"
    return f"data:{mime_type};base64,{b64_str}"

# Apply the patch *before* importing st_canvas
st_image.image_to_url = image_to_url


##################################################
# 2) IMPORTS
##################################################
from streamlit_drawable_canvas import st_canvas
from PIL import Image
import numpy as np

st.set_page_config(page_title="Digitize Graph (3 Points)", layout="wide")
st.title("Digitize a Graph from an Image (3 Reference Points)")

##################################################
# 3) FILE UPLOADER
##################################################
uploaded_file = st.file_uploader(
    "Upload a graph image (PNG/JPG)", 
    type=["png", "jpg", "jpeg"]
)

if uploaded_file is not None:
    # Load the image with PIL
    image = Image.open(uploaded_file)

    # 3a) Display raw image just to confirm it's loaded
    st.image(image, caption="Preview of uploaded image")

    # Original size
    orig_width, orig_height = image.size

    # We'll clamp the canvas to a maximum size so it's not huge
    canvas_width = min(orig_width, 800)
    canvas_height = min(orig_height, 600)

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
        background_image=image,          # pass the PIL Image
        update_streamlit=True,
        height=canvas_height,
        width=canvas_width,
        drawing_mode="point",            # each click -> a small circle
        point_display_radius=5,
        key="canvas",
    )

    ##################################################
    # 5) DIGITIZE BUTTON
    ##################################################
    if st.button("Digitize"):
        if canvas_result.json_data is None:
            st.error("No canvas data. Please click on the image first.")
        else:
            # Get the circles from JSON
            objects = canvas_result.json_data["objects"] or []
            circles = [obj for obj in objects if obj["type"] == "circle"]

            if len(circles) < 3:
                st.error("You need at least 3 points for reference!")
            else:
                # First 3 points = reference corners
                # We'll define a helper to extract circle centers
                def circle_center(c):
                    return (
                        c["left"] + c["radius"],
                        c["top"]  + c["radius"]
                    )

                ref1 = circles[0]
                ref2 = circles[1]
                ref3 = circles[2]

                p1x, p1y = circle_center(ref1)  # maps to (0,0)
                p2x, p2y = circle_center(ref2)  # maps to (maxX,0)
                p3x, p3y = circle_center(ref3)  # maps to (0,maxY)

                # The rest are data points
                data_circles = circles[3:]

                # Convert to NumPy for matrix math
                p1 = np.array([p1x, p1y])
                p2 = np.array([p2x, p2y])
                p3 = np.array([p3x, p3y])

                # We want T such that:
                # T(p1) = (0,0)
                # T(p2) = (max_x, 0)
                # T(p3) = (0, max_y)
                #
                # Let M be a 2x2 matrix, and we first shift by p1:
                # T(p) = M*(p - p1).
                #
                # Then M*(p2 - p1) = (max_x, 0)
                #      M*(p3 - p1) = (0, max_y)

                v12 = p2 - p1
                v13 = p3 - p1

                pixel_mat = np.array([
                    [v12[0], v13[0]],
                    [v12[1], v13[1]]
                ])
                real_mat = np.array([
                    [max_x,    0],
                    [0,    max_y]
                ])

                try:
                    inv_pixel_mat = np.linalg.inv(pixel_mat)
                    M = real_mat @ inv_pixel_mat
                except np.linalg.LinAlgError:
                    st.error("Reference points appear collinear or invalid. Cannot invert matrix.")
                    st.stop()

                # Transform each data point
                digitized_points = []
                for c in data_circles:
                    cx, cy = circle_center(c)
                    p = np.array([cx, cy])
                    real_xy = M @ (p - p1)  # affine transform
                    digitized_points.append(real_xy)

                st.success("Digitization complete!")
                st.write("**Transformed Points (x, y):**")
                # Display in a small table
                st.markdown(
                    "| Index |    X    |    Y    |\n"
                    "|-------|---------|---------|\n" +
                    "\n".join(
                        f"| {i+1}    | {pt[0]:.3f} | {pt[1]:.3f} |"
                        for i, pt in enumerate(digitized_points)
                    )
                )
