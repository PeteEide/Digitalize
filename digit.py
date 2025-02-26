import streamlit as st
from PIL import Image
import numpy as np

# 1) Import the click-detector component
from streamlit_image_coordinates import streamlit_image_coordinates

st.set_page_config(page_title="Digitize Graph (3 Points)", layout="wide")
st.title("Digitize a Graph from an Image (3 Reference Points, No Canvas)")

##################################################
# 2) File Uploader
##################################################
uploaded_file = st.file_uploader("Upload a graph image (PNG/JPG)", type=["png", "jpg", "jpeg"])

# A session state list to store *all* clicked points
if "points" not in st.session_state:
    st.session_state["points"] = []  # each item is (x, y) in pixel coords

if uploaded_file is not None:
    # Load image with PIL
    image_pil = Image.open(uploaded_file).convert("RGB")  # ensure RGB
    st.image(image_pil, caption="Preview of uploaded image")

    # Let user define real-world coords
    st.write("#### Real-World Coordinate Inputs:")
    col1, col2 = st.columns(2)
    with col1:
        max_x = st.number_input("maxX (for 2nd click)", value=10.0)
    with col2:
        max_y = st.number_input("maxY (for 3rd click)", value=5.0)

    st.markdown("""
    **Click detection**:
    - **Click #1** → (0, 0)
    - **Click #2** → (maxX, 0)
    - **Click #3** → (0, maxY)
    - Additional clicks → data points to digitize
    """)

    # 3) Use the click-detector component
    # The component returns the *latest* click in pixel coords (e.g. {'x':..., 'y':...})
    # We also pass a 'key' so it doesn't reset on each rerun.
    result = streamlit_image_coordinates(
        image_pil, 
        width=image_pil.width,  # or a desired scaled width
        height=image_pil.height,
        key="click_detector"
    )

    # 4) If there's a new click, append to the session_state["points"]
    if result is not None:
        x_pix, y_pix = result["x"], result["y"]
        if x_pix is not None and y_pix is not None:
            # If the user clicked inside the image
            # We'll store the pixel coords
            click_tup = (x_pix, y_pix)
            # Only append if it's a new click (component can re-return the same coords)
            if (not st.session_state["points"]) or (click_tup != st.session_state["points"][-1]):
                st.session_state["points"].append(click_tup)

    st.write("#### Collected Pixel Clicks so far:")
    st.write(st.session_state["points"])

    # 5) Digitize Button
    if st.button("Digitize"):
        # Must have at least 3 reference clicks
        if len(st.session_state["points"]) < 3:
            st.error("Need at least 3 clicks for reference points!")
        else:
            # First 3 points => references
            p1 = np.array(st.session_state["points"][0])  # (0,0)
            p2 = np.array(st.session_state["points"][1])  # (maxX,0)
            p3 = np.array(st.session_state["points"][2])  # (0,maxY)

            # If no additional points, nothing to digitize
            if len(st.session_state["points"]) <= 3:
                st.warning("No data points beyond the 3 references. Click more points first!")
            else:
                # Build the transform
                # p1->(0,0), p2->(maxX,0), p3->(0,maxY)
                v12 = p2 - p1  # vector in pixel space for (maxX,0)
                v13 = p3 - p1  # vector in pixel space for (0,maxY)

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
                    st.error("Reference points appear collinear or invalid. Can't invert matrix.")
                    st.stop()

                data_points = st.session_state["points"][3:]  # subsequent clicks
                digitized = []
                for dp in data_points:
                    p = np.array(dp)
                    real_xy = M @ (p - p1)
                    digitized.append(real_xy)

                st.success("Digitization complete!")
                st.write("**Transformed Data Points (x, y):**")
                rows = [
                    f"| {i+1} | {pt[0]:.3f} | {pt[1]:.3f} |"
                    for i, pt in enumerate(digitized)
                ]
                st.markdown(
                    "| Index |    X    |    Y    |\n"
                    "|-------|---------|---------|\n"
                    + "\n".join(rows)
                )

    # Optional: clear points
    if st.button("Clear Clicks"):
        st.session_state["points"] = []

else:
    st.info("Upload an image to begin.")

