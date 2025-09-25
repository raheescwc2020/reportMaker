import io
import datetime  # Import the datetime module
import json
import os
from flask import Flask, render_template, request, send_file

from reportlab.platypus import SimpleDocTemplate, Image, Table, TableStyle, Spacer, Paragraph
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER

app = Flask(__name__)

# Updated list of activities
ACTIVITIES = [
    'SWACHTA KI BHAGIDARI WITH PUBLIC PARTICIPANTS',
    'AWARENESS PROGRAM',
    'HYGIENE FOCUSED',
    'CREATING AWARENESS IN SCHOOL CHILDREN',
    'SAFAI MITRA SURAKSHA SHIVIR',
    'EK DIN, EK GHANTA, EK SATH - JOINING HANDS FOR NATIONS CLEANLINESS',
    'FOR CREATING AWARENESS',
    'CLEANLINESS TARGET UNIT',
    'SAFAI MITRA WELFARE SCHEME WORKSHOP',
    'MOTIVATING SAFAI MITRA',
    'SWACHH BHARAT DIWAS'
]

# Consolidated list of all warehouses from the previous table and the provided file
REGIONAL_WAREHOUSES = {

    'Ahmedabad': ['CW Shahalam', 'CW Anand', 'CW Baroda-I', 'CW Pipavav', 'CW Rajkot', 'CW Surat', 'CW Dantewada', 'CW Jagdalpur', 'CW Raigarh', 'CW Raipur', 'CW Kandla Port', 'CFS Mundra', 'CRWC Kandla', 'CW Rajkot (Hired)', 'CW Jamnagar'],
    'Bangalore': ['CW Belgachhia', 'CW Chikkaballapur', 'CW Tumkur', 'CW Belgaum', 'CW Mysore', 'CW Gadag', 'CW Dharwad', 'CW Mandya', 'CW Hubballi', 'CW Mangalore', 'CW Panambur'],
    'Bhopal': ['CW Bhopal', 'CW Jabalpur', 'CW Rewa', 'CW Chhindwara', 'CW Sagar', 'CW Neemuch', 'CW Damoh', 'CW Katni', 'CW Gwalior', 'CW Satna', 'CW Khandwa'],
    'Bhubaneshwar': ['CW Junagarh', 'CW Kendupalli-I', 'CW Kendupalli-II', 'CW Koksara', 'CW Kalamati', 'CW Nabrangpur', 'CW Bhubaneswar-I', 'CW Bhubaneswar-II', 'CW Balasore', 'CW Cuttack', 'CW Rourkela', 'CW Sambalpur', 'CW Jeypore', 'CW Paradeep', 'CW Angul', 'CW Bhawanipatna', 'CW Talcher'],
    'Chandigarh': ['CW Chandigarh', 'CW Faridkot', 'CW Amritsar', 'CW Firozpur', 'CW Ludhiana', 'CW Patiala', 'CW Mohali', 'CW Jalandhar', 'CW Gurdaspur', 'CW Sangrur', 'CW Bathinda', 'CW Samana', 'CW Kotkapura', 'CW Muktsar', 'CW Pathankot', 'CW Rupnagar', 'CW Sirhind', 'CW Hoshiarpur', 'CW Abohar', 'CW Malout', 'CW Phagwara', 'CW Moga', 'CW Nawanshahar', 'CW Tarntaran'],
    'Guwahati': ['CW Agartala', 'CW Dimapur', 'CW Imphal', 'CW Silchar', 'CW Shillong', 'CW Mirza', 'CW Guwahati', 'CW Dhaligaon', 'CW Goalpara', 'CW Jorhat', 'CW Dibrugarh', 'CW Aizawl', 'CW Gangtok', 'CW Silchar'],
    'Hyderabad': ['CW Hyderabad', 'CW Godavari', 'CW Vijayawada', 'CW Visakhapatnam', 'CW Kakinada', 'CW Warangal', 'CW Khammam', 'CW Karimnagar', 'CW Tirupati', 'CW Guntur'],
    'Jaipur': ['CW Jaipur', 'CW Alwar', 'CW Bikaner', 'CW Bharatpur', 'CW Jodhpur', 'CW Pali', 'CW Sikar', 'CW Kota', 'CW Bundi'],
    'Kolkata': ['CW Kolkata', 'CW Howrah', 'CW Siliguri', 'CW Durgapur', 'CW Malda', 'CW Krishnanagar', 'CW Port Blair', 'CW Balurghat', 'CW Haldia', 'CW Ranaghat'],
    'Lucknow': ['CW Lucknow', 'CW Varanasi', 'CW Gorakhpur', 'CW Kanpur', 'CW Meerut', 'CW Ghaziabad', 'CW Bareilly', 'CW Sultanpur', 'CW Budaun', 'CW Mathura', 'CW Allahabad'],
    'Mumbai': ['CW Mumbai', 'CW Thane', 'CW Aurangabad', 'CW Nashik', 'CW Pune', 'CW Nagpur', 'CW Shirwal', 'CW Amravati', 'CW Ahmednagar', 'CW Latur', 'CW Akola', 'CW Jalna', 'CW Washim'],
    'New Delhi': ['CW Delhi', 'CW Khera Kalan', 'CW Nangloi', 'CW Narela', 'CW Patparganj', 'CW Bawana', 'CW Shahdara', 'CW Karnal', 'CW Panipat', 'CW Rohtak', 'CW Sonipat', 'CW Rewari', 'CW Ambala Cantt', 'CW Gurugram', 'CW Hisar', 'CW Jind', 'CW Yamunanagar', 'CW Kaithal'],
    'Patna': ['CW Patna', 'CW Muzaffarpur', 'CW Gaya', 'CW Purnia', 'CW Jamshedpur', 'CW Ranchi', 'CW Bokaro', 'CW Dhanbad', 'CW Adityapur'],
    'Chennai': ['CW Chennai', 'CW Coimbatore', 'CW Madurai', 'CW Trichy', 'CW Dindigul', 'CW Karur', 'CW Sivagangai', 'CW Tuticorin', 'CW Nagercoil'],
    'Kochi': ['Regional Office - Kochi','CW Kunnamthanam', 'CW Ernakulam', 'CW Kochi (PB)', 'CW Kakkanad', 'CW Kanjikode', 'CW Kakkancherry', 'CW Trichur', 'CW Thalassery', 'CW Edathala', 'CW Kozhikode', 'CW Trivandrum', 'CW Madikkai', 'CW Kannur']
}

UPLOAD_FOLDER = 'uploads'
PDF_TEMPLATE_IMAGE = 'static/pdf_header_template.png'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    # Get a sorted list of regions to populate the first dropdown
    regions = sorted(REGIONAL_WAREHOUSES.keys())
    return render_template('index.html', activities=ACTIVITIES, regional_warehouses=REGIONAL_WAREHOUSES, regions=regions)

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    # Mapping from SWACHH UTSAV 2025 activity to ACTIVITY NAME
    activity_name_map = {
        'SWACHTA KI BHAGIDARI WITH PUBLIC PARTICIPANTS': 'Banner Display and Pledge',
        'AWARENESS PROGRAM': 'Awareness programmes for labours and stake holders at the Warehouses',
        'HYGIENE FOCUSED': 'Distribution of Dustbin, Gloves, Mask etc to various units like health centres, anganwadis etc.',
        'CREATING AWARENESS IN SCHOOL CHILDREN': 'Drawing or Essay writing Competition in schools',
        'SAFAI MITRA SURAKSHA SHIVIR': 'Eye Check up camp for Safaimitra',
        'EK DIN, EK GHANTA, EK SATH - JOINING HANDS FOR NATIONS CLEANLINESS': 'Cleanliness drive in RO/All Warehouses.',
        'FOR CREATING AWARENESS': 'Bag distribution at prominent locations',
        'CLEANLINESS TARGET UNIT': 'Cleanliness drive CTUs',
        'SAFAI MITRA WELFARE SCHEME WORKSHOP': 'Workshop for Safaimitra',
        'MOTIVATING SAFAI MITRA': 'Facilitation of Safaimitra',
        'SWACHH BHARAT DIWAS': '"Swachh Bharat Diwas" Plantation Drive'
    }

    # Get form data
    activity = request.form.get('activity')
    region = request.form.get('region')
    warehouse = request.form.get('warehouse')
    date_str_yyyy_mm_dd = request.form.get('date')
    activity_details = request.form.get('activity_details')
    images = request.files.getlist('images')

    # Get the corresponding "ACTIVITY NAME" from the map
    activity_name = activity_name_map.get(activity, 'N/A')

    # Convert the date string to the desired dd-mm-yyyy format
    try:
        date_object = datetime.datetime.strptime(date_str_yyyy_mm_dd, '%Y-%m-%d')
        date_str_dd_mm_yyyy = date_object.strftime('%d-%m-%Y')
    except (ValueError, TypeError):
        date_str_dd_mm_yyyy = 'N/A'

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
        header_image_width = letter[0]
        header_image_height = 1.0 * inch
        header_image = Image(PDF_TEMPLATE_IMAGE, width=header_image_width, height=header_image_height)
        story.append(header_image)
        story.append(Spacer(1, 0.2 * inch))

    # Add content to the story with new margins
    content_margin_left = 0.5 * inch

    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=6,
        alignment=1,
        leftIndent=content_margin_left,
        rightIndent=content_margin_left
    )
    subheader_style = ParagraphStyle(
        'Subheader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        alignment=1,
        leftIndent=content_margin_left,
        rightIndent=content_margin_left
    )
    details_style = ParagraphStyle(
        'Details',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=12,
        leftIndent=content_margin_left,
        rightIndent=content_margin_left,
        leading=14
    )

    # Get the default stylesheet
    styles = getSampleStyleSheet()
    # Add text content
    header_style = ParagraphStyle(
        'UnderlinedHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=16,
        alignment=TA_CENTER,
        underline=True
    )

    # Create a new style for the smaller, bolded activity name
    activity_name_style = ParagraphStyle(
        'BoldActivityName',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,  # Adjust the size as needed
        leading=14,
        alignment=TA_CENTER
    )

    # Your existing code with the new styles
    story.append(Paragraph(f'{activity}', header_style))
    story.append(Paragraph(f'{activity_name}', activity_name_style))
    story.append(Paragraph(f'<b>Location:</b> {warehouse} under {region} Region | <b>Date:</b> {date_str_dd_mm_yyyy}', subheader_style))
    story.append(Spacer(1, 0.2 * inch))

    # Add the activity details section
    if activity_details:
        story.append(Paragraph(f'<b>Activity Details:</b> {activity_details}', details_style))
        story.append(Spacer(3, 0.2 * inch))

    # Process and save images
    image_paths = []
    for img in images:
        if img.filename != '':
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], img.filename)
            img.save(filepath)
            image_paths.append(filepath)

    if image_paths:
        num_images = len(image_paths)
        if num_images == 1:
            columns = 1
        elif num_images <= 4:
            columns = 2
        else:
            columns = 3

        page_width = letter[0] - 2 * content_margin_left
        image_spacing = 5
        img_width = (page_width - (columns - 1) * image_spacing) / columns
        img_height = img_width

        data = []
        row = []
        for i, path in enumerate(image_paths):
            row.append(Image(path, width=img_width, height=img_height))
            if len(row) == columns:
                data.append(row)
                row = []
        if row:
            data.append(row)

        image_table = Table(data, colWidths=[img_width] * columns)
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