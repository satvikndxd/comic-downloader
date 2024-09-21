from flask import Flask, render_template, request, send_file
import os
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageOps
from fpdf import FPDF
import zipfile
import io

app = Flask(__name__)

def download_comic_images(comic_url):
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(comic_url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    image_tags = soup.find_all('img', {'class': 'wp-manga-chapter-img'})
    if not image_tags:
        image_tags = soup.find_all('img')

    if not os.path.exists('comics'):
        os.makedirs('comics')

    image_urls = []
    for idx, img_tag in enumerate(image_tags):
        image_url = img_tag.get('data-src') or img_tag.get('src')
        
        if image_url and 'readallcomics.com' in image_url.lower():
            continue

        if image_url:
            image_urls.append(image_url)
            img_data = requests.get(image_url).content
            image_path = f'comics/page_{idx+1}.jpg'
            with open(image_path, 'wb') as handler:
                handler.write(img_data)

    return len(image_urls)

def create_cbz(comic_name, num_pages):
    cbz_filename = f"{comic_name}.cbz"

    with zipfile.ZipFile(cbz_filename, 'w') as cbz:
        for i in range(1, num_pages + 1):
            image_path = f'comics/page_{i}.jpg'
            
            if not os.path.exists(image_path):
                continue

            image = Image.open(image_path)
            if image.mode != 'RGB':
                image = image.convert('RGB')

            image_cropped = ImageOps.crop(image, border=5)
            bbox = image_cropped.getbbox()
            if bbox:
                image_cropped = image_cropped.crop(bbox)

            cropped_image_path = f'comics/cropped_page_{i}.jpg'
            image_cropped.save(cropped_image_path, 'JPEG', quality=95)
            cbz.write(cropped_image_path, f"page_{i}.jpg")
            os.remove(cropped_image_path)

    return cbz_filename

def create_pdf(comic_name, num_pages):
    pdf_filename = f"{comic_name}.pdf"
    pdf = FPDF()
    
    for i in range(1, num_pages + 1):
        image_path = f'comics/page_{i}.jpg'

        if not os.path.exists(image_path):
            continue

        image = Image.open(image_path)
        image.thumbnail((pdf.w, pdf.h))

        if image.mode != 'RGB':
            image = image.convert('RGB')

        pdf.add_page()
        pdf.image(image_path, x=0, y=0, w=pdf.w, h=pdf.h)

    pdf.output(pdf_filename)
    return pdf_filename

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        comic_url = request.form['comic_url']
        format_choice = request.form['format_choice']
        
        comic_name = comic_url.split('/')[-2]
        num_pages = download_comic_images(comic_url)
        
        if format_choice == 'pdf':
            pdf_filename = create_pdf(comic_name, num_pages)
            return send_file(pdf_filename, as_attachment=True)
        elif format_choice == 'cbz':
            cbz_filename = create_cbz(comic_name, num_pages)
            return send_file(cbz_filename, as_attachment=True)
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)