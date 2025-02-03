from flask import Flask, send_file, jsonify, render_template_string, request, session, url_for
import os
import random
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key_here')  # Use environment variable for secret key

# Configuration
VIDEO_FOLDER = os.getenv('VIDEO_FOLDER', 'uploads')  # Path to your video folder
CHAT_FILE = os.getenv('CHAT_FILE', 'chat_messages.json')  # File to store chat messages

# Ensure required directories and files exist
if not os.path.exists(VIDEO_FOLDER):
    os.makedirs(VIDEO_FOLDER)

if not os.path.exists(CHAT_FILE):
    with open(CHAT_FILE, 'w') as f:
        json.dump([], f)

# Load video metadata
videos = [video for video in os.listdir(VIDEO_FOLDER) if video.endswith(('.mp4', '.mkv'))]
video_metadata = {}
for video in videos:
    video_metadata[video] = {
        'title': video.split('.')[0],
        'duration': 0  # Duration will be handled by frontend
    }

# Load chat messages
def load_chat_messages():
    try:
        with open(CHAT_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_chat_messages(messages):
    with open(CHAT_FILE, 'w') as f:
        json.dump(messages, f, indent=2)

chat_messages = load_chat_messages()

@app.route('/')
def index():
    if 'current_video_index' not in session:
        session['current_video_index'] = 0
    
    username_set = 'username' in session
    return render_template_string('''
<!DOCTYPE html>
<html lang="en" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Miu Alpha Streamer</title>
    <link href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root {
            --primary: #6366f1;
            --primary-hover: #4f46e5;
            --background: #ffffff;
            --text: #1e293b;
            --card-bg: rgba(255, 255, 255, 0.9);
            --border: rgba(0, 0, 0, 0.1);
            --shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }

        [data-theme="dark"] {
            --background: #0f172a;
            --text: #f8fafc;
            --card-bg: rgba(15, 23, 42, 0.9);
            --border: rgba(255, 255, 255, 0.1);
            --shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }

        body {
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            background: var(--background);
            color: var(--text);
            transition: all 0.3s ease;
            min-height: 100vh;
            margin: 0;
            overflow-x: hidden;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
            transition: transform 0.3s ease;
        }

        .container.shifted {
            transform: translateX(-400px);
        }

        .theme-toggle {
            position: fixed;
            top: 1.5rem;
            right: 1.5rem;
            background: var(--card-bg);
            border: 1px solid var(--border);
            padding: 0.75rem;
            border-radius: 50%;
            backdrop-filter: blur(10px);
            cursor: pointer;
            z-index: 1000;
            box-shadow: var(--shadow);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.3s ease;
        }

        .theme-toggle.shifted {
            transform: translateX(-400px);
        }

        .header {
            text-align: center;
            margin-bottom: 2rem;
            position: relative;
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 0.5rem;
        }

        .video-container {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 1.5rem;
            padding: 2rem;
            margin: 2rem 0;
            backdrop-filter: blur(10px);
            box-shadow: var(--shadow);
        }

        #video-player {
            width: 100%;
            border-radius: 1rem;
            aspect-ratio: 16/9;
            background: #000;
            margin-bottom: 1.5rem;
        }

        .video-info {
            text-align: center;
            margin-bottom: 1.5rem;
        }

        .video-info h3 {
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
        }

        .controls {
            display: flex;
            gap: 1rem;
            justify-content: center;
            margin: 2rem 0;
            flex-wrap: wrap;
        }

        .btn {
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 0.75rem;
            font-weight: 600;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }

        .btn-primary {
            background: var(--primary);
            color: white;
        }

        .btn-primary:hover {
            background: var(--primary-hover);
            transform: translateY(-1px);
        }

        .btn-secondary {
            background: var(--card-bg);
            border: 1px solid var(--border);
            color: var(--text);
        }

        .btn-secondary:hover {
            background: var(--border);
            transform: translateY(-1px);
        }

        .video-list {
            display: grid;
            gap: 1rem;
            margin-top: 2rem;
        }

        .video-item {
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 1rem;
            padding: 1.5rem;
            transition: transform 0.2s ease;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .video-item:hover {
            transform: translateY(-2px);
        }

        .video-content {
            flex-grow: 1;
        }

        .video-item strong {
            font-size: 1.1rem;
            display: block;
            margin-bottom: 0.5rem;
        }

        .chat-sidebar {
            position: fixed;
            top: 0;
            right: -400px;
            width: 400px;
            height: 100vh;
            background: var(--card-bg);
            border-left: 1px solid var(--border);
            backdrop-filter: blur(10px);
            box-shadow: var(--shadow);
            transition: right 0.3s ease;
            z-index: 999;
        }

        .chat-sidebar.open {
            right: 0;
        }

        .chat-header {
            padding: 1rem;
            border-bottom: 1px solid var(--border);
            text-align: center;
        }

        .chat-messages {
            height: calc(100vh - 150px);
            overflow-y: auto;
            padding: 1rem;
        }

        .chat-message {
            margin-bottom: 1rem;
            padding: 0.75rem;
            border-radius: 0.75rem;
            background: var(--background);
            border: 1px solid var(--border);
        }

        .chat-message strong {
            color: var(--primary);
        }

        .chat-message small {
            color: var(--text);
            opacity: 0.7;
        }

        .chat-input {
            display: flex;
            gap: 1rem;
            padding: 1rem;
            border-top: 1px solid var(--border);
        }

        .chat-input input {
            flex-grow: 1;
            padding: 0.75rem;
            border: 1px solid var(--border);
            border-radius: 0.75rem;
            background: var(--background);
            color: var(--text);
        }

        .chat-input button {
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 0.75rem;
            background: var(--primary);
            color: white;
            cursor: pointer;
        }

        .chat-input button:hover {
            background: var(--primary-hover);
        }

        .chat-hover-box {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 50px;
            height: 50px;
            background: rgba(0, 0, 0, 0.7);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 1000;
            transition: background 0.3s ease, transform 0.3s ease;
        }

        .chat-hover-box.shifted {
            transform: translateX(-400px);
        }

        .chat-hover-box:hover {
            background: rgba(0, 0, 0, 0.9);
        }

        .chat-hover-box span {
            font-size: 24px;
            color: white;
        }

        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 2rem;
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 1.5rem;
            backdrop-filter: blur(10px);
            box-shadow: var(--shadow);
            margin-top: 10%;
        }

        .login-container h2 {
            text-align: center;
            margin-bottom: 1.5rem;
        }

        .login-container input {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid var(--border);
            border-radius: 0.75rem;
            background: var(--background);
            color: var(--text);
            margin-bottom: 1rem;
        }

        .login-container button {
            width: 100%;
            padding: 0.75rem;
            border: none;
            border-radius: 0.75rem;
            background: var(--primary);
            color: white;
            cursor: pointer;
        }

        .login-container button:hover {
            background: var(--primary-hover);
        }

        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
            
            .video-container {
                padding: 1.5rem;
                margin: 1rem 0;
            }
            
            .btn {
                width: 100%;
                justify-content: center;
            }
            
            .video-item {
                flex-direction: column;
                align-items: flex-start;
                gap: 1rem;
            }

            .chat-sidebar {
                width: 100%;
                right: -100%;
            }

            .chat-sidebar.open {
                right: 0;
            }
        }

        .username-prompt {
            padding: 2rem;
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .username-prompt input {
            padding: 0.75rem;
            border: 1px solid var(--border);
            border-radius: 0.75rem;
            background: var(--background);
            color: var(--text);
        }

        .username-prompt button {
            padding: 0.75rem;
            border: none;
            border-radius: 0.75rem;
            background: var(--primary);
            color: white;
            cursor: pointer;
        }

        .username-prompt button:hover {
            background: var(--primary-hover);
        }

        #username-feedback {
            margin-left: 0.5rem;
            color: green;
        }
    </style>
</head>
<body>
    <button class="theme-toggle" id="theme-toggle">
        <span id="theme-icon">🌙</span>
    </button>

    <div class="chat-hover-box" id="chat-hover-box">
        <span>💬</span>
    </div>

    <div class="chat-sidebar" id="chat-sidebar">
        <div class="chat-header">
            <h3>Chat</h3>
        </div>
        <div id="username-prompt-section" style="{{ 'display: none;' if username_set else '' }}">
            <div class="username-prompt">
                <input type="text" id="username-input" placeholder="Enter your username">
                <button onclick="setUsername()">Register</button>
                <span id="username-feedback"></span>
            </div>
        </div>
        <div class="chat-messages" id="chat-messages" style="{{ 'display: block;' if username_set else 'display: none;' }}">
            <!-- Messages loaded dynamically -->
        </div>
        <div class="chat-input" style="{{ 'display: flex;' if username_set else 'display: none;' }}">
            <input type="text" id="chat-input" placeholder="Type your message...">
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>

    <div class="container" id="main-container">
        <div class="header">
            <h1>Miu Alpha Streamer</h1>
            <p class="text-muted">Next-Generation Video Streaming</p>
        </div>

        <div class="video-container">
            <div class="video-info">
                <h3>Now Playing: <span id="video-title">{{ videos[session['current_video_index']] }}</span></h3>
                <p>Duration: <span id="video-duration" class="loading-duration"></span> seconds</p>
            </div>
            <video id="video-player" controls autoplay>
                <source src="{{ url_for('stream_video', video_name=videos[session['current_video_index']]) }}" type="video/mp4">
                <source src="{{ url_for('stream_video', video_name=videos[session['current_video_index']]) }}" type="video/x-matroska">
                Your browser does not support the video tag.
            </video>
            
            <div class="controls">
                <button class="btn btn-primary" onclick="skipVideo()">
                    <span>⏭️</span> Skip Video
                </button>
                <button class="btn btn-secondary" onclick="shuffleVideos()">
                    <span>🔀</span> Shuffle
                </button>
                <button class="btn btn-secondary" onclick="togglePlayPause()">
                    <span>⏯️</span> Play/Pause
                </button>
            </div>
        </div>

        <div class="video-list">
            <h2 class="section-title">Available Videos</h2>
            {% for video in videos %}
                <div class="video-item">
                    <div class="video-content">
                        <strong>{{ video }}</strong>
                        <p>Duration: <span id="duration-{{ video }}" class="loading-duration"></span></p>
                    </div>
                    <button class="btn btn-primary" onclick="playVideo('{{ video }}')">
                        <span>▶️</span> Play
                    </button>
                </div>
            {% endfor %}
        </div>
    </div>

    <script>
        // Theme Management
        function toggleTheme() {
            const html = document.documentElement;
            const themeIcon = document.getElementById('theme-icon');
            const isDark = html.getAttribute('data-theme') === 'dark';
            
            html.setAttribute('data-theme', isDark ? 'light' : 'dark');
            themeIcon.textContent = isDark ? '🌙' : '☀️';
            localStorage.setItem('theme', isDark ? 'light' : 'dark');
        }

        // Initialize theme
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        document.getElementById('theme-icon').textContent = savedTheme === 'dark' ? '☀️' : '🌙';

        // Video Controls
        let videoElement = document.getElementById('video-player');
        let videoTitleElement = document.getElementById('video-title');
        let videoDurationElement = document.getElementById('video-duration');
        let currentVideoIndex = {{ session['current_video_index'] if 'current_video_index' in session else 0 }};

        videoElement.onloadedmetadata = function() {
            const duration = Math.round(videoElement.duration);
            videoDurationElement.textContent = duration;
            document.querySelectorAll('.loading-duration').forEach(el => {
                if(el.textContent === 'Loading...') el.textContent = duration;
            });
        };

        videoElement.onended = function() {
            handleVideoTransition('/next-video');
        };

        function playVideo(videoName) {
            handleVideoTransition(`/set-video/${videoName}`);
        }

        function skipVideo() {
            handleVideoTransition('/next-video?skip=true');
        }

        function shuffleVideos() {
            fetch('/shuffle-videos')
                .then(response => response.json())
                .then(data => {
                    currentVideoIndex = 0;
                    updatePlayer(data);
                    location.reload();
                });
        }

        function togglePlayPause() {
            videoElement.paused ? videoElement.play() : videoElement.pause();
        }

        function handleVideoTransition(url) {
            fetch(url)
                .then(response => response.json())
                .then(data => updatePlayer(data));
        }

        function updatePlayer(data) {
            currentVideoIndex = data.index;
            videoTitleElement.textContent = data.video_title;
            videoDurationElement.textContent = data.video_duration;
            videoElement.src = data.next_video_url;
            videoElement.play();
        }

        // Chat Controls
        function setUsername() {
            const usernameInput = document.getElementById('username-input');
            const feedback = document.getElementById('username-feedback');
            const username = usernameInput.value.trim();
            
            if (!username) {
                feedback.textContent = 'Please enter a username';
                feedback.style.color = 'red';
                return;
            }

            fetch('/set-username', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: username })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    document.getElementById('username-prompt-section').style.display = 'none';
                    document.getElementById('chat-messages').style.display = 'block';
                    document.getElementById('chat-input').style.display = 'flex';
                    feedback.textContent = '✅ Registered';
                    feedback.style.color = 'green';
                    loadMessages();
                    startMessagePolling();
                } else {
                    feedback.textContent = data.message;
                    feedback.style.color = 'red';
                }
            });
        }

        function sendMessage() {
            const chatInput = document.getElementById('chat-input');
            const message = chatInput.value.trim();
            
            if (message) {
                fetch('/send-message', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: message })
                })
                .then(response => {
                    if (!response.ok) throw new Error('Message send failed');
                    chatInput.value = '';
                })
                .catch(error => console.error('Error:', error));
            }
        }

        function loadMessages() {
            fetch('/get-messages')
                .then(response => response.json())
                .then(messages => {
                    const chatMessages = document.getElementById('chat-messages');
                    chatMessages.innerHTML = messages.map(msg => `
                        <div class="chat-message">
                            <strong>${msg.username}</strong> <small>${msg.timestamp}</small><br>
                            ${msg.message}
                        </div>
                    `).join('');
                    chatMessages.scrollTop = chatMessages.scrollHeight;
                });
        }

        function startMessagePolling() {
            setInterval(loadMessages, 1000);
        }

        // Event Listeners
        document.getElementById('chat-input').addEventListener('keypress', function(event) {
            if (event.key === 'Enter') sendMessage();
        });

        document.getElementById('chat-hover-box').addEventListener('click', toggleChat);
        document.getElementById('theme-toggle').addEventListener('click', toggleTheme);

        // Initialize chat state
        if ({{ 'true' if username_set else 'false' }}) {
            loadMessages();
            startMessagePolling();
        }

        function toggleChat() {
            const chatSidebar = document.getElementById('chat-sidebar');
            const mainContainer = document.getElementById('main-container');
            const chatHoverBox = document.getElementById('chat-hover-box');
            const themeToggle = document.getElementById('theme-toggle');
            
            chatSidebar.classList.toggle('open');
            mainContainer.classList.toggle('shifted');
            chatHoverBox.classList.toggle('shifted');
            themeToggle.classList.toggle('shifted');
        }
    </script>
</body>
</html>
    ''', videos=videos, video_metadata=video_metadata, username_set='username' in session)

@app.route('/set-username', methods=['POST'])
def set_username():
    data = request.get_json()
    username = data.get('username', '').strip()
    
    if not username:
        return jsonify({'status': 'error', 'message': 'Username not provided'}), 400
    
    session['username'] = username
    return jsonify({'status': 'success', 'message': 'Username set successfully'})

@app.route('/send-message', methods=['POST'])
def send_message():
    if 'username' not in session:
        return jsonify({'error': 'Username not set'}), 401
    
    data = request.get_json()
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({'error': 'No message provided'}), 400
    
    chat_message = {
        'username': session['username'],
        'message': message,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    chat_messages.append(chat_message)
    save_chat_messages(chat_messages)
    return jsonify(chat_message)

@app.route('/get-messages')
def get_messages():
    return jsonify(chat_messages)

@app.route('/stream-video/<video_name>')
def stream_video(video_name):
    video_path = os.path.join(VIDEO_FOLDER, video_name)
    if not os.path.exists(video_path):
        return jsonify({'error': 'Video not found'}), 404
    return send_file(video_path, as_attachment=False)

@app.route('/next-video')
def next_video():
    skip = request.args.get('skip', 'false').lower() == 'true'
    
    if skip:
        session['current_video_index'] = (session['current_video_index'] + 1) % len(videos)
    else:
        session['current_video_index'] = (session['current_video_index'] + 1) % len(videos)

    next_video_name = videos[session['current_video_index']]
    next_video_url = url_for('stream_video', video_name=next_video_name)
    video_title = video_metadata[next_video_name]['title']
    video_duration = video_metadata[next_video_name]['duration']

    return jsonify({
        'next_video_url': next_video_url,
        'index': session['current_video_index'],
        'video_title': video_title,
        'video_duration': video_duration
    })

@app.route('/set-video/<video_name>')
def set_video(video_name):
    if video_name in videos:
        session['current_video_index'] = videos.index(video_name)
    next_video_name = videos[session['current_video_index']]
    next_video_url = url_for('stream_video', video_name=next_video_name)
    video_title = video_metadata[next_video_name]['title']
    video_duration = video_metadata[next_video_name]['duration']
    
    return jsonify({
        'next_video_url': next_video_url,
        'video_title': video_title,
        'video_duration': video_duration,
        'index': session['current_video_index']
    })

@app.route('/shuffle-videos')
def shuffle_videos():
    random.shuffle(videos)
    session['current_video_index'] = 0
    next_video_name = videos[session['current_video_index']]
    next_video_url = url_for('stream_video', video_name=next_video_name)
    video_title = video_metadata[next_video_name]['title']
    video_duration = video_metadata[next_video_name]['duration']

    return jsonify({
        'next_video_url': next_video_url,
        'video_title': video_title,
        'video_duration': video_duration
    })

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)