import streamlit as st
import streamlit.elements.image as st_image
from io import BytesIO
import base64

def image_to_url(
    image, width=None, clamp=False, channels="RGB", output_format="auto", image_id=None
):
    if output_format == "auto":
        output_format = "PNG"
    buf = BytesIO()
    image.save(buf, format=output_format)
    b64 = base64.b64encode(buf.getvalue()).decode()
    mime = f"image/{output_format.lower()}"
    return f"data:{mime};base64,{b64}"

st_image.image_to_url = image_to_url

from streamlit_drawable_canvas import st_canvas
from PIL import Image

st.title("Canvas Background Test")

uploaded_file = st.file_uploader("Upload PNG/JPG", type=["png","jpg","jpeg"])
if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, caption="Preview of uploaded image")

    w, h = img.size
    canvas_result = st_canvas(
        background_image=img,   # pass the PIL image
        width=min(w, 800),
        height=min(h, 600),
        drawing_mode="point",
        stroke_width=5,
        stroke_color="#FF0000",
        key="canvas",
    )

