from flask import Flask, send_from_directory, render_template_string, session, jsonify, request, url_for
import os
import random
import threading
import subprocess
from datetime import timedelta
import asyncio
import aiofiles
from aiohttp import ClientSession
from functools import wraps

app = Flask(__name__)
app.secret_key = 'Letgoooooooooooooooooooooo'
app.permanent_session_lifetime = timedelta(minutes=10)

# Define paths
HLS_FOLDER = r"D:\Programs\video\hls"
VIDEO_FOLDER = r"D:\Programs\video\uploads"
MAX_CHANNELS = 13
video_metadata = {}

# Create necessary directories
os.makedirs(HLS_FOLDER, exist_ok=True)
os.makedirs(VIDEO_FOLDER, exist_ok=True)

# Thread-safe set to track active channels
active_channels = set()
active_channels_lock = threading.Lock()

def async_wrapper(f):
    @wraps(f)
    async def wrapper(*args, **kwargs):
        return await f(*args, **kwargs)
    return wrapper

async def convert_to_hls(input_path, output_dir):
    """Convert video to HLS format using ffmpeg asynchronously"""
    playlist_path = os.path.join(output_dir, 'playlist.m3u8')
    cmd = [
    'ffmpeg',
    '-i', input_path,
    '-c:v', 'libx264',
    '-preset', 'ultrafast',
    '-crf', '28',
    '-g', '30',  # Set keyframe interval to 1 second (assuming 30 fps)
    '-r', '30',  # Set constant frame rate to 30 fps
    '-c:a', 'aac',
    '-b:a', '128k',
    '-sn',
    '-threads', '2',
    '-vf', 'scale=1280:-1',
    '-hls_time', '2',  # Set segment duration to 1 second
    '-hls_playlist_type', 'vod',
    '-hls_segment_filename', os.path.join(output_dir, 'segment%03d.ts'),
    '-f', 'hls',
    playlist_path
]
    process = await asyncio.create_subprocess_exec(*cmd)
    await process.wait()
    if process.returncode != 0:
        print(f"Error converting {input_path}")

async def process_existing_videos():
    """Process existing videos asynchronously"""
    tasks = []
    for filename in sorted(os.listdir(VIDEO_FOLDER)):
        if filename.lower().endswith(('.mp4', '.mkv')):
            base_name = os.path.splitext(filename)[0]
            hls_dir = os.path.join(HLS_FOLDER, base_name)
            
            if not os.path.exists(os.path.join(hls_dir, 'playlist.m3u8')):
                os.makedirs(hls_dir, exist_ok=True)
                tasks.append(convert_to_hls(os.path.join(VIDEO_FOLDER, filename), hls_dir))
            
            if base_name not in video_metadata:
                video_metadata[base_name] = {'title': base_name, 'duration': 0}
    
    await asyncio.gather(*tasks)

def get_movies():
    """Get a list of movies in the HLS folder"""
    return [movie_folder for movie_folder in os.listdir(HLS_FOLDER) 
            if os.path.isdir(os.path.join(HLS_FOLDER, movie_folder))]

@app.route('/')
async def index():
    session_id = session.get('session_id', str(random.randint(100000, 999999)))
    session['session_id'] = session_id
    session.permanent = True

    with active_channels_lock:
        if len(active_channels) >= MAX_CHANNELS and session_id not in active_channels:
            return render_template_string("<h1>All channels are in use. Please try again later.</h1>"), 503
        active_channels.add(session_id)

    if 'video_list' not in session:
        session['video_list'] = random.sample(get_movies(), len(get_movies()))
    if 'current_video_index' not in session:
        session['current_video_index'] = 0

    current_video_name = session['video_list'][session['current_video_index']]
    playlist_url = url_for('serve_hls', movie=current_video_name, filename='playlist.m3u8')

    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Movie Streamer</title>
    <link rel="icon" href="{{ url_for('static', filename='80654.png') }}" type="image/x-icon">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
    <style>
        body {
            font-family: 'Poppins', sans-serif;
            background-color: #1a1a1a;
            color: #ffffff;
            padding: 20px;
        }
        .navbar {
            background-color: #333;
            padding: 10px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .navbar h1 {
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }
        .nav-icons {
            display: flex;
            gap: 15px;
        }
        .nav-icons a {
            color: #007bff;
            text-decoration: none;
            font-size: 24px;
            transition: color 0.3s ease;
        }
        .nav-icons a:hover {
            color: #0056b3;
        }
        .video-container {
            max-width: 800px;
            margin: 0 auto;
            text-align: center;
            background-color: #222;
            padding: 20px; 
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }
        .video-player {
            width: 100%;
            height: auto;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .controls {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-top: 20px;
        }
        .controls .btn {
            font-size: 14px;
            padding: 10px 20px;
            border-radius: 25px;
            transition: all 0.3s ease;
        }
        .controls .btn-primary {
            background-color: #007bff;
            border: none;
        }
        .controls .btn-primary:hover {
            background-color: #0056b3;
        }
        .controls .btn-secondary {
            background-color: #6c757d;
            border: none;
        }
        .controls .btn-secondary:hover {
            background-color: #5a6268;
        }
        .controls .btn-warning {
            background-color: #ffc107;
            border: none;
        }
        .controls .btn-warning:hover {
            background-color: #e0a800;
        }
        .movie-list {
            margin-top: 30px;
        }
        .movie-item {
            background-color: #333;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .movie-item:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }
        .movie-item strong {
            font-size: 18px;
            font-weight: 600;
        }
        .movie-item p {
            margin: 5px 0 0;
            font-size: 14px;
            color: #aaa;
        }
        .video-duration {
            color: #ffc107;
        }
    </style>
</head>
<body>
    <div class="navbar">
        <h1>Movie Streamer</h1>
        <div class="nav-icons">
            <a href="{{ url_for('downloads') }}" title="Downloads"><i class="fas fa-download"></i></a>
        </div>
    </div>
    <div class="container">
        <div class="video-container">
            <h3>Now Playing: <span id="video-title">{{ current_video_name }}</span></h3>
            <p>Duration: <span id="video-duration">0</span> seconds</p>
            <video id="video-player" class="video-player" controls autoplay>
                <source id="video-source" src="{{ playlist_url }}" type="application/x-mpegURL">
                Your browser does not support the video tag.
            </video>
            <div class="controls">
                <button class="btn btn-primary" onclick="skipVideo()">Skip Video</button>
                <button class="btn btn-secondary" onclick="shuffleVideos()">Shuffle Videos</button>
                <button class="btn btn-warning" onclick="togglePlayPause()">Play/Pause</button>
            </div>
        </div>
        <div class="movie-list">
            <h3 class="text-center my-3">Available Movies</h3>
            {% for movie in movies %}
                <div class="movie-item" onclick="playMovie('{{ movie }}')">
                    <strong>{{ movie }}</strong>
                    <p>Duration: <span id="duration-{{ movie }}" class="video-duration">Loading...</span></p>
                </div>
            {% endfor %}
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <script>
        const videoPlayer = document.getElementById('video-player');
        const videoSource = document.getElementById('video-source');
        const videoTitleElement = document.getElementById('video-title');
        const videoDurationElement = document.getElementById('video-duration');
        let hls = null;

        function initializeHls() {
            if (Hls.isSupported()) {
                if (hls) hls.destroy();
                hls = new Hls();
                hls.loadSource(videoSource.src);
                hls.attachMedia(videoPlayer);
                hls.on(Hls.Events.MANIFEST_PARSED, () => videoPlayer.play());
            } else if (videoPlayer.canPlayType('application/vnd.apple.mpegurl')) {
                videoPlayer.src = videoSource.src;
                videoPlayer.addEventListener('loadedmetadata', () => videoPlayer.play());
            }
        }

        function playMovie(movie) {
            fetch(`/set-video/${movie}`)
                .then(response => response.json())
                .then(data => {
                    videoSource.src = data.next_video_url;
                    videoPlayer.load();
                    initializeHls();
                    videoTitleElement.innerText = data.video_title;
                });
        }

        function skipVideo() {
            fetch('/next-video')
                .then(response => response.json())
                .then(data => {
                    videoSource.src = data.next_video_url;
                    videoPlayer.load();
                    initializeHls();
                    videoTitleElement.innerText = data.video_title;
                });
        }

        function shuffleVideos() {
            fetch('/shuffle-videos')
                .then(response => response.json())
                .then(data => {
                    videoSource.src = data.next_video_url;
                    videoPlayer.load();
                    initializeHls();
                    videoTitleElement.innerText = data.video_title;
                });
        }

        function togglePlayPause() {
            if (videoPlayer.paused) {
                videoPlayer.play();
            } else {
                videoPlayer.pause();
            }
        }

        window.onload = () => {
            const firstMovie = document.querySelector('.movie-item');
            if (firstMovie) {
                playMovie(firstMovie.textContent.trim());
            }
        };

        videoPlayer.onloadedmetadata = function() {
            videoDurationElement.innerText = Math.round(videoPlayer.duration);
            document.querySelector(`#duration-${videoTitleElement.innerText}`).innerText = Math.round(videoPlayer.duration);
        };
    </script>
</body>
</html>




''',
        movies=get_movies(), current_video_name=current_video_name, playlist_url=playlist_url)

@app.route('/downloads')
async def downloads():
    files = await asyncio.to_thread(os.listdir, VIDEO_FOLDER)  # Run blocking I/O in thread
    return render_template_string('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Movie Streamer</title>
    <link rel="icon" href="{{ url_for('static', filename='80654.png') }}" type="image/x-icon">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css" rel="stylesheet">
    <style>
        body {
            font-family: 'Poppins', sans-serif;
            background-color: #1a1a1a;
            color: #ffffff;
            padding: 20px;
        }
        .navbar {
            background-color: #333;
            padding: 10px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .navbar h1 {
            margin: 0;
            font-size: 24px;
            font-weight: 600;
        }
        .nav-icons {
            display: flex;
            gap: 15px;
        }
        .nav-icons a {
            color: #007bff;
            text-decoration: none;
            font-size: 24px;
            transition: color 0.3s ease;
        }
        .nav-icons a:hover {
            color: #0056b3;
        }
        .video-container {
            max-width: 800px;
            margin: 0 auto;
            text-align: center;
            background-color: #222;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }
        .video-player {
            width: 100%;
            height: auto;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .controls {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-top: 20px;
        }
        .controls .btn {
            font-size: 14px;
            padding: 10px 20px;
            border-radius: 25px;
            transition: all 0.3s ease;
        }
        .controls .btn-primary {
            background-color: #007bff;
            border: none;
        }
        .controls .btn-primary:hover {
            background-color: #0056b3;
        }
        .controls .btn-secondary {
            background-color: #6c757d;
            border: none;
        }
        .controls .btn-secondary:hover {
            background-color: #5a6268;
        }
        .controls .btn-warning {
            background-color: #ffc107;
            border: none;
        }
        .controls .btn-warning:hover {
            background-color: #e0a800;
        }
        .movie-list {
            margin-top: 30px;
        }
        .movie-item {
            background-color: #333;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 10px;
            cursor: pointer;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .movie-item:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
        }
        .movie-item strong {
            font-size: 18px;
            font-weight: 600;
        }
        .movie-item p {
            margin: 5px 0 0;
            font-size: 14px;
            color: #aaa;
        }
        .video-duration {
            color: #ffc107;
        }
    </style>
</head>
<body>
    <div class="navbar">
        <h1>Movie Streamer</h1>
        <div class="nav-icons">
            <a href="{{ url_for('downloads') }}" title="Downloads"><i class="fas fa-download"></i></a>
        </div>
    </div>
    <div class="container">
        <div class="video-container">
            <h3>Now Playing: <span id="video-title">{{ current_video_name }}</span></h3>
            <p>Duration: <span id="video-duration">0</span> seconds</p>
            <video id="video-player" class="video-player" controls autoplay>
                <source id="video-source" src="{{ playlist_url }}" type="application/x-mpegURL">
                Your browser does not support the video tag.
            </video>
            <div class="controls">
                <button class="btn btn-primary" onclick="skipVideo()">Skip Video</button>
                <button class="btn btn-secondary" onclick="shuffleVideos()">Shuffle Videos</button>
                <button class="btn btn-warning" onclick="togglePlayPause()">Play/Pause</button>
            </div>
        </div>
        <div class="movie-list">
            <h3 class="text-center my-3">Available Movies</h3>
            {% for movie in movies %}
                <div class="movie-item" onclick="playMovie('{{ movie }}')">
                    <strong>{{ movie }}</strong>
                    <p>Duration: <span id="duration-{{ movie }}" class="video-duration">Loading...</span></p>
                </div>
            {% endfor %}
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <script>
        const videoPlayer = document.getElementById('video-player');
        const videoSource = document.getElementById('video-source');
        const videoTitleElement = document.getElementById('video-title');
        const videoDurationElement = document.getElementById('video-duration');
        let hls = null;

        function initializeHls() {
            if (Hls.isSupported()) {
                if (hls) hls.destroy();
                hls = new Hls();
                hls.loadSource(videoSource.src);
                hls.attachMedia(videoPlayer);
                hls.on(Hls.Events.MANIFEST_PARSED, () => videoPlayer.play());
            } else if (videoPlayer.canPlayType('application/vnd.apple.mpegurl')) {
                videoPlayer.src = videoSource.src;
                videoPlayer.addEventListener('loadedmetadata', () => videoPlayer.play());
            }
        }

        function playMovie(movie) {
            fetch(`/set-video/${movie}`)
                .then(response => response.json())
                .then(data => {
                    videoSource.src = data.next_video_url;
                    videoPlayer.load();
                    initializeHls();
                    videoTitleElement.innerText = data.video_title;
                });
        }

        function skipVideo() {
            fetch('/next-video')
                .then(response => response.json())
                .then(data => {
                    videoSource.src = data.next_video_url;
                    videoPlayer.load();
                    initializeHls();
                    videoTitleElement.innerText = data.video_title;
                });
        }

        function shuffleVideos() {
            fetch('/shuffle-videos')
                .then(response => response.json())
                .then(data => {
                    videoSource.src = data.next_video_url;
                    videoPlayer.load();
                    initializeHls();
                    videoTitleElement.innerText = data.video_title;
                });
        }

        function togglePlayPause() {
            if (videoPlayer.paused) {
                videoPlayer.play();
            } else {
                videoPlayer.pause();
            }
        }

        window.onload = () => {
            const firstMovie = document.querySelector('.movie-item');
            if (firstMovie) {
                playMovie(firstMovie.textContent.trim());
            }
        };

        videoPlayer.onloadedmetadata = function() {
            videoDurationElement.innerText = Math.round(videoPlayer.duration);
            document.querySelector(`#duration-${videoTitleElement.innerText}`).innerText = Math.round(videoPlayer.duration);
        };
    </script>
</body>
</html>''', files=files)

@app.route('/download/<filename>')
async def download_file(filename):
    """Serve files with asynchronous file reading"""
    file_path = os.path.join(VIDEO_FOLDER, filename)
    async with aiofiles.open(file_path, 'rb') as f:
        contents = await f.read()
    return await asyncio.to_thread(send_from_directory, VIDEO_FOLDER, filename, as_attachment=True)

@app.route('/hls/<movie>/<path:filename>')
async def serve_hls(movie, filename):
    """Serve HLS files asynchronously"""
    movie_folder = os.path.join(HLS_FOLDER, movie)
    file_path = os.path.join(movie_folder, filename)
    async with aiofiles.open(file_path, 'rb') as f:
        contents = await f.read()
    return contents, 200, {'Content-Type': 'application/x-mpegURL' if filename.endswith('.m3u8') else 'video/MP2T'}

@app.route('/next-video')
async def next_video():
    user_videos = session['video_list']
    session['current_video_index'] = (session['current_video_index'] + 1) % len(user_videos)
    next_video_name = user_videos[session['current_video_index']]
    next_video_url = url_for('serve_hls', movie=next_video_name, filename='playlist.m3u8')
    metadata = video_metadata.get(next_video_name, {'title': next_video_name, 'duration': 0})
    
    return jsonify({
        'next_video_url': next_video_url,
        'video_title': metadata['title'],
        'video_duration': metadata['duration']
    })

@app.route('/set-video/<video_name>')
async def set_video(video_name):
    user_videos = session['video_list']
    if video_name in user_videos:
        session['current_video_index'] = user_videos.index(video_name)
    next_video_name = user_videos[session['current_video_index']]
    next_video_url = url_for('serve_hls', movie=next_video_name, filename='playlist.m3u8')
    metadata = video_metadata.get(next_video_name, {'title': next_video_name, 'duration': 0})
    
    return jsonify({
        'next_video_url': next_video_url,
        'video_title': metadata['title'],
        'video_duration': metadata['duration']
    })

@app.route('/shuffle-videos')
async def shuffle_videos():
    session['video_list'] = random.sample(get_movies(), len(get_movies()))
    session['current_video_index'] = 0
    next_video_name = session['video_list'][session['current_video_index']]
    next_video_url = url_for('serve_hls', movie=next_video_name, filename='playlist.m3u8')
    metadata = video_metadata.get(next_video_name, {'title': next_video_name, 'duration': 0})
    
    return jsonify({
        'next_video_url': next_video_url,
        'video_title': metadata['title'],
        'video_duration': metadata['duration']
    })

async def startup():
    await process_existing_videos()




import asyncio
from werkzeug.serving import run_simple
import logging


async def startup():
    try:
        # Your startup logic here
        print("Starting video processing...")
        # Add your actual startup code
        await asyncio.sleep(1)  # Example async operation
    except Exception as e:
        logging.error(f"Startup failed: {str(e)}")
        raise

async def run_server():
    """Run both startup and flask server"""
    try:
        # Run initial video processing
        await startup()
        
        # Create a task for Flask server
        loop = asyncio.get_event_loop()
        server_task = loop.run_in_executor(
            None,
            run_simple,
            '0.0.0.0',
            5001,
            app,
            False,
            True
        )
        await server_task
    except Exception as e:
        logging.error(f"Server failed: {str(e)}")
        raise
if __name__ == '__main__':
    # Run initial video processing
    asyncio.run(startup())
    
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("Shutting down gracefully...")
