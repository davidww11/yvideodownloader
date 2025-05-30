#!/usr/bin/env python3
"""
YouTube Video Downloader API
A Flask-based API for downloading YouTube videos using yt-dlp
"""

import os
import re
import json
import logging
import tempfile
import time
import random
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)  # Enable CORS for frontend integration

# Configuration
DOWNLOAD_DIR = os.path.join(tempfile.gettempdir(), 'youtube_downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

class YouTubeVideoDownloader:
    def __init__(self):
        self.ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'extract_flat': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'referer': 'https://www.youtube.com/',
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip,deflate',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                'Keep-Alive': '300',
                'Connection': 'keep-alive',
            },
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_skip': ['configs', 'webpage']
                }
            },
            'cookiefile': None,  # 可以后续添加cookie文件路径
            'ignoreerrors': False,
            'no_warnings': False,
        }
    
    def normalize_youtube_url(self, url):
        """Normalize YouTube URLs to ensure compatibility"""
        url = url.strip()
        
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Convert various YouTube URL formats to standard format
        # Handle youtu.be short links
        if 'youtu.be/' in url:
            video_id = url.split('youtu.be/')[1].split('?')[0].split('&')[0]
            url = f'https://www.youtube.com/watch?v={video_id}'
        
        # Ensure www.youtube.com format (but avoid double www)
        if 'youtube.com' in url and 'www.youtube.com' not in url:
            url = url.replace('youtube.com', 'www.youtube.com')
        if 'm.youtube.com' in url:
            url = url.replace('m.youtube.com', 'www.youtube.com')
        
        return url
    
    def validate_youtube_url(self, url):
        """Validate if the URL is a valid YouTube video URL"""
        patterns = [
            r'https?://(www\.)?youtube\.com/watch\?v=[\w-]+',
            r'https?://youtu\.be/[\w-]+',
            r'https?://(www\.)?youtube\.com/embed/[\w-]+',
            r'https?://(www\.)?youtube\.com/v/[\w-]+',
            r'https?://m\.youtube\.com/watch\?v=[\w-]+',
            r'https?://(www\.)?youtube\.com/.+'
        ]
        
        # Use search instead of match to find pattern anywhere in the string
        return any(re.search(pattern, url) for pattern in patterns)
    
    def extract_video_info(self, url):
        """Extract video information without downloading"""
        try:
            url = self.normalize_youtube_url(url)
            
            if not self.validate_youtube_url(url):
                raise ValueError("Invalid YouTube URL")
            
            # Try different yt-dlp configurations to bypass bot detection
            configs_to_try = [
                # Configuration 1: Chrome-like headers without cookies
                {
                    'quiet': True,
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'referer': 'https://www.youtube.com/',
                    'headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                        'Cache-Control': 'max-age=0',
                    },
                    'extractor_args': {
                        'youtube': {
                            'skip': ['dash', 'hls'],
                            'player_skip': ['configs', 'webpage']
                        }
                    }
                },
                # Configuration 2: Safari-like headers
                {
                    'quiet': True,
                    'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
                    'referer': 'https://www.youtube.com/',
                    'headers': {
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                    },
                },
                # Configuration 3: Firefox-like headers
                {
                    'quiet': True,
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
                    'referer': 'https://www.youtube.com/',
                    'headers': {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'Sec-Fetch-Dest': 'document',
                        'Sec-Fetch-Mode': 'navigate',
                        'Sec-Fetch-Site': 'none',
                    },
                },
                # Configuration 4: Mobile Chrome headers
                {
                    'quiet': True,
                    'user_agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                    'referer': 'https://m.youtube.com/',
                    'headers': {
                        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Accept-Encoding': 'gzip, deflate, br',
                        'DNT': '1',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                    },
                },
                # Configuration 5: Minimal configuration
                {
                    'quiet': True,
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'referer': 'https://www.youtube.com/',
                }
            ]
            
            info = None
            last_error = None
            
            for i, config in enumerate(configs_to_try):
                try:
                    logger.info(f"Trying configuration {i+1}")
                    
                    # Add random delay between attempts to avoid rapid requests
                    if i > 0:
                        delay = random.uniform(1, 3)
                        logger.info(f"Adding {delay:.1f}s delay before next attempt")
                        time.sleep(delay)
                    
                    with yt_dlp.YoutubeDL(config) as ydl:
                        info = ydl.extract_info(url, download=False)
                        if info:
                            logger.info(f"Successfully extracted info with configuration {i+1}")
                            break
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Configuration {i+1} failed: {str(e)}")
                    continue
            
            if not info:
                # Provide more helpful error message
                if "Sign in to confirm you're not a bot" in str(last_error):
                    # Simplified, user-friendly error message that will trigger frontend special handling
                    raise ValueError("Sign in to confirm you're not a bot")
                elif "Unable to fetch GVS PO Token" in str(last_error):
                    raise ValueError("Sign in to confirm you're not a bot")
                elif "Missing required Visitor Data" in str(last_error):
                    raise ValueError("Sign in to confirm you're not a bot")
                elif "Operation not permitted" in str(last_error) and "Cookies" in str(last_error):
                    raise ValueError("Sign in to confirm you're not a bot")
                else:
                    raise ValueError(f"Failed to extract video information. Please try a different video or try again later. ({str(last_error)[:100]}...)")
                
            if 'entries' in info:
                video_info = info['entries'][0] if info['entries'] else None
            else:
                video_info = info
            
            if not video_info:
                raise ValueError("No video found in the provided URL")
            
            # Extract available formats
            formats = []
            if 'formats' in video_info and video_info['formats']:
                # 使用字典来存储每个分辨率的最佳格式
                quality_formats = {}
                for fmt in video_info['formats']:
                    if fmt.get('vcodec') != 'none':  # Only video formats
                        quality = self.get_quality_label(fmt)
                        # 获取当前格式的文件大小，确保为数字
                        try:
                            current_size = int(fmt.get('filesize') or 0)
                        except Exception:
                            current_size = 0
                        try:
                            prev_size = int(quality_formats[quality].get('raw_filesize', 0)) if quality in quality_formats else 0
                        except Exception:
                            prev_size = 0
                        # 如果这个分辨率还没有记录，或者当前格式的文件大小更大（质量更好），则更新
                        if quality not in quality_formats or current_size > prev_size:
                            quality_formats[quality] = {
                                'format_id': fmt.get('format_id', ''),
                                'url': fmt.get('url', ''),
                                'ext': fmt.get('ext', 'mp4'),
                                'quality': quality,
                                'filesize': self.format_filesize(fmt.get('filesize')),
                                'raw_filesize': current_size,
                                'filename': f"{self.sanitize_filename(video_info.get('title', 'video'))}.{fmt.get('ext', 'mp4')}"
                            }
                
                # 将去重后的格式添加到列表中（去掉raw_filesize字段）
                formats = [{k: v for k, v in f.items() if k != 'raw_filesize'} for f in quality_formats.values()]
            
            # If no formats found, try the direct URL
            if not formats and video_info.get('url'):
                formats.append({
                    'format_id': 'direct',
                    'url': video_info['url'],
                    'ext': video_info.get('ext', 'mp4'),
                    'quality': 'Standard Quality',
                    'filesize': self.format_filesize(video_info.get('filesize')),
                    'filename': f"{self.sanitize_filename(video_info.get('title', 'video'))}.{video_info.get('ext', 'mp4')}"
                })
            
            return {
                'title': video_info.get('title', 'YouTube Video'),
                'author': video_info.get('uploader', 'Unknown'),
                'duration': self.format_duration(video_info.get('duration')),
                'thumbnail': video_info.get('thumbnail', ''),
                'formats': formats[:5] if formats else []  # Limit to 5 formats
            }
                
        except Exception as e:
            logger.error(f"Error extracting video info: {str(e)}")
            raise ValueError(f"Failed to extract video information: {str(e)}")
    
    def get_quality_label(self, fmt):
        """Generate a human-readable quality label"""
        height = fmt.get('height')
        width = fmt.get('width')
        
        if height:
            if height >= 2160:
                return "4K (2160p)"
            elif height >= 1440:
                return "1440p HD"
            elif height >= 1080:
                return "1080p HD"
            elif height >= 720:
                return "720p HD"
            elif height >= 480:
                return "480p"
            elif height >= 360:
                return "360p"
            elif height >= 240:
                return "240p"
            else:
                return f"{height}p"
        elif width:
            if width >= 3840:
                return "4K (2160p)"
            elif width >= 2560:
                return "1440p HD"
            elif width >= 1920:
                return "1080p HD"
            elif width >= 1280:
                return "720p HD"
            else:
                return "Standard Quality"
        else:
            return "Standard Quality"
    
    def format_filesize(self, size):
        """Format file size in human readable format"""
        if not size:
            return "Unknown size"
        
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def format_duration(self, duration):
        """Format duration in human readable format"""
        if not duration:
            return "Unknown"
        
        hours = int(duration // 3600)
        minutes = int((duration % 3600) // 60)
        seconds = int(duration % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def sanitize_filename(self, filename):
        """Sanitize filename for safe download"""
        if not filename:
            return "video"
        
        # Remove or replace invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = filename.strip().replace(' ', '_')
        return filename[:50]  # Limit length

# Initialize downloader
downloader = YouTubeVideoDownloader()

@app.route('/')
def home():
    """Serve the main page"""
    return app.send_static_file('index.html')

@app.route('/test')
def test_page():
    """Serve the test page"""
    return app.send_static_file('test.html')

@app.route('/debug')
def debug_page():
    """Serve the debug page"""
    return app.send_static_file('debug.html')

@app.route('/api/download', methods=['POST'])
def download_video():
    """API endpoint to process video download requests"""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'URL is required'}), 400
        
        url = data['url']
        format_type = data.get('format', 'mp4')
        
        logger.info(f"Processing download request for: {url}")
        
        # Extract video information
        video_info = downloader.extract_video_info(url)
        
        if not video_info['formats']:
            return jsonify({'error': 'No downloadable video formats found'}), 404
        
        logger.info(f"Successfully extracted video info: {video_info['title']}")
        
        return jsonify(video_info)
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({'error': 'Internal server error occurred'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting YouTube Video Downloader API on port {port}")
    logger.info(f"Download directory: {DOWNLOAD_DIR}")
    
    app.run(host='0.0.0.0', port=port, debug=debug) 