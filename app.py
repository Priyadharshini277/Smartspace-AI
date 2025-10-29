from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from Database import User, Project, session
import os
from datetime import datetime
import replicate
from PIL import Image
import requests
from io import BytesIO

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['GENERATED_FOLDER'] = 'static/generated'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max

# Create folders
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['GENERATED_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# IMPORTANT: Set your Replicate API token here
# Get FREE token from: https://replicate.com/account/api-tokens
os.environ['REPLICATE_API_TOKEN'] = 'YOUR_REPLICATE_API_TOKEN_HERE'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class UserModel(UserMixin):
    def __init__(self, user):
        self.id = user.id
        self.username = user.username
        self.email = user.email

@login_manager.user_loader
def load_user(user_id):
    user = session.query(User).get(int(user_id))
    if user:
        return UserModel(user)
    return None

def generate_interior_design(input_image_path, style):
    """Generate interior design using FREE Replicate AI"""
    try:
        print(f"🎨 Generating design with style: {style}")
        
        style_prompts = {
            'modern': 'modern luxury interior design, sleek furniture, minimalist decor, contemporary style, professional photography, 8k',
            'minimalist': 'minimalist interior design, clean lines, white walls, simple furniture, Scandinavian style, natural light, 8k',
            'midcentury': 'mid-century modern interior, retro furniture, warm wood tones, vintage 1960s style, professional photography, 8k',
            'japandi': 'japandi interior design, Japanese minimalism, Scandinavian warmth, natural materials, zen aesthetic, 8k'
        }
        
        prompt = style_prompts.get(style.lower(), f'{style} interior design, professional, high quality, 8k')
        
        with open(input_image_path, 'rb') as image_file:
            output = replicate.run(
                "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
                input={
                    "image": image_file,
                    "prompt": prompt,
                    "negative_prompt": "ugly, blurry, low quality, distorted, unrealistic, bad architecture",
                    "num_inference_steps": 30,
                    "guidance_scale": 7.5,
                    "strength": 0.6,
                }
            )
        
        if output and len(output) > 0:
            image_url = output[0] if isinstance(output, list) else output
            response = requests.get(image_url)
            img = Image.open(BytesIO(response.content))
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f'generated_{style}_{timestamp}.jpg'
            output_path = os.path.join(app.config['GENERATED_FOLDER'], output_filename)
            img.save(output_path, 'JPEG', quality=95)
            
            print(f"✅ Successfully generated: {output_filename}")
            return output_filename
        else:
            print("❌ No output from Replicate API")
            return None
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

# HOME PAGE ROUTE (Your fancy dark landing page)
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Check if user exists
        existing_user = session.query(User).filter_by(email=email).first()
        if existing_user:
            flash('Email already registered!', 'error')
            return redirect(url_for('register'))
        
        # Create new user
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        
        try:
            session.add(new_user)
            session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            session.rollback()
            flash(f'Registration error: {str(e)}', 'error')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        print(f"🔍 Login attempt - Email: {email}")
        
        # Try to find user
        user = session.query(User).filter_by(email=email).first()
        
        if not user:
            print(f"❌ No user found with email: {email}")
            flash('No account found with this email. Please register first.', 'error')
            return redirect(url_for('login'))
        
        print(f"✅ User found: {user.username}")
        print(f"🔐 Stored password hash: {user.password[:20]}...")
        
        # Check password
        password_valid = check_password_hash(user.password, password)
        print(f"🔑 Password check result: {password_valid}")
        
        if password_valid:
            login_user(UserModel(user))
            print(f"✅ Login successful for {user.username}")
            return redirect(url_for('dashboard'))
        else:
            print(f"❌ Invalid password for {email}")
            flash('Invalid password!', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    projects = session.query(Project).filter_by(user_id=current_user.id).order_by(Project.created_at.desc()).all()
    
    styles_dir = 'static/styles'
    STYLES_TO_SHOW = {'midcentury', 'minimalist', 'modern', 'japandi'}
    
    styles = []
    if os.path.exists(styles_dir):
        styles = [name for name in os.listdir(styles_dir)
                 if os.path.isdir(os.path.join(styles_dir, name))
                 and name.lower() in STYLES_TO_SHOW]
    
    return render_template('dashboard.html', styles=styles, projects=projects)

@app.route('/upload', methods=['POST'])
@login_required
def upload_image():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image uploaded'}), 400
        
        file = request.files['image']
        style = request.form.get('style', 'modern')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f'{timestamp}_{filename}'
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)
            
            print(f"📁 File saved: {filepath}")
            
            generated_filename = generate_interior_design(filepath, style)
            
            if generated_filename:
                return jsonify({
                    'success': True,
                    'original_image': f'/static/uploads/{unique_filename}',
                    'generated_image': f'/static/generated/{generated_filename}',
                    'style': style
                })
            else:
                return jsonify({'error': 'Failed to generate design. Check your API token.'}), 500
        
        return jsonify({'error': 'Invalid file type. Use JPG, JPEG, or PNG'}), 400
        
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/save_project', methods=['POST'])
@login_required
def save_project():
    try:
        data = request.json
        new_project = Project(
            user_id=current_user.id,
            project_name=data.get('project_name'),
            original_image=data.get('original_image'),
            generated_image=data.get('generated_image'),
            style=data.get('style'),
            customizations=data.get('customizations', '{}')
        )
        
        session.add(new_project)
        session.commit()
        return jsonify({'success': True, 'project_id': new_project.id})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<int:project_id>')
@login_required
def download_project(project_id):
    project = session.query(Project).filter_by(id=project_id, user_id=current_user.id).first()
    if project:
        file_path = project.generated_image.lstrip('/')
        return send_file(file_path, as_attachment=True)
    return "Project not found", 404

@app.route('/features')
@login_required
def features():
    return render_template('features.html')

@app.route('/gallery')
@login_required
def gallery():
    styles_to_show = ['midcentury', 'minimalist', 'modern', 'japandi']
    galleries = []
    styles_dir = os.path.join('static', 'styles')
    for style in styles_to_show:
        style_path = os.path.join(styles_dir, style)
        if os.path.isdir(style_path):
            images = [
                f'styles/{style}/{img}'
                for img in os.listdir(style_path)
                if img.lower().endswith(('.jpg', '.jpeg', '.png'))
            ]
            if images:
                galleries.append({"style": style.capitalize(), "images": images})
    return render_template('gallery.html', galleries=galleries)

@app.route('/gallery/<style>')
@login_required
def gallery_style(style):
    styles_dir = 'static/styles'
    style_path = os.path.join(styles_dir, style)
    
    images = []
    if os.path.exists(style_path):
        images = [f for f in os.listdir(style_path) 
                 if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
    
    return render_template('gallery_style.html', style=style, images=images)

@app.route('/about')
@login_required
def about():
    return render_template('about.html')

@app.route('/contact')
@login_required
def contact():
    return render_template('contact.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
