import os
import sys
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from PIL import Image
from rembg import remove
from datetime import datetime
from urllib.parse import urlparse

def ejecutar_pipeline_b2b(url_objetivo):
    print("="*60)
    print(f"🚀 [PIPELINE B2B TOTAL] Iniciando proceso para: {url_objetivo}")
    print("="*60)
    
    # Directorios de trabajo
    dir_raw = "fotos_descargadas_temp"
    dir_output = "peluches_optimizados_b2b"
    os.makedirs(dir_raw, exist_ok=True)
    os.makedirs(dir_output, exist_ok=True)
    
    productos_data = []
    
    # ----------------------------------------------------
    # PASO 1: SCRAPING QUIRÚRGICO Y DESCARGA DE ASSETS
    # ----------------------------------------------------
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 🌐 [FASE 1] Extrayendo datos y descargando assets...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            # Usamos 'domcontentloaded' para evitar bloqueos por tráfico de red infinito (chats, pixeles)
            page.goto(url_objetivo, wait_until="domcontentloaded", timeout=45000)
            print("⏳ Esperando renderizado de la tienda...")
            time.sleep(4)
            
            for _ in range(3): # Scroll para lazy loading
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(1.5)
        except Exception as e:
            print(f"❌ Error al navegar en la web: {e}")
            browser.close()
            return
            
        content = page.content()
        soup = BeautifulSoup(content, "html.parser")
        browser.close()

    selectors = [
        ".product-item", ".product-card", ".product", 
        "article.product-miniature", "div.thumbnail-container", 
        "li.product", ".grid-product", ".os-product", ".card-product"
    ]
    
    items = []
    for sel in selectors:
        found = soup.select(sel)
        if len(found) > 3:  # Umbral óptimo para detectar tarjetas reales
            items = found
            break
    
    if not items:
        items = [tag for tag in soup.find_all(["div", "article", "li"]) if tag.find("img") and tag.find(text=True)]

    print(f"📦 Se detectaron {len(items)} bloques candidatos en la web.")

    headers_req = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    valid_idx = 1

    for item in items:
        try:
            titulo_el = item.select_one("h2, h3, h4, .title, .name, [class*='title'], [class*='name'], a")
            nombre = titulo_el.get_text(strip=True) if titulo_el else None
            if not nombre or len(nombre) < 2 or len(nombre) > 160:
                continue

            # Filtro estricto antibasura (ignorar reseñas, menús o textos institucionales)
            basura_keywords = ["customer say", "review", "shipping", "contacto", "carrito", "cart", "wishlist", "faq"]
            if any(kw in nombre.lower() for kw in basura_keywords):
                continue

            precio_el = item.select_one(".price, .amount, [class*='price'], span.money")
            precio = precio_el.get_text(strip=True) if precio_el else "Consultar"

            img_el = item.find("img")
            img_src = ""
            if img_el:
                img_src = img_el.get("data-src") or img_el.get("src") or img_el.get("data-lazy-src") or ""

            # Descartar si no hay foto real o si es un logo/ícono decorativo
            if not img_src or "logo" in img_src.lower() or "icon" in img_src.lower():
                continue

            if not img_src.startswith("http"):
                parsed = urlparse(url_objetivo)
                img_src = f"{parsed.scheme}://{parsed.netloc}{img_src}" if img_src.startswith("/") else f"{parsed.scheme}://{parsed.netloc}/{img_src}"

            nombre_archivo_raw = f"raw_{valid_idx:03d}.jpg"
            ruta_raw = os.path.join(dir_raw, nombre_archivo_raw)

            # Descarga y validación estricta de peso (> 1KB)
            img_data = requests.get(img_src, headers=headers_req, timeout=10).content
            if len(img_data) < 1024:
                continue

            with open(ruta_raw, 'wb') as handler:
                handler.write(img_data)

            sku = f"B2B-{valid_idx:03d}"
            nombre_foto_b2b = f"{valid_idx:03d}_b2b.png"

            productos_data.append({
                "SKU": sku,
                "Producto": nombre,
                "Precio_Mayorista": precio,
                "Imagen_Optimizada": nombre_foto_b2b,
                "Ruta_Raw": ruta_raw
            })
            valid_idx += 1
        except Exception:
            continue

    print(f"✅ [FASE 1 COMPLETADA] {len(productos_data)} registros limpios y validados 1:1.")

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

                # 💡 Esto actualiza el texto en tiempo real en la pantalla web
                status_box.update(label=f"🎨 Fase 2/3: Procesando [{idx+1}/{total_productos}] — {prod['Producto'][:30]}...")

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
    # PASO 3: EXPORTACIÓN DE LA PLANILLA MAESTRA B2B
    # ----------------------------------------------------
    df = pd.DataFrame(productos_data)
    df_export = df.drop(columns=["Ruta_Raw"])
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_file = f"catalogo_maestro_b2b_{timestamp}.xlsx"
    csv_file = f"catalogo_maestro_b2b_{timestamp}.csv"

    df_export.to_excel(excel_file, index=False)
    df_export.to_csv(csv_file, index=False, encoding="utf-8-sig")

    print("\n" + "="*60)
    print("🎉 [PROCESO EXITOSO] ¡Pipeline B2B Finalizado con Éxito!")
    print(f"📊 Planilla Excel: ./{excel_file}")
    print(f"📄 Planilla CSV:   ./{csv_file}")
    print(f"📁 Fotos de Estudio: ./{dir_output}/")
    print("="*60)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url_input = sys.argv[1]
    else:
        url_input = input("Ingresá la URL del sitio web del proveedor mayorista: ").strip()
    
    ejecutar_pipeline_b2b(url_input)