from flask import Flask, render_template, request, send_file
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import os
import io

app = Flask(__name__)

# Dummy data for dropdowns
ACTIVITIES = ['Receiving', 'Stocking', 'Picking', 'Shipping']
WAREHOUSES = ['Warehouse A', 'Warehouse B', 'Warehouse C']
UPLOAD_FOLDER = 'uploads'
PDF_TEMPLATE_IMAGE = 'static/pdf_header_template.png'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html', activities=ACTIVITIES, warehouses=WAREHOUSES)

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    # Get form data
    activity = request.form.get('activity')
    warehouse = request.form.get('warehouse')
    date_str = request.form.get('date')
    images = request.files.getlist('images')

    # Create a PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    # Add header image from a template
    if os.path.exists(PDF_TEMPLATE_IMAGE):
        header_image = Image(PDF_TEMPLATE_IMAGE, width=7.5 * inch, height=1 * inch)
        story.append(header_image)
        story.append(Spacer(1, 0.2 * inch))

    # Define custom styles
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12,
        alignment=1, # Center alignment
    )
    subheader_style = ParagraphStyle(
        'Subheader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=6,
        alignment=1, # Center alignment
    )

    # Add text content
    story.append(Paragraph(f'<b>Activity:</b> {activity}', header_style))
    story.append(Paragraph(f'<b>Warehouse:</b> {warehouse} | <b>Date:</b> {date_str}', subheader_style))
    story.append(Spacer(1, 0.2 * inch))

    # Process and save images
    image_paths = []
    for img in images:
        if img.filename != '':
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], img.filename)
            img.save(filepath)
            image_paths.append(filepath)

    if image_paths:
        # Create a grid of images using a ReportLab Table
        num_images = len(image_paths)
        
        # Determine number of columns and a reasonable image size
        if num_images == 1:
            columns = 1
        elif num_images <= 4:
            columns = 2
        else:
            columns = 3 # A 3-column grid for more than 4 images
        
        # Calculate image width and height based on columns and page size
        margin = 0.5 * inch
        page_width = letter[0] - 2 * margin
        image_spacing = 5 # 5px margin as requested, which translates to ReportLab's internal unit
        
        # The image_width is the available page width divided by the number of columns, with spacing removed
        img_width = (page_width - (columns - 1) * image_spacing) / columns
        img_height = img_width # Keep aspect ratio square for the grid

        # Organize images into rows for the table
        data = []
        row = []
        for i, path in enumerate(image_paths):
            row.append(Image(path, width=img_width, height=img_height))
            if len(row) == columns:
                data.append(row)
                row = []
        if row:
            data.append(row)

        # Create the Table and its style
        # The 'GRID' command applies a grid of lines, which mimics the margin
        # We can create a more sophisticated style to represent the 5px margin
        
        # Create a Table with a custom style for spacing
        image_table = Table(data, colWidths=[img_width] * columns)
        
        table_style = TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), image_spacing / 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), image_spacing / 2),
            ('TOPPADDING', (0, 0), (-1, -1), image_spacing / 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), image_spacing / 2),
            ('GRID', (0,0), (-1,-1), 0.25, colors.black),
        ])
        image_table.setStyle(table_style)

        story.append(image_table)

    doc.build(story)

    # Clean up uploaded images
    for path in image_paths:
        os.remove(path)

    # Prepare response
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='report.pdf', mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True)