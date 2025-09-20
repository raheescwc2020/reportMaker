from flask import Flask, render_template, request, send_file
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import os
import io
import datetime # Import the datetime module

app = Flask(__name__)

# Updated list of activities
ACTIVITIES = [
    'SWACHTA KI BHAGIDARI WITH PUBLIC PARTICIPANTS',
    'AWARENESS PROGRAM',
    'HYGIENE FOCUSED',
    'CREATING AWARENESS IN SCHOOL CHILDREN',
    'SAFAI MITRA SURAKSHA SHIVIR',
    'EK DIN, EK GHANTA, EK SATH – JOINING HANDS FOR NATION’S CLEANLINESS',
    'FOR CREATING AWARENESS',
    'CLEANLINESS TARGET UNIT',
    'SAFAI MITRA WELFARE SCHEME WORKSHOP',
    'MOTIVATING SAFAI MITRA',
    'SWACHH BHARAT DIWAS'
]

# Dummy data for dropdowns
WAREHOUSES = [
'CW Kunnamthanam',
'CW Ernakulam',
'CW Kochi (PB)',
'CW Kakkanad',
'CW Kanjikode',
'CW Kakkancherry',
'CW Trichur',
'CW Thalassery',
'CW Edathala',
'CW Kozhikode',
'CW Trivandrum',
'CW Madikkai',
'CW Kannur']


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
    date_str_yyyy_mm_dd = request.form.get('date') # Original date string from form
    activity_details = request.form.get('activity_details') 
    images = request.files.getlist('images')

    # Convert the date string to the desired dd-mm-yyyy format
    try:
        date_object = datetime.datetime.strptime(date_str_yyyy_mm_dd, '%Y-%m-%d')
        date_str_dd_mm_yyyy = date_object.strftime('%d-%m-%Y')
    except (ValueError, TypeError):
        date_str_dd_mm_yyyy = 'N/A' # Handle potential errors if date is not in expected format

    # Define page dimensions and custom margins
    margin = 0
    doc = SimpleDocTemplate(
        io.BytesIO(), 
        pagesize=letter,
        topMargin=margin,
        leftMargin=margin,
        rightMargin=margin,
        bottomMargin=margin
    )
    
    story = []
    styles = getSampleStyleSheet()

    # Add header image from a template
    if os.path.exists(PDF_TEMPLATE_IMAGE):
        # The image will take the full width of the page
        header_image_width = letter[0] 
        header_image_height = 1.0 * inch
        header_image = Image(PDF_TEMPLATE_IMAGE, width=header_image_width, height=header_image_height)
        story.append(header_image)
        # Add a spacer to create a visible break before content
        story.append(Spacer(1, 0.2 * inch))

    # Add content to the story with new margins
    # The content will now be pushed to the left and top
    # We need to manually add margins for the content using a ParagraphStyle
    content_margin_left = 0.5 * inch
    content_margin_top = 0.5 * inch
    
    # Define custom styles with left padding to create a margin
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12,
        alignment=1, # Center alignment
        leftIndent=content_margin_left,
        rightIndent=content_margin_left
    )
    subheader_style = ParagraphStyle(
        'Subheader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=6,
        alignment=1, # Center alignment
        leftIndent=content_margin_left,
        rightIndent=content_margin_left
    )
    
    # New style for the details section
    details_style = ParagraphStyle(
        'Details',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=12,
        leftIndent=content_margin_left,
        rightIndent=content_margin_left,
        leading=14 # Line spacing
    )

    # Add text content using the newly formatted date string
    story.append(Paragraph(f'{activity}', header_style))
    story.append(Paragraph(f'<b>Warehouse:</b> {warehouse} | <b>Date:</b> {date_str_dd_mm_yyyy}', subheader_style))
    story.append(Spacer(1, 0.2 * inch))

    # Add the new activity details section
    if activity_details:
        story.append(Paragraph(f'<b></b>', details_style))
        story.append(Paragraph(activity_details.replace('\n', '<br/>'), details_style))
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
            columns = 3
        
        # Calculate image width and height based on columns and page size
        page_width = letter[0] - 2 * content_margin_left 
        image_spacing = 5 # 5px margin as requested, which translates to ReportLab's internal unit
        
        # The image_width is the available content width divided by the number of columns, with spacing removed
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
        image_table = Table(data, colWidths=[img_width] * columns)
        
        # We use padding in the TableStyle to create the 5px margin between images
        table_style = TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), image_spacing / 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), image_spacing / 2),
            ('TOPPADDING', (0, 0), (-1, -1), image_spacing / 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), image_spacing / 2),
            ('LEFTPADDING', (0, 0), (0, -1), content_margin_left),
            ('RIGHTPADDING', (-1, 0), (-1, -1), content_margin_left),
        ])
        image_table.setStyle(table_style)

        story.append(image_table)

    doc.build(story)

    # Clean up uploaded images
    for path in image_paths:
        os.remove(path)

    # Prepare response
    buffer = doc.filename
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='report.pdf', mimetype='application/pdf')

if __name__ == '__main__':
    app.run(debug=True)