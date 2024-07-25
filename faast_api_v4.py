import os
import shutil
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import ironpdf
import fitz  # PyMuPDF

app = FastAPI()

# Directory to store converted images and HTML files
OUTPUT_DIR = "docs"
IMAGE_DIR = os.path.join(OUTPUT_DIR, "images")
os.makedirs(IMAGE_DIR, exist_ok=True)

# Directory containing PDF files
PDF_DIR = "pdfs"

def get_pdf_files():
    pdf_files = {}
    for filename in os.listdir(PDF_DIR):
        if filename.lower().endswith('.pdf'):
            pdf_name = os.path.splitext(filename)[0]
            pdf_files[pdf_name] = os.path.join(PDF_DIR, filename)
    return pdf_files

def convert_pdf_to_images(pdf_file, dpi=300):
    pdf = ironpdf.PdfDocument.FromFile(pdf_file)
    base_filename = os.path.splitext(os.path.basename(pdf_file))[0]
    # Extract all pages to the images folder as PNG files with higher DPI
    pdf.RasterizeToImageFiles(os.path.join(IMAGE_DIR, f"{base_filename}_page_{{0}}.png"), dpi=dpi)
    # Get the list of image files in the folder
    image_paths = []
    for filename in os.listdir(IMAGE_DIR):
        if filename.lower().endswith(".png") and base_filename in filename:
            image_paths.append(filename)
    return sorted(image_paths)

def extract_content_from_pdf(pdf_file):
    content = []
    try:
        doc = fitz.open(pdf_file)
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            content.append({"text": text})
        return content
    except Exception as e:
        print(f"Error extracting content from PDF: {str(e)}")
        return []

def generate_index_html():
    pdf_files = get_pdf_files()
    pdf_links = ""
    for pdf_name in pdf_files.keys():
        pdf_links += f"""
        <h2>{pdf_name}</h2>
        <ul>
            <li><a href="{pdf_name}_text.html">Text View</a></li>
            <li><a href="{pdf_name}_image.html">Image View</a></li>
        </ul>
        """
    
    html_content = f"""
    <html>
        <head>
            <title>PDF Viewer</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }}
                h1 {{ color: #333; }}
                a {{ color: #007bff; text-decoration: none; }}
                a:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <h1>PDF Viewer</h1>
            <p>Click to view the PDF content:</p>
            {pdf_links}
        </body>
    </html>
    """
    
    with open(os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_content)

def generate_text_view(file_name, pdf_file):
    content = extract_content_from_pdf(pdf_file)
    
    html_content = f"""
    <html>
        <head>
            <title>PDF Text Viewer - {file_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; margin: 0 auto; max-width: 800px; }}
                h1 {{ color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }}
                .page {{ margin-bottom: 20px; border: 1px solid #ddd; padding: 10px; }}
                .page-number {{ font-weight: bold; margin-bottom: 10px; }}
                .page-content {{ white-space: pre-wrap; }}
            </style>
        </head>
        <body>
            <h1>PDF Text Content - {file_name}</h1>
            <div id="pdf-content">
    """
    
    for i, page in enumerate(content, 1):
        html_content += f'<div class="page"><div class="page-number">Page {i}</div>'
        html_content += f'<div class="page-content">{page["text"]}</div></div>'

    html_content += """
            </div>
        </body>
    </html>
    """
    
    with open(os.path.join(OUTPUT_DIR, f"{file_name}_text.html"), "w", encoding="utf-8") as f:
        f.write(html_content)

def generate_image_view(file_name, pdf_file):
    image_paths = convert_pdf_to_images(pdf_file, dpi=300)
    
    html_content = f"""
    <html>
        <head>
            <title>PDF Image Viewer - {file_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; margin: 0 auto; }}
                h1 {{ color: #333; border-bottom: 2px solid #333; padding-bottom: 10px; }}
                #pdf-container {{ max-width: 800px; margin: 0 auto; }}
                .pdf-page {{ width: 100%; margin-bottom: 20px; }}
                #zoom-controls {{ position: fixed; top: 10px; right: 10px; background: white; padding: 10px; border: 1px solid #ddd; }}
            </style>
            <script>
                function changeZoom() {{
                    var zoom = document.getElementById('zoom').value;
                    var container = document.getElementById('pdf-container');
                    container.style.transform = `scale(${{zoom}})`;
                    container.style.transformOrigin = 'top center';
                }}
            </script>
        </head>
        <body>
            <h1>PDF Image Content - {file_name}</h1>
            <div id="zoom-controls">
                <label for="zoom">Zoom:</label>
                <input type="number" id="zoom" name="zoom" min="0.1" max="3.0" step="0.1" value="1.0" onchange="changeZoom()">
            </div>
            <div id="pdf-container">
    """
    
    for image_path in image_paths:
        html_content += f'<img src="images/{image_path}" alt="{image_path}" class="pdf-page"><br>'

    html_content += """
            </div>
        </body>
    </html>
    """
    
    with open(os.path.join(OUTPUT_DIR, f"{file_name}_image.html"), "w", encoding="utf-8") as f:
        f.write(html_content)

def generate_static_files():
    pdf_files = get_pdf_files()
    generate_index_html()
    for file_name, pdf_file in pdf_files.items():
        generate_text_view(file_name, pdf_file)
        generate_image_view(file_name, pdf_file)

if __name__ == "__main__":
    generate_static_files()
    print("Static files generated in the 'docs' folder.")