import os

class Config:
    # 1. Gemini API Key
    GEMINI_API_KEY = "AIzaSyDkz56WM_TVgcdHJ9xuEJnBs5QLkCtJvcw"
    
    # 2. Folder MUST be inside static for the web browser to display them!
    UPLOAD_FOLDER = os.path.join('static', 'uploads')
    
    # 3. Security: Only allow these files
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}

    # 4. Oracle DB (For later!)
    ORACLE_USER = "system"
    ORACLE_PASSWORD = "your_password"
    ORACLE_DSN = "localhost:1521/xe"