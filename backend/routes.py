from flask_cors import cross_origin
from flask import Blueprint, request, render_template, redirect, make_response, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

from .utils import process_webcam_capture, process_url_input, process_image_file, process_output_file, process_upload_file
from .models import User, db

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def homepage():
    resp = make_response(render_template("upload-file.html"))
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@main_bp.route('/url')
def detect_by_url_page():
    return render_template("input-url.html")

@main_bp.route('/webcam')
def detect_by_webcam_page():
    return render_template("webcam-capture.html")

@main_bp.route('/analyze', methods=['POST', 'GET'])
@cross_origin(supports_credentials=True)
def analyze():
    if request.method == 'POST':
        out_name, filepath, filename, filetype, csv_name1, csv_name2 = None, None, None, None, None, None

        if 'webcam-button' in request.form:
            filename, filepath, filetype = process_webcam_capture(request)

        elif 'url-button' in request.form:
            filename, filepath, filetype = process_url_input(request)

        elif 'upload-button' in request.form:
            filename, filepath, filetype = process_upload_file(request)

        # Get all inputs in form
        min_iou = float(request.form.get('threshold-range')) / 100
        min_conf = float(request.form.get('confidence-range')) / 100
        model_types = request.form.get('model-types').lower()
        enhanced = request.form.get('enhanced') == 'on'
        ensemble = request.form.get('ensemble') == 'on'
        tta = request.form.get('tta') == 'on'
        segmentation = request.form.get('seg') == 'on'

        if filetype == 'image':
            out_name, output_path, output_type = process_image_file(filename, filepath, model_types, tta, ensemble, min_conf, min_iou, enhanced, segmentation)
        else:
            return render_template('detect-input-url.html', error_msg="Invalid input url!!!")

        filename, csv_name1, csv_name2 = process_output_file(output_path)

        if 'url-button' in request.form:
            return render_template('detect-input-url.html', out_name=out_name, segname=output_path, fname=filename, output_type=output_type, filetype=filetype, csv_name=csv_name1, csv_name2=csv_name2)

        elif 'webcam-button' in request.form:
            return render_template('detect-webcam-capture.html', out_name=out_name, segname=output_path, fname=filename, output_type=output_type, filetype=filetype, csv_name=csv_name1, csv_name2=csv_name2)

        return render_template('detect-upload-file.html', out_name=out_name, segname=output_path, fname=filename, output_type=output_type, filetype=filetype, csv_name=csv_name1, csv_name2=csv_name2)

    return redirect('/')

# Регистрация
@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if not username or not email or not password:
            flash('Please fill out all fields')
            return redirect(url_for('main.register'))
            
        # Check if the user already exists
        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash('A user with that email already exists')
            return redirect(url_for('main.register'))
        
        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful')
        session['user_id'] = new_user.id  # Сохраняем user_id в сессию
        return redirect(url_for('main.analyze'))
    
    return render_template('register.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        if not email or not password:
            flash('Please fill out all fields')
            return redirect(url_for('main.login'))
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Login successful')
            return redirect(url_for('main.analyze'))
        else:
            flash('Invalid credentials')
            return redirect(url_for('main.login'))
    
    return render_template('login.html')


@main_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out')
    return redirect(url_for('main.analyze'))


@main_bp.after_request
def add_header(response):
    # Include cookie for every request
    response.headers.add('Access-Control-Allow-Credentials', True)

    # Prevent the client from caching the response
    if 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'public, no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
    return response