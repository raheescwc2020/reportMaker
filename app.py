import os
import json
import io
import datetime
import traceback 

from dotenv import load_dotenv
# NEW LINE:
load_dotenv()

# Database imports
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import inspect 

# Reportlab imports
from reportlab.platypus import SimpleDocTemplate, Image, Table, TableStyle, Spacer, Paragraph
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, g

# --- FLASK APPLICATION SETUP ---
app = Flask(__name__)
app.secret_key = 'super_secret_and_complex_key_for_session_management' 

# 1. DATABASE CONFIGURATION
# We explicitly construct the connection URI using the environment variables
# confirmed to be set by the Railway MySQL service, ensuring the pymysql driver is used.
MYSQL_USER = os.environ.get('MYSQLUSER', 'root')
MYSQL_PASS = os.environ.get('MYSQL_ROOT_PASSWORD') # Use the most secure password variable
MYSQL_HOST = os.environ.get('MYSQLHOST', 'localhost')
MYSQL_PORT = os.environ.get('MYSQLPORT', '3306')
MYSQL_DB = os.environ.get('MYSQL_DATABASE', 'railway')

# Construct the URI: mysql+pymysql://user:password@host:port/database
# We use the public URL variable if the private one isn't available, but default to private for performance.
DATABASE_URI = os.environ.get(
    'MYSQL_URL'
)

if not DATABASE_URI:
    # Construct the URI explicitly using individual variables if the URL isn't set
    if MYSQL_PASS:
        DATABASE_URI = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASS}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    else:
        # Fallback for local testing or if required variables are missing
        DATABASE_URI = 'sqlite:///links.db' 
        print("WARNING: Using SQLite fallback. Database URI could not be constructed from environment variables.")


# Apply the constructed URI to Flask-SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI

# Suppress deprecation warning
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 

db = SQLAlchemy(app)


# --- DATABASE MODEL (Schema) ---

class Link(db.Model):
    """
    Defines the structure for the 'spreadsheet_manager' table.
    """
    __tablename__ = 'spreasheet_manager' 
    
    id: Mapped[int] = mapped_column(db.Integer, primary_key=True)
    name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    category: Mapped[str] = mapped_column(db.String(50), nullable=False)
    url: Mapped[str] = mapped_column(db.String(255), unique=True, nullable=False)

    def __repr__(self):
        return f'<Link {self.name}>'


# --- DATABASE INITIALIZATION FUNCTION ---
def initialize_database():
    """
    Creates tables if they don't exist and seeds initial data.
    This runs once, on the first request, ensuring tables are ready for deployment environments.
    """
    try:
        # Use inspect for public API to check for table existence
        engine = db.engine
        inspector = inspect(engine)
        table_exists = 'spreadsheet_manager' in inspector.get_table_names()

        # Check if the table already exists by attempting to query
        if table_exists:
            print("Database table 'spreadsheet_manager' already exists. Skipping creation.")
        else:
            print("Database table 'spreadsheet_manager' not found. Creating table...")
            db.create_all()
            print("Tables created successfully.")

        # Seed initial data only if the table is empty
        if db.session.execute(db.select(Link)).scalar() is None: 
            print("Seeding initial data...")
            initial_links = [
                Link(name="Q4 Sales Metrics - Finance Seed", category="Finance", url="https://docs.google.com/spreadsheets/d/initial_seed_finance_q4"),
                Link(name="HR Onboarding Checklist - HR Seed", category="HR", url="https://docs.google.com/spreadsheets/d/initial_seed_hr_onboarding"),
                Link(name="RV Solutions Project Status", category="Project Management", url="https://docs.google.com/spreadsheets/d/rv_project_status_tracker"),
                Link(name="Marketing Budget Tracker 2025", category="Marketing", url="https://docs.google.com/spreadsheets/d/marketing_budget_2025"),
                Link(name="IT Infrastructure Inventory", category="IT", url="https://docs.google.com/spreadsheets/d/it_inventory_list"),
                Link(name="Client Satisfaction Survey Results", category="Customer Service", url="https://docs.google.com/spreadsheets/d/satisfaction_survey_data"),
                Link(name="Supply Chain Logistics Plan Q3", category="Operations", url="https://docs.google.com/spreadsheets/d/q3_logistics_plan"),
                Link(name="Monthly Expenses Report June 2025", category="Finance", url="https://docs.google.com/spreadsheets/d/june_expenses_2025"),
                Link(name="Team Performance Review Tracker", category="HR", url="https://docs.google.com/spreadsheets/d/performance_tracker_hr"),
                Link(name="Social Media Campaign Schedule", category="Marketing", url="https://docs.google.com/spreadsheets/d/social_media_schedule"),
                Link(name="New Product Development Roadmap", category="Project Management", url="https://docs.google.com/spreadsheets/d/product_roadmap_v2"),
                Link(name="Employee Training Records 2024", category="HR", url="https://docs.google.com/spreadsheets/d/training_records_2024"),
                Link(name="Vendor Contact List - Operations", category="Operations", url="https://docs.google.com/spreadsheets/d/vendor_contact_list_ops"),
            ]
            db.session.add_all(initial_links)
            db.session.commit()
            print("Initial links added successfully.")
            
            # --- MODIFICATION TO DEMONSTRATE DATA RETRIEVAL ---
            # Retrieve the first link added to show that data fetching works
            first_link = db.session.execute(db.select(Link).order_by(Link.id).limit(1)).scalar()
            if first_link:
                print(f"Verified data retrieval: The first link found is: {first_link.name}")
            else:
                print("Could not retrieve the first link after seeding.")
            # --- END MODIFICATION ---

            
    except Exception as e:
        print("\n--- DATABASE INITIALIZATION ERROR ---")
        print(f"Failed to connect to or initialize database using URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print(f"Error: {e}")
        print(traceback.format_exc())
        print("-----------------------------------\n")

# --- EXECUTE DB INITIALIZATION ON DEPLOYMENT STARTUP ---
# This decorator is crucial for Gunicorn (Railway) deployment
@app.before_request
def before_request_func():
    """
    A simpler alternative to @app.before_first_request for modern Flask/Gunicorn deployments.
    Uses a global flag (g.db_initialized) to ensure it runs only once per process startup.
    """
    if not getattr(g, 'db_initialized', False):
        with app.app_context():
            initialize_database()
        g.db_initialized = True


# --- SPREADSHEET MANAGER CONFIG/DATA ---
ADMIN_USER = "admin"
ADMIN_PASS = "securepassword123"
LINKS_PER_PAGE = 10 # New constant for pagination

# Spreadsheet Helper Functions
def is_admin():
    """Checks if the user is authenticated as an admin."""
    return session.get('logged_in', False)

def get_links():
    """
    Fetches all stored links from the database (spreadsheet_manager table).
    This function correctly uses the Link model to query the underlying table.
    """
    try:
        # This is the primary function used by the application to retrieve ALL data.
        return db.session.execute(db.select(Link).order_by(Link.id)).scalars().all()
    except Exception as e:
        print(f"Database fetch error: {e}")
        # Flash message for the user interface
        flash("Could not connect to or query the database. Check console logs for details.", 'error')
        return []

# --- SWACHHATHA REPORT CONFIG/DATA ---
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

REGIONAL_WAREHOUSES = {
    'Ahmedabad': ['CW Shahalam', 'CW Anand', 'CW Baroda-I', 'CW Pipavav', 'CW Rajkot', 'CW Surat', 'CW Dantewada', 'CW Jagdalpur', 'CW Raigarh', 'CW Raipur', 'CW Kandla Port', 'CFS Mundra', 'CRWC Kandla', 'CW Rajkot (Hired)', 'CW Jamnagar'],
    'Bangalore': ['CW Belgachhia', 'CW Chikkaballapur', 'CW Tumkur', 'CW Belgaum', 'CW Mysore', 'CW Gadag', 'CW Dharwad', 'CW Mandya', 'CW Hubballi', 'CW Mangalore', 'CW Panambur'],
    'Bhopal': ['CW Bhopal', 'CW Jabalpur', 'CW Rewa', 'CW Chhindwara', 'CW Sagar', 'CW Neemuch', 'CW Damoh', 'CW Katni', 'CW Gwalior', 'CW Satna', 'CW Khandwa'],
    'Bhubaneshwar': ['CW Junagarh', 'CW Kendupalli-I', 'CW Kendupalli-II', 'CW Koksara', 'CW Kalamati', 'CW Nabrangpur', 'CW Bhubaneswar-I', 'CW Bhubaneswar-II', 'CW Balasore', 'CW Cuttack', 'CW Rourkela', 'CW Sambalpur', 'CW Jeypore', 'CW Paradeep', 'CW Angul', 'CW Bhawanipatna', 'CW Talcher'],
    'Chandigarh': ['CW Chandigarh', 'CW Faridkot', 'CW Amritsar', 'CW Firozpur', 'CW Ludhiana', 'CW Patiala', 'CW Mohali', 'CW Jalandhar', 'CW Gurdaspur', 'CW Sangrur', 'CW Bathinda', 'CW Samana', 'CW Kotkapura', 'CW Muktsar', 'CW Pathankot', 'CW Rupnagar', 'CW Sirhind', 'CW Hoshiarpur', 'CW Abohar', 'CW Malout', 'CW Phagwara', 'CW Moga', 'CW Nawanshahar', 'CW Tarntaran'],
    'Guwahati': ['CW Agartala', 'CW Dimapur', 'CW Imphal', 'CW Silchar', 'CW Shillong', 'CW Mirza', 'CW Guwahati', 'CW Dhaligaon', 'CW Goalpara', 'CW Jorhat', 'CW Dibrugarh', 'CW Aizawl', 'CW Gangtok', 'CW Guwahati', 'CW Silchar'],
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


# --- ROUTING FOR SPREADSHEET MANAGER ---

@app.route('/')
@app.route('/spreadsheets')
def public_directory():
    """The Public View: Shows all links in a searchable table, fetching data from the database with pagination."""
    
    # 1. Get current page number from URL query, default to 1
    page = request.args.get('page', 1, type=int)
    
    try:
        # 2. Use paginate to fetch a subset of links
        pagination = db.paginate(
            db.select(Link).order_by(Link.id),
            page=page,
            per_page=LINKS_PER_PAGE,
            error_out=False # Set to False so it doesn't 404 if page is out of range
        )
        
        # 3. Pass the pagination object and the actual items (links) to the template
        return render_template(
            'combined_dashboard.html', 
            page_title="Spreadsheet Directory",
            links=pagination.items,
            pagination=pagination, # Pass the full pagination object
            is_admin=is_admin(),
            view_name='spreadsheets_public'
        )
    except Exception as e:
        print(f"Database pagination error: {e}")
        flash("Could not fetch paginated data from the database.", 'error')
        return render_template(
            'combined_dashboard.html', 
            page_title="Spreadsheet Directory",
            links=[], 
            pagination=None,
            is_admin=is_admin(),
            view_name='spreadsheets_public'
        )

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin Login Console."""
    if is_admin():
        return redirect(url_for('admin_add_link'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == ADMIN_USER and password == ADMIN_PASS:
            session['logged_in'] = True
            flash('Logged in successfully!', 'success')
            return redirect(url_for('admin_add_link'))
        else:
            flash('Invalid credentials. Please try again.', 'error')

    return render_template(
        'combined_dashboard.html', 
        page_title="Admin Login",
        is_admin=is_admin(),
        view_name='admin_login'
    )

@app.route('/admin/add', methods=['GET', 'POST'])
def admin_add_link():
    """
    Admin Console: Add New Link Form. 
    Handles both displaying the form (GET) and saving new links to the 'spreadsheet_manager' table (POST).
    """
    if not is_admin():
        # This prevents unauthorized users from even seeing or submitting the form
        flash('You must log in to access the admin console.', 'warning')
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        link_name = request.form.get('linkName', '').strip()
        link_category = request.form.get('linkCategory', '').strip()
        link_url = request.form.get('linkUrl', '').strip()

        if link_name and link_category and link_url:
            new_link = Link(
                name=link_name,
                category=link_category,
                url=link_url
            )
            try:
                db.session.add(new_link)
                db.session.commit()
                flash(f'Link "{link_name}" added successfully to the database!', 'success')
                # Redirect back to the form after successful submission
                return redirect(url_for('admin_add_link')) 
            except Exception as e:
                db.session.rollback()
                # Check for common unique constraint violations (e.g., duplicate URL)
                if 'Duplicate entry' in str(e) or 'IntegrityError' in str(e):
                    flash('Error: A link with that URL already exists in the database.', 'error')
                else:
                    flash(f'Error adding link: {e}', 'error')
        else:
            flash('All fields are required.', 'error')

    # For GET request or POST request with validation errors:
    return render_template(
        'combined_dashboard.html', 
        page_title="Admin Console: Add Link",
        is_admin=is_admin(),
        view_name='admin_add_view',
        links=get_links() # Fetch existing links for a list view on the admin page
    )


# --- ROUTING FOR SPREADSHEET MANAGER (Cont.) ---

# ... existing admin_add_link route ...

@app.route('/admin/bulk_upload', methods=['POST'])
def admin_bulk_upload():
    """
    Handles CSV file upload, parses it, and bulk-adds links to the database.
    Expected CSV format (including header): Name, Category, URL
    """
    if not is_admin():
        flash('You must log in to access the admin console.', 'warning')
        return redirect(url_for('admin_login'))

    # 1. Check if a file was actually uploaded
    if 'csv_file' not in request.files:
        flash('No file part in the request.', 'error')
        return redirect(url_for('admin_add_link'))

    file = request.files['csv_file']

    if file.filename == '':
        flash('No selected file.', 'error')
        return redirect(url_for('admin_add_link'))

    # 2. Validate file extension
    if not file.filename.endswith('.csv'):
        flash('Invalid file format. Please upload a CSV file.', 'error')
        return redirect(url_for('admin_add_link'))

    links_to_add = []
    links_added = 0
    links_skipped = 0
    
    try:
        # Read the file data into a string buffer and decode it as UTF-8
        stream = io.StringIO(file.stream.read().decode("UTF8"))
        
        # Use csv.reader to parse the data
        reader = csv.reader(stream)
        
        # 3. Skip header row (assuming Name, Category, URL are the headers)
        try:
            next(reader) 
        except StopIteration:
            flash('The CSV file is empty.', 'error')
            return redirect(url_for('admin_add_link'))
        
        # 4. Iterate over rows, validate, and prepare for bulk insert
        for i, row in enumerate(reader):
            # Clean and validate row data
            if len(row) >= 3:
                name = row[0].strip()
                category = row[1].strip()
                url = row[2].strip()
                
                if name and category and url:
                    links_to_add.append(Link(name=name, category=category, url=url))
                else:
                    links_skipped += 1
                    print(f"Skipping row {i+2}: Missing Name, Category, or URL.")
            else:
                links_skipped += 1
                print(f"Skipping row {i+2}: Malformed row (expected 3 columns, got {len(row)}).")

        # 5. Perform bulk database insert
        if links_to_add:
            db.session.add_all(links_to_add)
            db.session.commit()
            links_added = len(links_to_add)

            # 6. Success message
            if links_skipped > 0:
                flash(f'Successfully added {links_added} links. {links_skipped} rows were skipped due to missing data or incorrect format.', 'warning')
            else:
                flash(f'Successfully added {links_added} spreadsheet links from CSV.', 'success')
        elif links_skipped > 0:
            flash(f'No valid links were found in the CSV. {links_skipped} rows were skipped.', 'error')
        else:
            flash('The CSV file was processed, but no valid links were found after the header.', 'warning')

    except Exception as e:
        db.session.rollback()
        # Catch common duplicate URL errors
        if 'Duplicate entry' in str(e) or 'IntegrityError' in str(e):
             flash('Error: Upload failed due to a **duplicate URL** being present in the CSV or already in the database.', 'error')
        else:
            flash(f'An unexpected error occurred during CSV processing: {e}', 'error')
            print(f"CSV Bulk Upload Error: {traceback.format_exc()}")
            
    return redirect(url_for('admin_add_link'))


@app.route('/admin/logout')
def admin_logout():
    """Logout and clear the session."""
    session.pop('logged_in', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('public_directory'))


# --- ROUTING FOR SWACHHATHA REPORT GENERATOR ---

@app.route('/swachatha')
def swachatha_form():
    """The Swachhatha View: Shows the PDF generation form."""
    regions = sorted(REGIONAL_WAREHOUSES.keys())
    return render_template(
        'combined_dashboard.html', 
        page_title="Swachhatha Report Generator",
        activities=ACTIVITIES, 
        regional_warehouses=REGIONAL_WAREHOUSES, 
        regions=regions,
        view_name='swachatha_form',
        is_admin=is_admin()
    )

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    """Generates the PDF report based on form submission."""
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
    images = request.files.getlist('images')

    activity_name = activity_name_map.get(activity, 'N/A')

    try:
        date_object = datetime.datetime.strptime(date_str_yyyy_mm_dd, '%Y-%m-%d')
        date_str_dd_mm_yyyy = date_object.strftime('%d-%m-%Y')
    except (ValueError, TypeError):
        date_str_dd_mm_yyyy = 'N/A'

    # Setup PDF document
    buffer = io.BytesIO()
    margin = 0
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=margin,
        leftMargin=margin,
        rightMargin=margin,
        bottomMargin=margin
    )

    story = []
    styles = getSampleStyleSheet()

    # Add header image
    if os.path.exists(PDF_TEMPLATE_IMAGE):
        header_image_width = letter[0]
        header_image_height = 1.0 * inch
        header_image = Image(PDF_TEMPLATE_IMAGE, width=header_image_width, height=header_image_height)
        story.append(header_image)
        story.append(Spacer(1, 0.2 * inch))

    # Define styles
    content_margin_left = 0.5 * inch
    header_style = ParagraphStyle(
        'UnderlinedHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=16,
        alignment=TA_CENTER,
        underline=True
    )
    activity_name_style = ParagraphStyle(
        'BoldActivityName',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=14,
        alignment=TA_CENTER
    )
    subheader_style = ParagraphStyle(
        'Subheader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        alignment=TA_CENTER,
    )

    # Add text content
    story.append(Paragraph(f'{activity}', header_style))
    story.append(Paragraph(f'{activity_name}', activity_name_style))
    story.append(Paragraph(f'<b>Location:</b> {warehouse} under {region} Region | <b>Date:</b> {date_str_dd_mm_yyyy}', subheader_style))
    story.append(Spacer(1, 0.2 * inch))

    # Process and add images
    image_paths = []
    for img in images:
        if img.filename != '':
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], img.filename)
            img.save(filepath)
            image_paths.append(filepath)

    if image_paths:
        num_images = len(image_paths)
        columns = 3 if num_images > 4 else (2 if num_images > 1 else 1)

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

        # Create table for images
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
        try:
            os.remove(path)
        except OSError:
            pass

    # Prepare response
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name='report.pdf', mimetype='application/pdf')


if __name__ == '__main__':
    # Ensure all necessary folders exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    if not os.path.exists('static'):
        os.makedirs('static')
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    
    # --- DB INIT AND SEEDING (Local Only) ---
    with app.app_context():
        initialize_database()
    # --- DB INIT AND SEEDING END ---
        
    app.run(debug=True)
