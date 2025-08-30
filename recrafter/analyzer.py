"""
Content analysis and extraction for Recrafter
"""

import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup, Tag
import logging

from .models import Page, Component, PageMetadata, ContentModel
from .config import AnalysisConfig
from .utils import extract_text_from_html


class ContentAnalyzer:
    """Analyzes HTML content to extract metadata and components"""
    
    def __init__(self, config: AnalysisConfig):
        self.config = config
        self.logger = logging.getLogger("recrafter.analyzer")
        
        # Common component patterns
        self.component_patterns = [
            # Navigation
            ('nav', 'navigation'),
            ('header', 'header'),
            ('footer', 'footer'),
            ('menu', 'menu'),
            ('sidebar', 'sidebar'),
            
            # Content
            ('main', 'main_content'),
            ('article', 'article'),
            ('section', 'section'),
            ('aside', 'aside'),
            
            # Forms
            ('form', 'form'),
            ('input', 'input'),
            ('button', 'button'),
            
            # Media
            ('img', 'image'),
            ('video', 'video'),
            ('audio', 'audio'),
            ('carousel', 'carousel'),
            ('slider', 'slider'),
            
            # Interactive
            ('modal', 'modal'),
            ('dropdown', 'dropdown'),
            ('tabs', 'tabs'),
            ('accordion', 'accordion')
        ]
    
    async def analyze_page(self, page: Page) -> None:
        """Analyze a page and extract components and metadata"""
        try:
            soup = BeautifulSoup(page.html_content, 'html.parser')
            
            # Extract metadata
            if self.config.extract_metadata:
                page.metadata = self.extract_metadata(soup)
            
            # Extract components
            if self.config.extract_components:
                page.components = self.extract_components(soup)
            
            # Identify page type
            if self.config.identify_page_types:
                page_type = self.identify_page_type(page, soup)
                if page_type:
                    page.metadata.page_type = page_type
            
            self.logger.debug(f"Analyzed page: {page.url}")
            
        except Exception as e:
            self.logger.error(f"Failed to analyze page {page.url}: {e}")
    
    def extract_metadata(self, soup: BeautifulSoup) -> PageMetadata:
        """Extract metadata from HTML"""
        metadata = PageMetadata()
        
        # Title
        title_tag = soup.find('title')
        if title_tag:
            metadata.title = title_tag.get_text(strip=True)
        
        # Meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name', '').lower()
            content = meta.get('content', '')
            
            if name == 'description':
                metadata.description = content
            elif name == 'keywords':
                metadata.keywords = [kw.strip() for kw in content.split(',') if kw.strip()]
            elif name == 'author':
                metadata.author = content
            elif name == 'language':
                metadata.language = content
        
        # Canonical URL
        canonical = soup.find('link', rel='canonical')
        if canonical:
            metadata.canonical_url = canonical.get('href')
        
        # Open Graph tags
        for meta in soup.find_all('meta', property=re.compile(r'^og:')):
            property_name = meta.get('property', '').replace('og:', '')
            content = meta.get('content', '')
            if property_name and content:
                metadata.og_tags[property_name] = content
        
        # Twitter tags
        for meta in soup.find_all('meta', name=re.compile(r'^twitter:')):
            name = meta.get('name', '').replace('twitter:', '')
            content = meta.get('content', '')
            if name and content:
                metadata.twitter_tags[name] = content
        
        return metadata
    
    def extract_components(self, soup: BeautifulSoup) -> List[Component]:
        """Extract reusable components from HTML"""
        components = []
        
        # Extract by tag patterns
        for tag_name, component_type in self.component_patterns:
            elements = soup.find_all(tag_name)
            for element in elements:
                component = self._create_component_from_element(element, component_type)
                if component:
                    components.append(component)
        
        # Extract by common class patterns
        components.extend(self._extract_by_class_patterns(soup))
        
        # Extract by ID patterns
        components.extend(self._extract_by_id_patterns(soup))
        
        # Extract forms
        components.extend(self._extract_forms(soup))
        
        # Extract navigation
        components.extend(self._extract_navigation(soup))
        
        return components
    
    def _create_component_from_element(self, element: Tag, component_type: str) -> Optional[Component]:
        """Create a component from a DOM element"""
        try:
            # Generate selector
            selector = self._generate_selector(element)
            
            # Extract classes
            classes = element.get('class', [])
            if isinstance(classes, str):
                classes = [classes]
            
            # Extract attributes
            attributes = {}
            for attr, value in element.attrs.items():
                if attr not in ['class', 'id']:
                    attributes[attr] = str(value)
            
            # Extract content sample
            content_sample = element.get_text(strip=True)[:100] if element.get_text(strip=True) else None
            
            return Component(
                selector=selector,
                tag_name=element.name,
                classes=classes,
                attributes=attributes,
                content_sample=content_sample
            )
            
        except Exception as e:
            self.logger.debug(f"Failed to create component from element: {e}")
            return None
    
    def _generate_selector(self, element: Tag) -> str:
        """Generate a CSS selector for an element"""
        try:
            # Try ID first
            if element.get('id'):
                return f"#{element['id']}"
            
            # Try class
            if element.get('class'):
                classes = element.get('class')
                if isinstance(classes, list):
                    return f".{'.'.join(classes)}"
                else:
                    return f".{classes}"
            
            # Generate tag-based selector
            selector = element.name
            
            # Add parent context if available
            parent = element.parent
            if parent and parent.name != '[document]':
                selector = f"{parent.name} > {selector}"
            
            return selector
            
        except Exception:
            return element.name if element.name else 'unknown'
    
    def _extract_by_class_patterns(self, soup: BeautifulSoup) -> List[Component]:
        """Extract components by common class patterns"""
        components = []
        
        # Common class patterns for components
        class_patterns = [
            r'nav(?:igation)?',
            r'menu',
            r'sidebar',
            r'header',
            r'footer',
            r'content',
            r'form',
            r'button',
            r'card',
            r'tile',
            r'widget',
            r'component'
        ]
        
        for pattern in class_patterns:
            regex = re.compile(pattern, re.IGNORECASE)
            elements = soup.find_all(class_=regex)
            
            for element in elements:
                component = self._create_component_from_element(element, f"class_{pattern}")
                if component:
                    components.append(component)
        
        return components
    
    def _extract_by_id_patterns(self, soup: BeautifulSoup) -> List[Component]:
        """Extract components by common ID patterns"""
        components = []
        
        # Common ID patterns for components
        id_patterns = [
            r'nav(?:igation)?',
            r'menu',
            r'sidebar',
            r'header',
            r'footer',
            r'content',
            r'form',
            r'button',
            r'card',
            r'tile',
            r'widget',
            r'component'
        ]
        
        for pattern in id_patterns:
            regex = re.compile(pattern, re.IGNORECASE)
            elements = soup.find_all(id=regex)
            
            for element in elements:
                component = self._create_component_from_element(element, f"id_{pattern}")
                if component:
                    components.append(component)
        
        return components
    
    def _extract_forms(self, soup: BeautifulSoup) -> List[Component]:
        """Extract form components"""
        components = []
        
        forms = soup.find_all('form')
        for form in forms:
            component = self._create_component_from_element(form, 'form')
            if component:
                # Add form-specific attributes
                component.attributes['action'] = form.get('action', '')
                component.attributes['method'] = form.get('method', 'get')
                components.append(component)
        
        return components
    
    def _extract_navigation(self, soup: BeautifulSoup) -> List[Component]:
        """Extract navigation components"""
        components = []
        
        # Look for navigation elements
        nav_elements = soup.find_all(['nav', 'ul', 'ol'])
        
        for element in nav_elements:
            # Check if it looks like navigation
            if self._is_navigation_element(element):
                component = self._create_component_from_element(element, 'navigation')
                if component:
                    components.append(component)
        
        return components
    
    def _is_navigation_element(self, element: Tag) -> bool:
        """Check if an element looks like navigation"""
        # Check for navigation-related classes
        classes = element.get('class', [])
        if isinstance(classes, str):
            classes = [classes]
        
        nav_classes = ['nav', 'navigation', 'menu', 'breadcrumb', 'pagination']
        if any(nav_class in ' '.join(classes).lower() for nav_class in nav_classes):
            return True
        
        # Check for navigation-related IDs
        element_id = element.get('id', '').lower()
        if any(nav_id in element_id for nav_id in nav_classes):
            return True
        
        # Check for navigation-related children
        nav_children = element.find_all(['a', 'li'])
        if len(nav_children) > 2:  # Likely navigation if many links
            return True
        
        return False
    
    def identify_page_type(self, page: Page, soup: BeautifulSoup) -> Optional[str]:
        """Identify the type of page"""
        url = page.url.lower()
        title = page.title.lower()
        content = extract_text_from_html(page.html_content).lower()
        
        # Check for common page types
        if any(word in url for word in ['/blog/', '/news/', '/article/']):
            return 'blog_post'
        elif any(word in url for word in ['/product/', '/item/', '/detail/']):
            return 'product_page'
        elif any(word in url for word in ['/category/', '/collection/']):
            return 'category_page'
        elif any(word in url for word in ['/contact', '/about', '/team']):
            return 'information_page'
        elif any(word in url for word in ['/search', '/results']):
            return 'search_page'
        elif page.is_homepage:
            return 'homepage'
        elif any(word in title for word in ['login', 'signin', 'register', 'signup']):
            return 'authentication_page'
        elif soup.find('form'):
            return 'form_page'
        
        return 'general_page'
    
    def generate_content_models(self, pages: List[Page]) -> List[ContentModel]:
        """Generate content models from analyzed pages"""
        if not self.config.create_content_models:
            return []
        
        models = []
        
        # Group pages by type
        pages_by_type = {}
        for page in pages:
            page_type = page.metadata.page_type or 'general_page'
            if page_type not in pages_by_type:
                pages_by_type[page_type] = []
            pages_by_type[page_type].append(page)
        
        # Generate model for each page type
        for page_type, type_pages in pages_by_type.items():
            model = self._create_content_model(page_type, type_pages)
            if model:
                models.append(model)
        
        return models
    
    def _create_content_model(self, page_type: str, pages: List[Page]) -> Optional[ContentModel]:
        """Create a content model for a specific page type"""
        try:
            model = ContentModel(
                name=f"{page_type.replace('_', ' ').title()} Model",
                page_type=page_type,
                description=f"Content model for {page_type} pages"
            )
            
            # Add sample pages
            model.sample_pages = [page.url for page in pages[:5]]  # Limit to 5 examples
            
            # Add common fields based on page type
            if page_type == 'homepage':
                model.add_field('title', 'text', required=True, description='Page title')
                model.add_field('hero_content', 'rich_text', description='Hero section content')
                model.add_field('featured_content', 'content_reference', description='Featured content items')
            
            elif page_type == 'blog_post':
                model.add_field('title', 'text', required=True, description='Post title')
                model.add_field('content', 'rich_text', required=True, description='Post content')
                model.add_field('author', 'text', description='Post author')
                model.add_field('publish_date', 'date', description='Publication date')
                model.add_field('tags', 'text_list', description='Post tags')
            
            elif page_type == 'product_page':
                model.add_field('title', 'text', required=True, description='Product name')
                model.add_field('description', 'rich_text', description='Product description')
                model.add_field('price', 'number', description='Product price')
                model.add_field('images', 'image_list', description='Product images')
                model.add_field('specifications', 'key_value_list', description='Product specs')
            
            elif page_type == 'form_page':
                model.add_field('title', 'text', required=True, description='Form title')
                model.add_field('description', 'rich_text', description='Form description')
                model.add_field('form_fields', 'form_field_list', description='Form field definitions')
                model.add_field('submit_button_text', 'text', description='Submit button text')
            
            else:
                # Generic model
                model.add_field('title', 'text', required=True, description='Page title')
                model.add_field('content', 'rich_text', description='Page content')
                model.add_field('metadata', 'metadata_group', description='Page metadata')
            
            return model
            
        except Exception as e:
            self.logger.error(f"Failed to create content model for {page_type}: {e}")
            return None
