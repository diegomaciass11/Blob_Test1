import streamlit as st
from rembg import remove
from PIL import Image
import io
from azure.storage.blob import BlobServiceClient
import os

# 🔐 Configuración de conexión (en producción usa st.secrets o variables de entorno)
AZURE_CONNECTION_STRING = st.secrets.get("AZURE_CONNECTION_STRING", "")
CONTAINER_NAME = st.secrets.get("AZURE_CONTAINER_NAME", "imagenes")

st.title("🖼️ Quitador de fondo + subida a Azure Blob")

uploaded_file = st.file_uploader("Sube tu imagen", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Abrimos la imagen
    image = Image.open(uploaded_file).convert("RGBA")
    st.image(image, caption="Imagen original", use_column_width=True)

    with st.spinner("Procesando imagen..."):
        # 🔹 Remover fondo
        result_image = remove(image)
        # 🔹 Redimensionar a 600x600
        resized_image = result_image.resize((600, 600), Image.LANCZOS)

        st.image(resized_image, caption="Imagen sin fondo (600x600)", use_column_width=True)

        # Guardamos en buffer en memoria
        buffer = io.BytesIO()
        resized_image.save(buffer, format="PNG")
        buffer.seek(0)

        # 👉 Botón de descarga
        st.download_button(
            label="📥 Descargar imagen procesada",
            data=buffer,
            file_name="imagen_sin_fondo_600x600.png",
            mime="image/png"
        )

        # 👉 Subida a Azure Blob
        if AZURE_CONNECTION_STRING != "":
            try:
                st.write("🔄 Subiendo imagen al blob storage...")

                # Cliente de Azure
                blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
                blob_client = blob_service_client.get_blob_client(
                    container=CONTAINER_NAME,
                    blob=uploaded_file.name.replace(" ", "_")
                )

                # Regresamos buffer al inicio antes de subir
                buffer.seek(0)
                blob_client.upload_blob(buffer, overwrite=True)

                blob_url = blob_client.url
                st.success("✅ Imagen subida con éxito a Azure Blob Storage.")
                st.markdown(f"[🔗 Ver imagen en Azure]({blob_url})")

            except Exception as e:
                st.error(f"❌ Error al subir a Azure: {e}")
        else:
            st.warning("⚠️ No se configuró la conexión a Azure. Agrega tu connection string en `st.secrets`.")
