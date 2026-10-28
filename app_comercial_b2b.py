import os
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from PIL import Image
from rembg import remove
from datetime import datetime
from urllib.parse import urlparse
import streamlit as st

# Configuración visual de la página
st.set_page_config(
    page_title="B2B Studio Catalog AI",
    page_icon="🛍️",
    layout="wide"
)

# Estilo visual moderno corporativo
st.markdown("""
    <style>
    .main-header { font-size: 28px; font-weight: 700; color: #1E3A8A; }
    .sub-header { font-size: 16px; color: #64748B; }
    .metric-card { background-color: #F8FAFC; padding: 20px; border-radius: 10px; border: 1px solid #E2E8F0; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">🛍️ B2B Studio Catalog AI — Panel de Transformación</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Automatización inteligente de scraping, remoción de fondos con IA y normalización de catálogos mayoristas.</p>', unsafe_allow_html=True)
st.divider()

# Barra lateral para configuraciones de marca
with st.sidebar:
    st.header("⚙️ Configuración de Estudio")
    resolucion = st.selectbox("Resolución de Salida", [1200, 1000, 800], index=0)
    formato_fondo = st.color_picker("Color de Fondo", "#FFFFFF")
    st.info("💡 Motor de IA activo: Bria RMBG / ONNX Runtime local.")

# Sección Principal de Entrada
url_objetivo = st.text_input("🔗 URL del Proveedor o E-commerce Mayorista:", placeholder="https://ejemplo.com/")

if st.button("🚀 Ejecutar Pipeline de Transformación", type="primary"):
    if not url_objetivo:
        st.warning("⚠️ Por favor, ingresá una URL válida antes de continuar.")
    else:
        dir_raw = "fotos_descargadas_temp"
        dir_output = "peluches_optimizados_b2b"
        os.makedirs(dir_raw, exist_ok=True)
        os.makedirs(dir_output, exist_ok=True)

        productos_data = []

        # Contenedores de Estado en Streamlit
        status_box = st.status("🔄 Iniciando proceso automatizado...", expanded=True)

        try:
            # ----------------------------------------------------
            # PASO 1: SCRAPING
            # ----------------------------------------------------
            status_box.update(label="🌐 Fase 1/3: Extrayendo datos y descargando assets de la web...", state="running")
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url_objetivo, wait_until="domcontentloaded", timeout=45000)
                time.sleep(3)
                for _ in range(3):
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(1.5)
                
                content = page.content()
                soup = BeautifulSoup(content, "html.parser")
                browser.close()

            items = soup.select(".product-item, .product-card, .product, article.product-miniature, div.thumbnail-container, li.product")
            if not items:
                items = soup.find_all(["div", "article", "li"], class_=lambda c: c and any(k in c.lower() for k in ["product", "item", "card"]))

            headers_req = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

            for idx, item in enumerate(items):
                try:
                    titulo_el = item.select_one("h2, h3, h4, .title, .name, [class*='title'], [class*='name'], a")
                    nombre = titulo_el.get_text(strip=True) if titulo_el else None
                    if not nombre or len(nombre) < 2 or len(nombre) > 160:
                        continue

                    precio_el = item.select_one(".price, .amount, [class*='price'], span.money")
                    precio = precio_el.get_text(strip=True) if precio_el else "Consultar"

                    img_el = item.find("img")
                    img_src = ""
                    if img_el:
                        img_src = img_el.get("data-src") or img_el.get("src") or ""

                    nombre_archivo_raw = f"raw_{idx:03d}.jpg"
                    ruta_raw = os.path.join(dir_raw, nombre_archivo_raw)
                    
                    if img_src:
                        if not img_src.startswith("http"):
                            parsed = urlparse(url_objetivo)
                            img_src = f"{parsed.scheme}://{parsed.netloc}{img_src}" if img_src.startswith("/") else f"{parsed.scheme}://{parsed.netloc}/{img_src}"
                        try:
                            img_data = requests.get(img_src, headers=headers_req, timeout=10).content
                            with open(ruta_raw, 'wb') as handler:
                                handler.write(img_data)
                        except Exception:
                            ruta_raw = None

                    sku = f"B2B-{idx+1:03d}"
                    nombre_foto_b2b = f"{idx:03d}_b2b.png"

                    productos_data.append({
                        "SKU": sku,
                        "Producto": nombre,
                        "Precio_Mayorista": precio,
                        "Imagen_Optimizada": nombre_foto_b2b,
                        "Ruta_Raw": ruta_raw if img_src else None
                    })
                except Exception:
                    continue

            if not productos_data:
                status_box.update(label="❌ No se encontraron productos estructurados en la URL.", state="error")
                st.stop()

            st.success(f"✅ Fase 1 completada: {len(productos_data)} productos detectados.")

            # ----------------------------------------------------
            # PASO 2: IA & PROCESAMIENTO DE IMÁGENES
            # ----------------------------------------------------
            status_box.update(label="🎨 Fase 2/3: Aplicando inteligencia artificial y normalización de estudio...", state="running")
            progress_bar = st.progress(0)

            total_productos = len(productos_data)
            for idx, prod in enumerate(productos_data):
                ruta_raw = prod["Ruta_Raw"]
                nombre_foto_b2b = prod["Imagen_Optimizada"]
                ruta_salida = os.path.join(dir_output, nombre_foto_b2b)

                if ruta_raw and os.path.exists(ruta_raw) and os.path.getsize(ruta_raw) > 1024:
                    try:
                        with Image.open(ruta_raw) as input_image:
                            input_image.verify()
                        
                        input_image = Image.open(ruta_raw)
                        output_image = remove(input_image)

                        if output_image.mode != "RGBA":
                            output_image = output_image.convert("RGBA")

                        target_size = resolucion
                        output_image.thumbnail((target_size - 100, target_size - 100), Image.Resampling.LANCZOS)

                        fondo = Image.new("RGBA", (target_size, target_size), (255, 255, 255, 255))
                        paste_x = (target_size - output_image.width) // 2
                        paste_y = (target_size - output_image.height) // 2

                        fondo.paste(output_image, (paste_x, paste_y), output_image)
                        fondo.convert("RGB").save(ruta_salida, "PNG", optimize=True)
                    except Exception:
                        pass
                
                progress_bar.progress((idx + 1) / total_productos)

            status_box.update(label="📊 Fase 3/3: Generando planillas maestras de exportación...", state="complete")

            # ----------------------------------------------------
            # PASO 3: EXPORTACIÓN Y DESCARGAS
            # ----------------------------------------------------
            df = pd.DataFrame(productos_data).drop(columns=["Ruta_Raw"])
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            excel_file = f"catalogo_maestro_{timestamp}.xlsx"
            df.to_excel(excel_file, index=False)

            st.divider()
            st.markdown("### 🎉 ¡Catálogo Transformado con Éxito!")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Productos Procesados", len(df))
            with col2:
                st.metric("Formato de Imágenes", f"{resolucion}x{resolucion}px (Fondo Blanco)")

            # Vista Previa en Tabla
            st.dataframe(df, use_container_width=True)

            # Botón de Descarga Excel
            with open(excel_file, "rb") as f:
                st.download_button(
                    label="📥 Descargar Planilla Excel Comercial",
                    data=f,
                    file_name=excel_file,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            status_box.update(label=f"❌ Error crítico en el pipeline: {str(e)}", state="error")