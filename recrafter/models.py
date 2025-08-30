"""
Data models for Recrafter
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from datetime import datetime
from urllib.parse import urlparse
import hashlib


@dataclass
class Asset:
    """Represents a downloaded asset (image, CSS, JS, etc.)"""
    url: str
    local_path: str
    content_type: str
    size: int
    checksum: str
    downloaded_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_response(cls, url: str, local_path: str, content_type: str, content: bytes) -> 'Asset':
        """Create asset from HTTP response"""
        return cls(
            url=url,
            local_path=local_path,
            content_type=content_type,
            size=len(content),
            checksum=hashlib.md5(content).hexdigest()
        )


@dataclass
class Link:
    """Represents a link found in HTML"""
    url: str
    text: str
    title: Optional[str] = None
    rel: Optional[str] = None
    is_internal: bool = True
    is_asset: bool = False


@dataclass
class Component:
    """Represents a reusable component found in HTML"""
    selector: str
    tag_name: str
    classes: List[str] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)
    content_sample: Optional[str] = None
    frequency: int = 1


@dataclass
class PageMetadata:
    """Metadata extracted from a page"""
    title: Optional[str] = None
    description: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    author: Optional[str] = None
    language: Optional[str] = None
    canonical_url: Optional[str] = None
    og_tags: Dict[str, str] = field(default_factory=dict)
    twitter_tags: Dict[str, str] = field(default_factory=dict)
    page_type: Optional[str] = None


@dataclass
class Page:
    """Represents a crawled HTML page"""
    url: str
    local_path: str
    depth: int
    title: str
    html_content: str
    metadata: PageMetadata
    links: List[Link] = field(default_factory=list)
    assets: List[Asset] = field(default_factory=list)
    components: List[Component] = field(default_factory=list)
    layout_info: Optional[Dict[str, Any]] = None
    crawled_at: datetime = field(default_factory=datetime.now)
    status_code: int = 200
    content_type: str = "text/html"
    size: int = 0
    
    @property
    def domain(self) -> str:
        """Get domain from URL"""
        return urlparse(self.url).netloc
    
    @property
    def path(self) -> str:
        """Get path from URL"""
        return urlparse(self.url).path
    
    @property
    def is_homepage(self) -> bool:
        """Check if this is the homepage"""
        return self.path in ['', '/', '/index.html']
    
    def add_link(self, link: Link) -> None:
        """Add a link to the page"""
        self.links.append(link)
    
    def add_asset(self, asset: Asset) -> None:
        """Add an asset to the page"""
        self.assets.append(asset)
    
    def add_component(self, component: Component) -> None:
        """Add a component to the page"""
        # Check if component already exists and increment frequency
        for existing in self.components:
            if existing.selector == component.selector:
                existing.frequency += 1
                return
        
        self.components.append(component)


@dataclass
class SiteMap:
    """Represents the site structure and navigation"""
    base_url: str
    pages: List[Page] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_page(self, page: Page) -> None:
        """Add a page to the sitemap"""
        self.pages.append(page)
    
    def get_pages_by_depth(self, depth: int) -> List[Page]:
        """Get all pages at a specific depth"""
        return [p for p in self.pages if p.depth == depth]
    
    def get_page_by_url(self, url: str) -> Optional[Page]:
        """Get a page by its URL"""
        for page in self.pages:
            if page.url == url:
                return page
        return None
    
    def get_internal_links(self) -> List[Link]:
        """Get all internal links from all pages"""
        links = []
        for page in self.pages:
            links.extend([link for link in page.links if link.is_internal])
        return links
    
    def get_external_links(self) -> List[Link]:
        """Get all external links from all pages"""
        links = []
        for page in self.pages:
            links.extend([link for link in page.links if not link.is_internal])
        return links
    
    def get_assets(self) -> List[Asset]:
        """Get all assets from all pages"""
        assets = []
        for page in self.pages:
            assets.extend(page.assets)
        return assets
    
    def get_components(self) -> List[Component]:
        """Get all components from all pages"""
        components = []
        for page in self.pages:
            components.extend(page.components)
        return components


@dataclass
class ContentModel:
    """Represents a content model for CMS"""
    name: str
    fields: List[Dict[str, Any]] = field(default_factory=list)
    description: Optional[str] = None
    page_type: Optional[str] = None
    sample_pages: List[str] = field(default_factory=list)
    
    def add_field(self, name: str, field_type: str, required: bool = False, 
                  description: Optional[str] = None) -> None:
        """Add a field to the content model"""
        field_def = {
            'name': name,
            'type': field_type,
            'required': required,
            'description': description
        }
        self.fields.append(field_def)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'fields': self.fields,
            'description': self.description,
            'page_type': self.page_type,
            'sample_pages': self.sample_pages
        }


@dataclass
class CrawlResult:
    """Result of a crawling operation"""
    site_map: SiteMap
    content_models: List[ContentModel] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def add_error(self, error: str) -> None:
        """Add an error message"""
        self.errors.append(error)
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message"""
        self.warnings.append(warning)
    
    def add_content_model(self, model: ContentModel) -> None:
        """Add a content model"""
        self.content_models.append(model)
    
    def finalize(self) -> None:
        """Mark crawl as completed"""
        self.completed_at = datetime.now()
        
        # Generate statistics
        self.statistics = {
            'total_pages': len(self.site_map.pages),
            'total_assets': len(self.site_map.get_assets()),
            'total_links': len(self.site_map.get_internal_links()) + len(self.site_map.get_external_links()),
            'total_components': len(self.site_map.get_components()),
            'content_models': len(self.content_models),
            'errors': len(self.errors),
            'warnings': len(self.warnings),
            'duration_seconds': (self.completed_at - self.started_at).total_seconds()
        }
