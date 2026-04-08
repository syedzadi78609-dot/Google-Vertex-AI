import os
import hashlib
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for
from PIL import Image
from werkzeug.utils import secure_filename
from config import Config
from google import genai 

app = Flask(__name__)
app.secret_key = "atelier_secret"
app.config.from_object(Config)

# --- DEBUG: KEEPING YOUR TERMINAL LOGS ---
print("------------------------------")
print(f"DEBUG: API KEY LOADED: {app.config.get('GEMINI_API_KEY')}")
print("------------------------------")

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize Gemini Client
client = genai.Client(api_key=app.config['GEMINI_API_KEY'])

# --- MASTER DATABASE ---
users_db = {
    "Artist_User": {
        "username": "Artist_User",
        "art_points": 850, 
        "anim_points": 0, 
        "art_level": "Expert",
        "anim_level": "Rookie",
        "profile_pic": "default_avatar.png",
        "status": "Building the ArtVault... 🎀",
        "selected_sensei": "AI Sensei",
        "selected_icon_name": "Sparkles",
        "icons": {"Sparkles": "✨", "Palette": "🎨", "Star": "⭐"},
        
        "comrades": [],
        "pending_requests": [],
        "sent_requests": [],
        "status_access_list": [],
        "post_access_list": [],
        
        "animation_frames": [], 
        "processed_hashes": [], 
        "saved_critiques": [],  
        "active_statuses": [],
        "vault_posts": [],
        "messages": {}
    },
    
    "SketchMaster_99": {
        "username": "SketchMaster_99",
        "art_points": 1200, 
        "anim_points": 500,
        "art_level": "Elite",
        "anim_level": "Expert",
        "profile_pic": "default_avatar.png",
        "status": "Practicing anatomy! 🖌️",
        "selected_sensei": "Master Oogway",
        "selected_icon_name": "Palette",
        "icons": {"Sparkles": "✨", "Palette": "🎨", "Star": "⭐"},
        "comrades": ["Artist_User"], 
        "pending_requests": [],
        "sent_requests": [],
        "status_access_list": ["Artist_User"],
        "post_access_list": ["Artist_User"],
        "animation_frames": [],
        "processed_hashes": [],
        "saved_critiques": [],
        "active_statuses": [],
        "vault_posts": [],
        "messages": {}
    }
}

current_user_name = "Artist_User"

def get_level(pts):
    if pts >= 2000: return "Grandmaster"
    if pts >= 1500: return "Master"
    if pts >= 1000: return "Elite"
    if pts >= 500: return "Expert"
    return "Rookie"

def get_image_hash(image_path):
    with open(image_path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()

# --- 1. NAVIGATION & SEARCH ---

@app.route('/')
def index():
    return render_template('splash.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/login_logic', methods=['GET', 'POST'])
def login_logic():
    if request.method == 'POST':
        return redirect(url_for('profile_page'))
    return redirect(url_for('login'))

@app.route('/signup')
def signup_page():
    return render_template('signup.html')

@app.route('/forgot-password')
def forgot_password():
    return render_template('forgot_password.html')

@app.route('/profile/<username>')
@app.route('/profile')
def profile_page(username=None):
    me = users_db[current_user_name]
    
    if username is None or username == current_user_name:
        return render_template('profile.html', user=me, is_owner=True, viewer_is_comrade=True)
    
    target_user = users_db.get(username)
    if not target_user:
        return redirect(url_for('search_artists'))

    viewer_is_comrade = current_user_name in target_user.get("comrades", [])
    request_pending = username in me.get("sent_requests", [])
    
    return render_template('profile.html', 
                           user=target_user, 
                           is_owner=False, 
                           viewer_is_comrade=viewer_is_comrade,
                           request_pending=request_pending)

@app.route('/search')
def search_artists():
    query = request.args.get('q', '')
    results = [u for name, u in users_db.items() if query.lower() in name.lower()]
    return render_template('search.html', results=results, query=query)

# --- SOCIAL ROUTES ---

@app.route('/comrades/feed')
def comrade_feed():
    me = users_db[current_user_name]
    my_comrades = [users_db[name] for name in me["comrades"] if name in users_db]
    return render_template('comrade_feed.html', comrades=my_comrades)

@app.route('/status/<username>')
def view_status(username):
    me = users_db[current_user_name]
    target_user = users_db.get(username)
    if not target_user:
        return "User not found", 404
    
    if username in me["comrades"]:
        return render_template('view_status.html', target_user=target_user)
    return "You are not authorized to view this status.", 403

# --- 2. THE COMRADE ENGINE ---

@app.route('/send-request/<username>', methods=['POST'])
def send_comrade_request(username):
    me = users_db[current_user_name]
    target = users_db.get(username)
    if target and username not in me["comrades"] and username not in me["sent_requests"]:
        me["sent_requests"].append(username)
        target["pending_requests"].append(current_user_name)
    return redirect(url_for('profile_page', username=username))

@app.route('/accept-request/<username>', methods=['POST'])
def accept_comrade(username):
    me = users_db[current_user_name]
    target = users_db.get(username)
    if target and username in me["pending_requests"]:
        me["comrades"].append(username)
        target["comrades"].append(current_user_name)
        me["pending_requests"].remove(username)
        if current_user_name in target["sent_requests"]:
            target["sent_requests"].remove(current_user_name)
        me["status_access_list"].append(username)
        target["status_access_list"].append(current_user_name)
    return redirect(url_for('profile_page'))

@app.route('/decline-request/<username>', methods=['POST'])
def decline_comrade(username):
    me = users_db[current_user_name]
    target = users_db.get(username)
    if username in me["pending_requests"]:
        me["pending_requests"].remove(username)
    if target and current_user_name in target["sent_requests"]:
        target["sent_requests"].remove(current_user_name)
    return redirect(url_for('profile_page'))

# --- 3. THE ART STUDIOS ---

@app.route('/animation')
def animation():
    user = users_db[current_user_name]
    return render_template('animation.html', user=user, frames=user["animation_frames"])

@app.route('/upload-animation', methods=['POST'])
def upload_animation():
    user = users_db[current_user_name]
    files = request.files.getlist('anim_frames')
    for file in files:
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            if filename not in user["animation_frames"]:
                user["animation_frames"].append(filename)
    return redirect(url_for('animation'))

@app.route('/clear-animation')
def clear_animation():
    users_db[current_user_name]["animation_frames"] = []
    return redirect(url_for('animation'))

@app.route('/upload-art', methods=['POST'])
def upload_art():
    user = users_db[current_user_name]
    file = request.files.get('art_file')
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)
        user.setdefault("saved_critiques", []).append({
            "image": filename,
            "prompt": "Manual Upload",
            "feedback": "No critique yet.",
            "timestamp": datetime.now().strftime("%b %d, %Y")
        })
    return redirect(url_for('gallery'))

@app.route('/delete-art/<filename>', methods=['POST'])
def delete_art(filename):
    user = users_db[current_user_name]
    user["saved_critiques"] = [item for item in user.get("saved_critiques", []) if item['image'] != filename]
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    return redirect(url_for('gallery'))

@app.route('/gallery')
def gallery():
    user = users_db[current_user_name]
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    all_files = os.listdir(app.config['UPLOAD_FOLDER'])
    user_art_filenames = [item['image'] for item in user.get("saved_critiques", [])]
    artworks = []
    for filename in all_files:
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            if filename in user_art_filenames:
                artworks.append({"filename": filename, "title": filename.split('.')[0]})
    return render_template('gallery.html', user=user, artworks=artworks)

@app.route('/critique-room')
def critique_room():
    return render_template('critique_room.html', user=users_db[current_user_name])

@app.route('/wisdom-vault')
def wisdom_vault():
    user = users_db[current_user_name]
    vault_items = []
    for item in user["saved_critiques"]:
        vault_items.append({
            "image_url": url_for('static', filename='uploads/' + item['image']),
            "user_prompt": item.get('prompt', 'Analyze my art.'),
            "sensei_response": item['feedback'],
            "date_created": datetime.strptime(item['timestamp'], "%b %d, %Y")
        })
    return render_template('wisdom_vault.html', critiques=vault_items)

# --- 4. BACKEND UPDATES & AI ---

@app.route('/update-atelier', methods=['POST'])
def update_atelier():
    user = users_db[current_user_name]
    new_name = request.form.get('username')
    if new_name: user['username'] = new_name
    user['status'] = request.form.get('status', user['status'])
    user['selected_icon_name'] = request.form.get('active_icon', user['selected_icon_name'])
    file = request.files.get('profile_pic_file')
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        user['profile_pic'] = filename 
    return redirect(url_for('profile_page'))

@app.route('/get-critique', methods=['POST'])
def get_critique():
    user = users_db[current_user_name]
    user_query = request.form.get('query', 'Analyze my art.')
    file = request.files.get('art_file')
    if not file: return jsonify({"status": "error", "feedback": "No file!"}), 400

    filename = secure_filename(file.filename)
    path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(path)
    img_hash = get_image_hash(path)
    is_new = img_hash not in user["processed_hashes"]
    
    try:
        img = Image.open(path)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.thumbnail((1024, 1024)) 
        sys_prompt = "You are Sensei. Be wise and strict. If art is good, say 'Masterpiece Secured'. Keep it brief."
        response = client.models.generate_content(
            model="gemini-1.5-flash", 
            contents=[sys_prompt, user_query, img]
        )
        feedback = response.text
        leveled_up = False
        if is_new:
            user["processed_hashes"].append(img_hash)
            old_level = user["art_level"]
            user["art_points"] += 50
            user["art_level"] = get_level(user["art_points"])
            leveled_up = (old_level != user["art_level"])
            user.setdefault("saved_critiques", []).append({
                "image": filename,
                "prompt": user_query,
                "feedback": feedback,
                "timestamp": datetime.now().strftime("%b %d, %Y")
            })
        return jsonify({
            "status": "success", "feedback": feedback, "is_new": is_new,
            "points": user["art_points"], "level": user["art_level"], "leveled_up": leveled_up
        })
    except Exception as e:
        return jsonify({"status": "error", "feedback": "Sensei is meditating."})

if __name__ == '__main__':
    app.run(debug=True)