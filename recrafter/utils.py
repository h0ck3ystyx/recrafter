"""
Utility functions for Recrafter
"""

import os
import re
import hashlib
import mimetypes
from urllib.parse import urljoin, urlparse, urlunparse
from pathlib import Path
from typing import Optional, List, Tuple
import logging


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    """Setup logging configuration"""
    logger = logging.getLogger("recrafter")
    logger.setLevel(getattr(logging, level.upper()))
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def normalize_url(url: str, base_url: str) -> str:
    """Normalize a URL relative to a base URL"""
    if not url:
        return base_url
    
    # Handle relative URLs
    if url.startswith('#'):
        return base_url
    
    # Handle protocol-relative URLs
    if url.startswith('//'):
        parsed_base = urlparse(base_url)
        return f"{parsed_base.scheme}:{url}"
    
    # Handle relative URLs
    if not url.startswith(('http://', 'https://')):
        return urljoin(base_url, url)
    
    return url


def is_same_domain(url: str, base_domain: str, include_subdomains: bool = False) -> bool:
    """Check if URL is in the same domain"""
    parsed_url = urlparse(url)
    url_domain = parsed_url.netloc.lower()
    base_domain = base_domain.lower()
    
    if include_subdomains:
        return url_domain == base_domain or url_domain.endswith(f".{base_domain}")
    else:
        return url_domain == base_domain


def get_domain_from_url(url: str) -> str:
    """Extract domain from URL"""
    return urlparse(url).netloc.lower()


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage"""
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'[^\w\-_.]', '_', filename)
    
    # Limit length
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200-len(ext)] + ext
    
    return filename


def get_file_extension_from_url(url: str) -> str:
    """Get file extension from URL"""
    parsed = urlparse(url)
    path = parsed.path
    
    # Try to get extension from path
    if '.' in path:
        return os.path.splitext(path)[1]
    
    # Try to get extension from content type
    content_type = mimetypes.guess_type(url)[0]
    if content_type:
        ext = mimetypes.guess_extension(content_type)
        if ext:
            return ext
    
    return ''


def create_directory_structure(base_path: str, url_path: str) -> str:
    """Create directory structure based on URL path"""
    # Parse URL path and create directories
    path_parts = [p for p in url_path.split('/') if p]
    
    if not path_parts:
        return base_path
    
    # Create directories
    current_path = base_path
    for part in path_parts[:-1]:  # Skip the last part (filename)
        current_path = os.path.join(current_path, sanitize_filename(part))
        os.makedirs(current_path, exist_ok=True)
    
    return current_path


def get_asset_path(url: str, base_output_dir: str, asset_type: str = "assets") -> str:
    """Generate local path for an asset"""
    parsed = urlparse(url)
    path = parsed.path
    
    # Create asset directory structure
    asset_dir = os.path.join(base_output_dir, asset_type)
    
    # Handle root assets
    if path == '/':
        filename = 'index' + get_file_extension_from_url(url)
    else:
        filename = os.path.basename(path)
        if not filename:
            filename = 'index' + get_file_extension_from_url(url)
    
    # Sanitize filename
    filename = sanitize_filename(filename)
    
    # Create full path
    full_path = os.path.join(asset_dir, filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    return full_path


def calculate_file_hash(file_path: str) -> str:
    """Calculate MD5 hash of a file"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return ""


def is_text_file(content_type: str) -> bool:
    """Check if content type is text-based"""
    text_types = [
        'text/', 'application/json', 'application/xml', 'application/javascript',
        'application/css', 'application/x-yaml', 'application/x-www-form-urlencoded'
    ]
    return any(content_type.startswith(t) for t in text_types)


def clean_html_content(html: str) -> str:
    """Clean HTML content by removing scripts, ads, etc."""
    # Remove script tags
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove style tags
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove comments
    html = re.sub(r'<!--.*?-->', '', html, flags=re.DOTALL)
    
    # Remove common ad-related classes and IDs
    ad_patterns = [
        r'<[^>]*class="[^"]*(?:ad|advertisement|banner)[^"]*"[^>]*>',
        r'<[^>]*id="[^"]*(?:ad|advertisement|banner)[^"]*"[^>]*>',
        r'<[^>]*class="[^"]*(?:google|facebook|twitter)[^"]*"[^>]*>'
    ]
    
    for pattern in ad_patterns:
        html = re.sub(pattern, '', html, flags=re.IGNORECASE)
    
    return html


def extract_text_from_html(html: str) -> str:
    """Extract clean text content from HTML"""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html)
    
    # Decode HTML entities
    import html
    text = html.unescape(text)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text


def get_file_size_mb(file_path: str) -> float:
    """Get file size in MB"""
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except OSError:
        return 0.0


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"


def is_valid_url(url: str) -> bool:
    """Check if URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def get_robots_txt_url(base_url: str) -> str:
    """Get robots.txt URL for a domain"""
    parsed = urlparse(base_url)
    return f"{parsed.scheme}://{parsed.netloc}/robots.txt"
