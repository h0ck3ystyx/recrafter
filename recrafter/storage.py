"""
Storage management for Recrafter
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import logging
from bs4 import BeautifulSoup
from datetime import datetime

from .models import Page, Asset, SiteMap, CrawlResult
from .config import StorageConfig
from .utils import sanitize_filename, create_directory_structure


class StorageManager:
    """Manages file storage and organization"""
    
    def __init__(self, config: StorageConfig):
        self.config = config
        self.logger = logging.getLogger("recrafter.storage")
        self.base_dir = Path(config.output_dir)
        
        # Directory structure
        self.pages_dir = self.base_dir / "pages"
        self.assets_dir = self.base_dir / "assets"
        self.metadata_dir = self.base_dir / "metadata"
        self.logs_dir = self.base_dir / "logs"
        
    async def ensure_output_directory(self) -> None:
        """Ensure output directory structure exists"""
        try:
            # Create main directories
            for directory in [self.pages_dir, self.assets_dir, self.metadata_dir, self.logs_dir]:
                directory.mkdir(parents=True, exist_ok=True)
            
            # Create asset subdirectories
            asset_subdirs = ['images', 'css', 'js', 'fonts', 'documents', 'other']
            for subdir in asset_subdirs:
                (self.assets_dir / subdir).mkdir(exist_ok=True)
            
            self.logger.info(f"Output directory structure created: {self.base_dir}")
            
        except Exception as e:
            self.logger.error(f"Failed to create output directory: {e}")
            raise
    
    async def get_page_path(self, url: str) -> str:
        """Generate local path for a page"""
        parsed = urlparse(url)
        path = parsed.path
        
        # Handle root page
        if path in ['', '/']:
            filename = 'index.html'
        else:
            # Remove leading slash and get filename
            path = path.lstrip('/')
            if not path:
                filename = 'index.html'
            elif path.endswith('/'):
                filename = os.path.join(path, 'index.html')
            else:
                # Check if path has extension
                if '.' in os.path.basename(path):
                    filename = path
                else:
                    filename = f"{path}.html"
        
        # Sanitize path
        filename = sanitize_filename(filename)
        full_path = self.pages_dir / filename
        
        # Ensure directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        return str(full_path)
    
    async def get_asset_path(self, url: str) -> str:
        """Generate local path for an asset"""
        parsed = urlparse(url)
        path = parsed.path
        filename = os.path.basename(path)
        
        if not filename:
            # Generate filename from content type or URL
            ext = self._get_extension_from_url(url)
            filename = f"asset_{hash(url) % 10000}{ext}"
        
        # Determine asset type and subdirectory
        asset_type = self._categorize_asset(url)
        subdir = self.assets_dir / asset_type
        
        # Ensure subdirectory exists
        subdir.mkdir(exist_ok=True)
        
        # Sanitize filename
        filename = sanitize_filename(filename)
        full_path = subdir / filename
        
        return str(full_path)
    
    async def save_page(self, page: Page) -> None:
        """Save a page to disk"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(page.local_path), exist_ok=True)
            
            # Save HTML content
            with open(page.local_path, 'w', encoding='utf-8') as f:
                f.write(page.html_content)
            
            self.logger.debug(f"Page saved: {page.local_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save page {page.url}: {e}")
            raise
    
    async def save_asset(self, asset: Asset, content: bytes) -> None:
        """Save an asset to disk"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(asset.local_path), exist_ok=True)
            
            # Save binary content
            with open(asset.local_path, 'wb') as f:
                f.write(content)
            
            self.logger.debug(f"Asset saved: {asset.local_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save asset {asset.url}: {e}")
            raise
    
    async def save_metadata(self, crawl_result: CrawlResult) -> None:
        """Save metadata and analysis results"""
        try:
            # Save sitemap
            sitemap_path = self.metadata_dir / "sitemap.json"
            with open(sitemap_path, 'w', encoding='utf-8') as f:
                json.dump(self._sitemap_to_dict(crawl_result.site_map), f, indent=2, default=str)
            
            # Save content models
            if crawl_result.content_models:
                models_path = self.metadata_dir / "content_models.json"
                with open(models_path, 'w', encoding='utf-8') as f:
                    json.dump([model.to_dict() for model in crawl_result.content_models], f, indent=2)
            
            # Save crawl summary
            summary_path = self.metadata_dir / "crawl_summary.json"
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'statistics': crawl_result.statistics,
                    'errors': crawl_result.errors,
                    'warnings': crawl_result.warnings,
                    'started_at': crawl_result.started_at.isoformat(),
                    'completed_at': crawl_result.completed_at.isoformat() if crawl_result.completed_at else None
                }, f, indent=2, default=str)
            
            self.logger.info("Metadata saved successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to save metadata: {e}")
            raise
    
    def _categorize_asset(self, url: str) -> str:
        """Categorize asset by type"""
        ext = self._get_extension_from_url(url).lower()
        
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico']:
            return 'images'
        elif ext in ['.css']:
            return 'css'
        elif ext in ['.js']:
            return 'js'
        elif ext in ['.woff', '.woff2', '.ttf', '.otf', '.eot']:
            return 'fonts'
        elif ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx']:
            return 'documents'
        else:
            return 'other'
    
    def _get_extension_from_url(self, url: str) -> str:
        """Get file extension from URL"""
        path = urlparse(url).path
        if '.' in path:
            return os.path.splitext(path)[1]
        return ''
    
    def _sitemap_to_dict(self, site_map: SiteMap) -> Dict[str, Any]:
        """Convert sitemap to dictionary for JSON serialization"""
        return {
            'base_url': site_map.base_url,
            'created_at': site_map.created_at.isoformat(),
            'total_pages': len(site_map.pages),
            'pages': [
                {
                    'url': page.url,
                    'local_path': page.local_path,
                    'depth': page.depth,
                    'title': page.title,
                    'crawled_at': page.crawled_at.isoformat(),
                    'status_code': page.status_code,
                    'content_type': page.content_type,
                    'size': page.size,
                    'links_count': len(page.links),
                    'assets_count': len(page.assets),
                    'components_count': len(page.components)
                }
                for page in site_map.pages
            ]
        }
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get information about storage usage"""
        try:
            total_size = 0
            file_counts = {
                'pages': 0,
                'assets': 0,
                'metadata': 0
            }
            
            # Count pages
            for file_path in self.pages_dir.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_counts['pages'] += 1
            
            # Count assets
            for file_path in self.assets_dir.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_counts['assets'] += 1
            
            # Count metadata
            for file_path in self.metadata_dir.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_counts['metadata'] += 1
            
            return {
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'file_counts': file_counts,
                'base_directory': str(self.base_dir)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get storage info: {e}")
            return {}
    
    async def cleanup_old_files(self, max_age_days: int = 30) -> None:
        """Clean up old files"""
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_days * 24 * 60 * 60
            
            cleaned_count = 0
            
            for directory in [self.pages_dir, self.assets_dir, self.metadata_dir]:
                for file_path in directory.rglob('*'):
                    if file_path.is_file():
                        file_age = current_time - file_path.stat().st_mtime
                        if file_age > max_age_seconds:
                            file_path.unlink()
                            cleaned_count += 1
            
            if cleaned_count > 0:
                self.logger.info(f"Cleaned up {cleaned_count} old files")
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old files: {e}")
    
    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """Create a backup of the output directory"""
        try:
            import shutil
            from datetime import datetime
            
            if not backup_name:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            backup_path = self.base_dir.parent / backup_name
            
            # Create backup
            shutil.copytree(self.base_dir, backup_path)
            
            self.logger.info(f"Backup created: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            raise
    
    def load_crawled_data(self) -> Dict[str, Any]:
        """Load all crawled data from storage for analysis"""
        try:
            data = {
                'pages': [],
                'assets': [],
                'metadata': {},
                'storage_info': self.get_storage_info()
            }
            
            # Load metadata
            metadata_files = ['sitemap.json', 'content_models.json', 'crawl_summary.json']
            for filename in metadata_files:
                metadata_path = self.metadata_dir / filename
                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            data['metadata'][filename.replace('.json', '')] = json.load(f)
                    except Exception as e:
                        self.logger.warning(f"Failed to load {filename}: {e}")
            
            # Load pages
            for html_file in self.pages_dir.rglob('*.html'):
                try:
                    page_data = self._load_page_from_file(html_file)
                    if page_data:
                        data['pages'].append(page_data)
                except Exception as e:
                    self.logger.warning(f"Failed to load page {html_file}: {e}")
            
            # Load assets info
            for asset_dir in ['images', 'css', 'js', 'fonts', 'documents', 'other']:
                asset_path = self.assets_dir / asset_dir
                if asset_path.exists():
                    for asset_file in asset_path.rglob('*'):
                        if asset_file.is_file():
                            try:
                                asset_info = self._get_asset_info(asset_file, asset_dir)
                                data['assets'].append(asset_info)
                            except Exception as e:
                                self.logger.warning(f"Failed to load asset info {asset_file}: {e}")
            
            self.logger.info(f"Loaded {len(data['pages'])} pages and {len(data['assets'])} assets")
            return data
            
        except Exception as e:
            self.logger.error(f"Failed to load crawled data: {e}")
            return {}
    
    def _load_page_from_file(self, html_file: Path) -> Optional[Dict[str, Any]]:
        """Load a single page from HTML file"""
        try:
            # Read HTML content
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Parse HTML to extract basic info
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Get title
            title_tag = soup.find('title')
            title = title_tag.get_text(strip=True) if title_tag else html_file.stem
            
            # Get URL from file path (approximate)
            relative_path = html_file.relative_to(self.pages_dir)
            url_path = str(relative_path).replace('\\', '/').replace('.html', '')
            if url_path == 'index':
                url_path = '/'
            elif not url_path.startswith('/'):
                url_path = f"/{url_path}"
            
            page_data = {
                'url': url_path,
                'local_path': str(html_file),
                'title': title,
                'html_content': html_content,
                'depth': len(relative_path.parts) - 1,
                'size': len(html_content),
                'content_type': 'text/html',
                'status_code': 200,
                'crawled_at': datetime.fromtimestamp(html_file.stat().st_mtime).isoformat(),
                'metadata': {},
                'components': [],
                'layout_info': None
            }
            
            return page_data
            
        except Exception as e:
            self.logger.error(f"Failed to load page from {html_file}: {e}")
            return None
    
    def _get_asset_info(self, asset_file: Path, asset_type: str) -> Dict[str, Any]:
        """Get information about an asset file"""
        try:
            stat = asset_file.stat()
            return {
                'local_path': str(asset_file),
                'asset_type': asset_type,
                'filename': asset_file.name,
                'size': stat.st_size,
                'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'extension': asset_file.suffix.lower()
            }
        except Exception as e:
            self.logger.error(f"Failed to get asset info for {asset_file}: {e}")
            return {}
