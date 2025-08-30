"""
Core crawler engine for Recrafter
"""

import asyncio
import aiohttp
import time
from typing import Set, List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging

from .models import Page, Link, Asset, SiteMap, CrawlResult
from .config import Config
from .utils import (
    normalize_url, is_same_domain, sanitize_filename, 
    get_asset_path, is_text_file, clean_html_content,
    get_robots_txt_url, setup_logging
)
from .storage import StorageManager
from .analyzer import ContentAnalyzer


class CrawlerEngine:
    """Main crawler engine for Recrafter"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger("recrafter.crawler")
        self.visited_urls: Set[str] = set()
        self.session: Optional[aiohttp.ClientSession] = None
        self.storage = StorageManager(config.storage)
        self.analyzer = ContentAnalyzer(config.analysis)
        self.semaphore = asyncio.Semaphore(config.crawler.max_concurrent)
        
    async def __aenter__(self):
        """Async context manager entry"""
        headers = {
            'User-Agent': self.config.crawler.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        timeout = aiohttp.ClientTimeout(total=self.config.crawler.timeout)
        self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def crawl(self, start_url: str) -> CrawlResult:
        """Main crawling method"""
        self.logger.info(f"Starting crawl from: {start_url}")
        
        # Initialize result
        site_map = SiteMap(base_url=start_url)
        result = CrawlResult(site_map=site_map)
        
        # Create output directory
        await self.storage.ensure_output_directory()
        
        # Check robots.txt
        if self.config.crawler.respect_robots_txt:
            await self._check_robots_txt(start_url)
        
        # Start crawling
        try:
            await self._crawl_page(start_url, 0, site_map, result)
        except Exception as e:
            self.logger.error(f"Crawling failed: {e}")
            result.add_error(f"Crawling failed: {e}")
        finally:
            result.finalize()
            self.logger.info("Crawling completed")
        
        return result
    
    async def _crawl_page(self, url: str, depth: int, site_map: SiteMap, result: CrawlResult) -> None:
        """Crawl a single page"""
        if depth > self.config.crawler.max_depth:
            return
        
        if url in self.visited_urls:
            return
        
        self.visited_urls.add(url)
        
        async with self.semaphore:
            try:
                self.logger.info(f"Crawling {url} (depth: {depth})")
                
                # Download page
                page = await self._download_page(url, depth)
                if not page:
                    return
                
                # Save page
                await self.storage.save_page(page)
                
                # Add to site map
                site_map.add_page(page)
                
                # Analyze content
                await self.analyzer.analyze_page(page)
                
                # Extract links and assets
                links, assets = await self._extract_links_and_assets(page)
                
                # Save assets
                if self.config.storage.save_assets:
                    for asset in assets:
                        await self._download_asset(asset, page)
                
                # Add links and assets to page
                for link in links:
                    page.add_link(link)
                for asset in assets:
                    page.add_asset(asset)
                
                # Update page with extracted data
                page.links = links
                page.assets = assets
                
                # Save updated page
                await self.storage.save_page(page)
                
                # Crawl internal links
                if depth < self.config.crawler.max_depth:
                    internal_links = [link for link in links if link.is_internal]
                    for link in internal_links:
                        await self._crawl_page(link.url, depth + 1, site_map, result)
                
                # Rate limiting
                if self.config.crawler.delay > 0:
                    await asyncio.sleep(self.config.crawler.delay)
                    
            except Exception as e:
                self.logger.error(f"Error crawling {url}: {e}")
                result.add_error(f"Error crawling {url}: {e}")
    
    async def _download_page(self, url: str, depth: int) -> Optional[Page]:
        """Download a single page"""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    self.logger.warning(f"HTTP {response.status} for {url}")
                    return None
                
                content_type = response.headers.get('content-type', '').split(';')[0]
                
                if not content_type.startswith('text/html'):
                    self.logger.info(f"Skipping non-HTML content: {url} ({content_type})")
                    return None
                
                html_content = await response.text()
                
                # Clean HTML if configured
                if self.config.storage.clean_html:
                    html_content = clean_html_content(html_content)
                
                # Parse title
                soup = BeautifulSoup(html_content, 'html.parser')
                title = soup.title.string if soup.title else url
                
                # Create page object
                page = Page(
                    url=url,
                    local_path=await self.storage.get_page_path(url),
                    depth=depth,
                    title=title,
                    html_content=html_content,
                    metadata=self.analyzer.extract_metadata(soup),
                    status_code=response.status,
                    content_type=content_type,
                    size=len(html_content.encode('utf-8'))
                )
                
                return page
                
        except Exception as e:
            self.logger.error(f"Failed to download {url}: {e}")
            return None
    
    async def _extract_links_and_assets(self, page: Page) -> tuple[List[Link], List[Asset]]:
        """Extract links and assets from HTML content"""
        soup = BeautifulSoup(page.html_content, 'html.parser')
        links = []
        assets = []
        
        # Extract links
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href')
            if href:
                normalized_url = normalize_url(href, page.url)
                if is_valid_url(normalized_url):
                    is_internal = is_same_domain(normalized_url, page.domain)
                    link = Link(
                        url=normalized_url,
                        text=a_tag.get_text(strip=True),
                        title=a_tag.get('title'),
                        is_internal=is_internal
                    )
                    links.append(link)
        
        # Extract assets
        asset_selectors = [
            ('img', 'src'),
            ('link', 'href'),
            ('script', 'src'),
            ('source', 'src'),
            ('video', 'src'),
            ('audio', 'src')
        ]
        
        for tag_name, attr_name in asset_selectors:
            for tag in soup.find_all(tag_name):
                attr_value = tag.get(attr_name)
                if attr_value:
                    normalized_url = normalize_url(attr_value, page.url)
                    if is_valid_url(normalized_url):
                        asset = Asset(
                            url=normalized_url,
                            local_path=await self.storage.get_asset_path(normalized_url),
                            content_type=self._guess_content_type(normalized_url),
                            size=0,
                            checksum=""
                        )
                        assets.append(asset)
        
        return links, assets
    
    async def _download_asset(self, asset: Asset, page: Page) -> None:
        """Download an asset"""
        try:
            async with self.session.get(asset.url) as response:
                if response.status != 200:
                    return
                
                content = await response.read()
                content_type = response.headers.get('content-type', 'application/octet-stream')
                
                # Update asset with actual data
                asset.content_type = content_type
                asset.size = len(content)
                asset.checksum = hashlib.md5(content).hexdigest()
                
                # Save asset
                await self.storage.save_asset(asset, content)
                
        except Exception as e:
            self.logger.warning(f"Failed to download asset {asset.url}: {e}")
    
    def _guess_content_type(self, url: str) -> str:
        """Guess content type from URL"""
        ext = url.split('.')[-1].lower()
        content_types = {
            'css': 'text/css',
            'js': 'application/javascript',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'svg': 'image/svg+xml',
            'pdf': 'application/pdf'
        }
        return content_types.get(ext, 'application/octet-stream')
    
    async def _check_robots_txt(self, base_url: str) -> None:
        """Check robots.txt for crawling rules"""
        try:
            robots_url = get_robots_txt_url(base_url)
            async with self.session.get(robots_url) as response:
                if response.status == 200:
                    content = await response.text()
                    self.logger.info(f"Found robots.txt at {robots_url}")
                    # TODO: Implement robots.txt parsing
        except Exception as e:
            self.logger.debug(f"Could not fetch robots.txt: {e}")


def is_valid_url(url: str) -> bool:
    """Check if URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


import hashlib
