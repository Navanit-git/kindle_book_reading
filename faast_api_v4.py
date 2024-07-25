import os
import shutil
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import ironpdf
import fitz  # PyMuPDF

app = FastAPI()

# Directory to store converted images
IMAGE_DIR = "images"
os.makedirs(IMAGE_DIR, exist_ok=True)

# Serve static files (images)
app.mount("/images", StaticFiles(directory=IMAGE_DIR), name="images")

# Directory containing PDF files
PDF_DIR = "/Users/navanitdubey/python_projects/kindle_test/pdfs"

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
        raise HTTPException(status_code=500, detail=f"Error extracting content from PDF: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def root():
    pdf_files = get_pdf_files()
    pdf_links = ""
    for pdf_name in pdf_files.keys():
        pdf_links += f"""
        <h2>{pdf_name}</h2>
        <ul>
            <li><a href="/view-pdf/{pdf_name}/text_view">Text View</a></li>
            <li><a href="/view-pdf/{pdf_name}/image_view">Image View</a></li>
        </ul>
        """
    
    return f"""
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

@app.get("/view-pdf/{file_name}/{view_type}", response_class=HTMLResponse)
async def view_pdf(file_name: str, view_type: str):
    pdf_files = get_pdf_files()
    if file_name not in pdf_files:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    pdf_file = pdf_files[file_name]
    
    if view_type not in ["text_view", "image_view"]:
        raise HTTPException(status_code=400, detail="Invalid view type. Use 'text_view' or 'image_view'.")
    
    try:
        if view_type == "text_view":
            # Extract text content from PDF
            content = extract_content_from_pdf(pdf_file)
            
            # Prepare HTML content for text view
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
            
            # Add text content to HTML
            for i, page in enumerate(content, 1):
                html_content += f'<div class="page"><div class="page-number">Page {i}</div>'
                html_content += f'<div class="page-content">{page["text"]}</div></div>'

            html_content += """
                    </div>
                </body>
            </html>
            """
        
        else:  # image_view
            # Convert PDF to images
            image_paths = convert_pdf_to_images(pdf_file, dpi=300)
            
            # Prepare HTML content for image view
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
            
            # Add images to HTML content
            for image_path in image_paths:
                html_content += f'<img src="/images/{image_path}" alt="{image_path}" class="pdf-page"><br>'

            html_content += """
                    </div>
                </body>
            </html>
            """
        
        return HTMLResponse(content=html_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    # Clean up the images directory on server shutdown
    shutil.rmtree(IMAGE_DIR)

if __name__ == "__main__":
    import uvicorn
    print("Starting server. Available endpoints:")
    print("  - GET /")
    print("  - GET /view-pdf/{file_name}/text_view")
    print("  - GET /view-pdf/{file_name}/image_view")
    uvicorn.run(app, host="0.0.0.0", port=8000)