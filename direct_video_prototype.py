from flask import Flask, send_file, jsonify, render_template_string, request, url_for
import os
import random
from flask import session

app = Flask(__name__)

VIDEO_FOLDER = "uploads"  # Path to your video folder
video_metadata = {}

# Get a list of all video files in the folder
videos = [video for video in os.listdir(VIDEO_FOLDER) if video.endswith(('.mp4', '.mkv'))]

# Add video metadata (title) without calculating the duration via moviepy
for video in videos:
    video_metadata[video] = {
        'title': video.split('.')[0],
        'duration': 0  # Placeholder, as duration can be extracted from the frontend (HTML5 video)
    }

@app.route('/')
def index():
    # Initialize session for each user to keep track of the current video index
    if 'current_video_index' not in session:
        session['current_video_index'] = 0  # Default to the first video

    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Miu ALfha Streamer</title>
        <link href="https://maxcdn.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" rel="stylesheet">
        <style>
            body { font-family: Arial, sans-serif; }
            .controls { margin-top: 20px; text-align: center; }
            .btn { margin: 5px; }
            .video-container { margin: 20px auto; text-align: center; }
            .video-list { margin-top: 30px; }
            .video-item { padding: 10px; border: 1px solid #ddd; margin-bottom: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1 class="text-center my-4">Miu Alfha Streamer</h1>
            <div class="video-container">
                <h3>Now Playing: <span id="video-title">{{ videos[session['current_video_index']] }}</span></h3>
                <p>Duration: <span id="video-duration">0</span> seconds</p>
                <video id="video-player" controls autoplay style="width: 100%; max-width: 720px;">
                    <source src="{{ url_for('stream_video', video_name=videos[session['current_video_index']]) }}" type="video/mp4">
                    <source src="{{ url_for('stream_video', video_name=videos[session['current_video_index']]) }}" type="video/x-matroska">
                    Your browser does not support the video tag.
                </video>
            </div>
            <div class="controls">
                <button class="btn btn-primary" onclick="skipVideo()">Skip Video</button>
                <button class="btn btn-secondary" onclick="shuffleVideos()">Shuffle Videos</button>
                <button class="btn btn-warning" onclick="togglePlayPause()">Play/Pause</button>
            </div>

            <!-- Displaying Video List -->
            <div class="video-list">
                <h3>Available Videos</h3>
                {% for video in videos %}
                    <div class="video-item">
                        <strong>{{ video }}</strong>
                        <p>Duration: <span id="duration-{{ video }}" class="video-duration">Loading...</span></p>
                        <button class="btn btn-info" onclick="playVideo('{{ video }}')">Play Video</button>
                    </div>
                {% endfor %}
            </div>
        </div>

        <script>
            let videoElement = document.getElementById('video-player');
            let videoTitleElement = document.getElementById('video-title');
            let videoDurationElement = document.getElementById('video-duration');
            let currentVideoIndex = {{ session['current_video_index'] }};

            // Fetch and update video duration dynamically when the video metadata is loaded
            videoElement.onloadedmetadata = function() {
                videoDurationElement.innerText = Math.round(videoElement.duration); // Duration in seconds
                document.getElementById('duration-' + videoTitleElement.innerText).innerText = Math.round(videoElement.duration);
            };

            videoElement.onended = function() {
                fetch('/next-video')
                    .then(response => response.json())
                    .then(data => {
                        currentVideoIndex = data.index;
                        videoTitleElement.innerText = data.video_title;
                        videoDurationElement.innerText = data.video_duration;
                        videoElement.src = data.next_video_url;
                        videoElement.play();
                    });
            }

            function playVideo(videoName) {
                fetch('/set-video/' + videoName)
                    .then(response => response.json())
                    .then(data => {
                        currentVideoIndex = data.index;
                        videoTitleElement.innerText = data.video_title;
                        videoDurationElement.innerText = data.video_duration;
                        videoElement.src = data.next_video_url;
                        videoElement.play();
                    });
            }

            function skipVideo() {
                fetch('/next-video?skip=true')
                    .then(response => response.json())
                    .then(data => {
                        currentVideoIndex = data.index;
                        videoTitleElement.innerText = data.video_title;
                        videoDurationElement.innerText = data.video_duration;
                        videoElement.src = data.next_video_url;
                        videoElement.play();
                    });
            }

            function shuffleVideos() {
                fetch('/shuffle-videos')
                    .then(response => response.json())
                    .then(data => {
                        currentVideoIndex = 0;
                        videoTitleElement.innerText = data.video_title;
                        videoDurationElement.innerText = data.video_duration;
                        videoElement.src = data.next_video_url;
                        videoElement.play();
                    });
            }

            function togglePlayPause() {
                if (videoElement.paused) {
                    videoElement.play();
                } else {
                    videoElement.pause();
                }
            }
        </script>
    </body>
    </html>
    """, videos=videos, video_metadata=video_metadata)

@app.route('/stream-video/<video_name>')
def stream_video(video_name):
    video_path = os.path.join(VIDEO_FOLDER, video_name)
    if os.path.exists(video_path):
        return send_file(video_path, as_attachment=False)
    else:
        return render_template_string("""<h1>Sorry, this video is unavailable!</h1><a href="/">Go back to the main page</a>"""), 404

@app.route('/next-video')
def next_video():
    skip = request.args.get('skip', 'false').lower() == 'true'
    
    # Skip to next video if needed
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
    app.secret_key = 'your_secret_key_here'  # Set a secret key for sessions
    app.run()  # Run the app without ngrok
