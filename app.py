import streamlit as st
from rembg import remove
from PIL import Image
from io import BytesIO
from azure.storage.blob import BlobServiceClient
import uuid, re

# ---- Funciones de arriba (pega aquí trim_alpha, to_square_contain, to_square_cover) ----
# (omito por brevedad; pégalos exactamente como están)

def sanitize_blob_name(name: str) -> str:
    base = re.sub(r"\.[^.]+$", "", name).strip().replace(" ", "_")
    base = re.sub(r"[^A-Za-z0-9_\-]", "", base)
    return f"{base}_{uuid.uuid4().hex[:8]}.png"

st.set_page_config(page_title="600×600 sin deformar", layout="centered")
st.title("🖼️ Quitar fondo → 600×600 sin deformar → (opcional) subir a Blob")

colA, colB = st.columns(2)
with colA:
    modo = st.radio("Modo de encuadre", ["Contain (padding)", "Cover (recorte)"])
with colB:
    permitir_upscaling = st.checkbox("Permitir upscaling", value=False,
                                     help="Desactívalo para NO agrandar imágenes pequeñas (mejor calidad).")

fondo_transparente = st.checkbox("Fondo transparente (solo Contain)", value=True)

uploaded_file = st.file_uploader("Sube tu imagen (JPG/PNG)", type=["jpg", "jpeg", "png"])

# Azure secrets (opcional)
azure_ok = False
try:
    CONNECTION_STRING = st.secrets["azure"]["connection_string"]
    CONTAINER_NAME = st.secrets["azure"]["container_name"]
    azure_ok = True
except Exception:
    pass  # si no hay credenciales, igual puedes descargar localmente

if uploaded_file is not None:
    original = Image.open(uploaded_file).convert("RGBA")
    st.image(original, caption="Original (sin deformar)", use_container_width=True)

    with st.spinner("Procesando…"):
        # 1) Quitar fondo
        no_bg = remove(original)
        # 2) Recortar bordes transparentes
        no_bg = trim_alpha(no_bg)

        # 3) Encajar sin deformar a 600×600
        if modo.startswith("Contain"):
            bg = (255, 255, 255, 0) if fondo_transparente else (255, 255, 255, 255)
            final_img = to_square_contain(no_bg, size=600, allow_upscale=permitir_upscaling, bg=bg)
        else:
            final_img = to_square_cover(no_bg, size=600, allow_upscale=permitir_upscaling)

    st.image(final_img, caption="Resultado 600×600 (sin deformar)", use_container_width=True)

    # 4) Guardado PNG optimizado (sin perder calidad visual)
    buf = BytesIO()
    # Para PNG: optimize=True intenta mejor compresión sin afectar nitidez
    final_img.save(buf, format="PNG", optimize=True)
    buf.seek(0)

    st.download_button("⬇️ Descargar PNG 600×600", data=buf,
                       file_name="imagen_600x600.png", mime="image/png")

    # 5) Subir a Azure Blob (opcional)
    if azure_ok and st.button("☁️ Subir a Azure Blob"):
        try:
            blob_service = BlobServiceClient.from_connection_string(CONNECTION_STRING)
            container_client = blob_service.get_container_client(CONTAINER_NAME)

            blob_name = sanitize_blob_name(uploaded_file.name)
            blob_client = container_client.get_blob_client(blob=blob_name)

            buf.seek(0)
            blob_client.upload_blob(buf, overwrite=True)

            account_url = blob_service.url
            public_url = f"{account_url}/{CONTAINER_NAME}/{blob_name}"
            st.success("✅ Subida correcta.")
            st.code(public_url)
        except Exception as e:
            st.error(f"❌ Error al subir: {e}")

