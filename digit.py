import streamlit as st
import numpy as np
from PIL import Image, ImageDraw
from io import BytesIO
import base64

# Set up the Streamlit page
st.set_page_config(page_title="Digitize Graph", layout="wide")
st.title("Digitize a Graph from an Image (3 Reference Points)")

# File uploader
uploaded_file = st.file_uploader(
    "Upload a graph image (PNG/JPG)", 
    type=["png", "jpg", "jpeg"]
)

if uploaded_file is not None:
    # Load the image
    image_pil = Image.open(uploaded_file).convert("RGBA")
    
    # Display a preview
    st.image(image_pil, caption="Preview of uploaded image")
    
    # Store image dimensions
    orig_width, orig_height = image_pil.size
    st.write(f"Image Mode: {image_pil.mode}, Size: {orig_width}x{orig_height}")
    
    # Instructions
    st.markdown("""
    **Instructions**:
    1. Click the points directly on the preview image above
    2. First three points define your coordinate system:
       - First point → (0, 0)
       - Second point → (maxX, 0)
       - Third point → (0, maxY)
    3. Enter maxX and maxY values below
    4. Additional points will be digitized
    """)
    
    # Create two columns - one for inputs, one for results
    col1, col2 = st.columns(2)
    
    with col1:
        # Let user specify maxX, maxY
        max_x = st.number_input("maxX (for 2nd reference point)", value=10.0)
        max_y = st.number_input("maxY (for 3rd reference point)", value=5.0)
        
        # Store points in session state if not already there
        if 'points' not in st.session_state:
            st.session_state.points = []
            
        # Add a manual point input option
        st.markdown("### Add point coordinates (pixels)")
        x_px = st.number_input("X pixel coordinate", min_value=0, max_value=orig_width, step=1)
        y_px = st.number_input("Y pixel coordinate", min_value=0, max_value=orig_height, step=1)
        
        if st.button("Add Point"):
            st.session_state.points.append((x_px, y_px))
            st.success(f"Added point at pixel ({x_px}, {y_px})")
            
        if st.button("Clear All Points"):
            st.session_state.points = []
            st.success("Cleared all points")
            
    # Get points from session state
    points = st.session_state.points
    
    # Draw points on a copy of the image for visualization
    if points:
        image_with_points = image_pil.copy()
        draw = ImageDraw.Draw(image_with_points)
        
        # Draw numbered circles for each point
        for i, (x, y) in enumerate(points):
            radius = 5
            draw.ellipse((x-radius, y-radius, x+radius, y+radius), fill="red")
            draw.text((x+7, y-7), f"{i+1}", fill="white")
        
        # Show image with points
        st.image(image_with_points, caption="Image with digitized points", use_column_width=True)
    
    with col2:
        st.markdown("### Digitized Points")
        
        if len(points) < 3:
            st.warning("Need at least 3 reference points!")
        else:
            # Extract reference points
            p1 = np.array(points[0])  # => (0,0)
            p2 = np.array(points[1])  # => (maxX,0)
            p3 = np.array(points[2])  # => (0,maxY)
            
            # Build the transform
            v12 = p2 - p1  # pixel vector for (maxX,0)
            v13 = p3 - p1  # pixel vector for (0,maxY)
            
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
                
                # Digitize points beyond the first 3
                data_points = points[3:]
                digitized_points = []
                
                for p in data_points:
                    p_array = np.array(p)
                    real_xy = M @ (p_array - p1)
                    digitized_points.append(real_xy)
                
                # Show results
                st.success("Digitization complete!")
                st.write("**Transformed Points (x, y):**")
                
                # Display results in a table
                rows = [
                    f"| {i+1} | {pt[0]:.3f} | {pt[1]:.3f} |"
                    for i, pt in enumerate(digitized_points)
                ]
                
                if rows:
                    st.markdown(
                        "| Index |    X    |    Y    |\n"
                        "|-------|---------|---------|\n"
                        + "\n".join(rows)
                    )
                else:
                    st.info("Add more points beyond the 3 reference points to see digitized coordinates.")
                    
            except np.linalg.LinAlgError:
                st.error("Reference points appear collinear or invalid. Cannot invert matrix.")
else:
    st.info("Upload an image to begin.")
