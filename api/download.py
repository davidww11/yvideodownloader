#!/usr/bin/env python3
"""
Vercel Serverless Function for YouTube Video Download API
"""

import os
import re
import json
import logging
from datetime import datetime
from http.server import BaseHTTPRequestHandler
import yt_dlp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YouTubeVideoDownloader:
    def __init__(self):
        self.ydl_opts = {
            'format': 'best[ext=mp4]/best',
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
            
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    raise ValueError("Could not extract video information")
                
                if 'entries' in info:
                    video_info = info['entries'][0] if info['entries'] else None
                else:
                    video_info = info
                
                if not video_info:
                    raise ValueError("No video found in the provided URL")
                
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
                    'formats': formats[:5] if formats else []
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
        
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        filename = filename.strip().replace(' ', '_')
        return filename[:50]

# Initialize downloader
downloader = YouTubeVideoDownloader()

class handler(BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()
        self.wfile.write(b'')

    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            if not data or 'url' not in data:
                self._set_headers(400)
                self.wfile.write(json.dumps({'error': 'URL is required'}).encode('utf-8'))
                return
            
            url = data['url']
            format_type = data.get('format', 'mp4')
            
            logger.info(f"Processing download request for: {url}")
            
            video_info = downloader.extract_video_info(url)
            
            if not video_info['formats']:
                self._set_headers(404)
                self.wfile.write(json.dumps({'error': 'No downloadable video formats found'}).encode('utf-8'))
                return
            
            logger.info(f"Successfully extracted video info: {video_info['title']}")
            
            self._set_headers(200)
            self.wfile.write(json.dumps(video_info).encode('utf-8'))
            
        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            self._set_headers(400)
            self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': 'Internal server error occurred'}).encode('utf-8'))

    def do_GET(self):
        self._set_headers(405)
        self.wfile.write(json.dumps({'error': 'Method not allowed'}).encode('utf-8')) 