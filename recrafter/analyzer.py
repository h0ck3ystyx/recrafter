"""
Content analysis and extraction for Recrafter
"""

import re
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup, Tag
import logging
from collections import defaultdict, Counter
from difflib import SequenceMatcher
import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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
        
        # Layout detection patterns
        self.layout_patterns = {
            'grid_system': [
                r'container', r'row', r'col', r'grid', r'flex', r'flexbox',
                r'bootstrap', r'foundation', r'material', r'semantic'
            ],
            'sections': [
                r'hero', r'banner', r'header', r'footer', r'main', r'content',
                r'sidebar', r'aside', r'navigation', r'breadcrumb'
            ],
            'components': [
                r'card', r'tile', r'widget', r'panel', r'box', r'container',
                r'wrapper', r'holder', r'block', r'section'
            ]
        }
    
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
            
            # Extract layout information
            if self.config.extract_layout_patterns:
                page.layout_info = self.extract_layout_patterns(soup)
            
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
        for meta in soup.find_all('meta'):
            meta_name = meta.get('name', '')
            if meta_name and meta_name.startswith('twitter:'):
                name = meta_name.replace('twitter:', '')
                content = meta.get('content', '')
                if name and content:
                    metadata.twitter_tags[name] = content
        
        return metadata
    
    def extract_components(self, soup: BeautifulSoup) -> List[Component]:
        """Extract reusable components from HTML"""
        components = []
        
        # Extract by tag patterns
        for element_tag, component_type in self.component_patterns:
            elements = soup.find_all(element_tag)
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
        nav_elements = []
        for tag_name in ['nav', 'ul', 'ol']:
            nav_elements.extend(soup.find_all(tag_name))
        
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
        nav_children = []
        for child_tag in ['a', 'li']:
            nav_children.extend(element.find_all(child_tag))
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
    
    def extract_layout_patterns(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract layout patterns and CSS classes"""
        layout_info = {
            'grid_system': [],
            'sections': [],
            'components': [],
            'css_framework': None,
            'responsive_classes': [],
            'layout_structure': {}
        }
        
        # Extract all CSS classes
        all_classes = set()
        for element in soup.find_all(class_=True):
            classes = element.get('class', [])
            if isinstance(classes, str):
                classes = [classes]
            all_classes.update(classes)
        
        # Detect grid system
        for pattern in self.layout_patterns['grid_system']:
            regex = re.compile(pattern, re.IGNORECASE)
            matching_classes = [cls for cls in all_classes if regex.search(cls)]
            if matching_classes:
                layout_info['grid_system'].extend(matching_classes)
        
        # Detect sections
        for pattern in self.layout_patterns['sections']:
            regex = re.compile(pattern, re.IGNORECASE)
            matching_classes = [cls for cls in all_classes if regex.search(cls)]
            if matching_classes:
                layout_info['sections'].extend(matching_classes)
        
        # Detect components
        for pattern in self.layout_patterns['components']:
            regex = re.compile(pattern, re.IGNORECASE)
            matching_classes = [cls for cls in all_classes if regex.search(cls)]
            if matching_classes:
                layout_info['components'].extend(matching_classes)
        
        # Detect CSS framework
        framework_indicators = {
            'bootstrap': ['container', 'row', 'col-', 'btn-', 'alert-'],
            'foundation': ['grid-container', 'grid-x', 'cell'],
            'material': ['mdl-', 'mdl-layout', 'mdl-card'],
            'semantic': ['ui', 'ui-', 'ui-grid', 'ui-button']
        }
        
        for framework, indicators in framework_indicators.items():
            if any(indicator in ' '.join(all_classes) for indicator in indicators):
                layout_info['css_framework'] = framework
                break
        
        # Detect responsive classes
        responsive_patterns = [r'sm-', r'md-', r'lg-', r'xl-', r'xs-', r'hidden-', r'visible-']
        for pattern in responsive_patterns:
            regex = re.compile(pattern, re.IGNORECASE)
            responsive_classes = [cls for cls in all_classes if regex.search(cls)]
            layout_info['responsive_classes'].extend(responsive_classes)
        
        # Analyze layout structure
        layout_info['layout_structure'] = self._analyze_layout_structure(soup)
        
        return layout_info
    
    def _analyze_layout_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze the overall layout structure of the page"""
        structure = {
            'header_present': bool(soup.find(['header', 'nav'])),
            'footer_present': bool(soup.find('footer')),
            'sidebar_present': bool(soup.find(class_=re.compile(r'sidebar|aside|sidebar-', re.I))),
            'main_content_areas': [],
            'navigation_elements': [],
            'form_elements': [],
            'media_elements': []
        }
        
        # Find main content areas
        main_elements = soup.find_all(['main', 'article', 'section'])
        for element in main_elements:
            classes = element.get('class', [])
            if isinstance(classes, str):
                classes = [classes]
            
            content_info = {
                'tag': element.name,
                'classes': classes,
                'id': element.get('id', ''),
                'content_length': len(element.get_text(strip=True))
            }
            structure['main_content_areas'].append(content_info)
        
        # Find navigation elements
        nav_elements = soup.find_all(['nav', 'ul', 'ol'])
        for element in nav_elements:
            if self._is_navigation_element(element):
                nav_info = {
                    'tag': element.name,
                    'classes': element.get('class', []),
                    'id': element.get('id', ''),
                    'link_count': len(element.find_all('a'))
                }
                structure['navigation_elements'].append(nav_info)
        
        # Find form elements
        forms = soup.find_all('form')
        for form in forms:
            form_info = {
                'action': form.get('action', ''),
                'method': form.get('method', 'get'),
                'field_count': len(form.find_all(['input', 'textarea', 'select'])),
                'classes': form.get('class', [])
            }
            structure['form_elements'].append(form_info)
        
        # Find media elements
        media_elements = soup.find_all(['img', 'video', 'audio'])
        for element in media_elements:
            media_info = {
                'tag': element.name,
                'src': element.get('src', ''),
                'alt': element.get('alt', ''),
                'classes': element.get('class', [])
            }
            structure['media_elements'].append(media_info)
        
        return structure
    
    def cluster_pages_by_structure(self, pages: List[Page], similarity_threshold: float = 0.8) -> Dict[str, Any]:
        """Cluster pages based on DOM structure similarity"""
        if len(pages) < 2:
            return {'clusters': [], 'similarity_matrix': [], 'recommendations': []}
        
        # Extract structural features for each page
        page_features = []
        for page in pages:
            features = self._extract_structural_features(page)
            page_features.append(features)
        
        # Calculate similarity matrix
        similarity_matrix = self._calculate_similarity_matrix(page_features)
        
        # Cluster pages using DBSCAN
        clustering = DBSCAN(eps=1-similarity_threshold, min_samples=2, metric='precomputed')
        distance_matrix = 1 - similarity_matrix
        cluster_labels = clustering.fit_predict(distance_matrix)
        
        # Group pages by cluster
        clusters = defaultdict(list)
        for i, label in enumerate(cluster_labels):
            if label >= 0:  # Skip noise points
                clusters[f"cluster_{label}"].append({
                    'url': pages[i].url,
                    'title': pages[i].title,
                    'page_type': pages[i].metadata.page_type or 'unknown',
                    'similarity_score': np.mean(similarity_matrix[i])
                })
        
        # Generate recommendations
        recommendations = self._generate_clustering_recommendations(clusters, similarity_matrix, pages)
        
        return {
            'clusters': dict(clusters),
            'similarity_matrix': similarity_matrix.tolist(),
            'recommendations': recommendations,
            'similarity_threshold': similarity_threshold,
            'total_pages': len(pages),
            'cluster_count': len(clusters)
        }
    
    def _extract_structural_features(self, page: Page) -> Dict[str, Any]:
        """Extract structural features from a page for similarity comparison"""
        soup = BeautifulSoup(page.html_content, 'html.parser')
        
        features = {
            'tag_structure': self._extract_tag_structure(soup),
            'class_patterns': self._extract_class_patterns(soup),
            'id_patterns': self._extract_id_patterns(soup),
            'component_count': len(page.components),
            'layout_signature': self._extract_layout_signature(soup),
            'content_structure': self._extract_content_structure(soup)
        }
        
        return features
    
    def _extract_tag_structure(self, soup: BeautifulSoup) -> Dict[str, int]:
        """Extract tag frequency structure"""
        tag_counts = Counter()
        for tag in soup.find_all():
            tag_counts[tag.name] += 1
        return dict(tag_counts)
    
    def _extract_class_patterns(self, soup: BeautifulSoup) -> Dict[str, int]:
        """Extract CSS class patterns"""
        class_counts = Counter()
        for element in soup.find_all(class_=True):
            classes = element.get('class', [])
            if isinstance(classes, str):
                classes = [classes]
            for cls in classes:
                # Normalize class names
                normalized = re.sub(r'[0-9]+', 'N', cls)
                class_counts[normalized] += 1
        return dict(class_counts)
    
    def _extract_id_patterns(self, soup: BeautifulSoup) -> Dict[str, int]:
        """Extract ID patterns"""
        id_counts = Counter()
        for element in soup.find_all(id=True):
            element_id = element.get('id', '')
            # Normalize ID names
            normalized = re.sub(r'[0-9]+', 'N', element_id)
            id_counts[normalized] += 1
        return dict(id_counts)
    
    def _extract_layout_signature(self, soup: BeautifulSoup) -> str:
        """Extract a layout signature based on major structural elements"""
        signature_parts = []
        
        # Check for major layout elements
        if soup.find('header'):
            signature_parts.append('H')
        if soup.find('nav'):
            signature_parts.append('N')
        if soup.find('main'):
            signature_parts.append('M')
        if soup.find('aside'):
            signature_parts.append('A')
        if soup.find('footer'):
            signature_parts.append('F')
        
        # Check for grid system
        grid_elements = soup.find_all(class_=re.compile(r'container|row|col|grid', re.I))
        if grid_elements:
            signature_parts.append('G')
        
        # Check for forms
        if soup.find('form'):
            signature_parts.append('F')
        
        return ''.join(sorted(signature_parts))
    
    def _extract_content_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract content structure information"""
        content_info = {
            'text_length': len(soup.get_text(strip=True)),
            'heading_count': len(soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])),
            'paragraph_count': len(soup.find_all('p')),
            'link_count': len(soup.find_all('a')),
            'image_count': len(soup.find_all('img')),
            'list_count': len(soup.find_all(['ul', 'ol']))
        }
        return content_info
    
    def _calculate_similarity_matrix(self, page_features: List[Dict[str, Any]]) -> np.ndarray:
        """Calculate similarity matrix between pages"""
        n_pages = len(page_features)
        similarity_matrix = np.zeros((n_pages, n_pages))
        
        for i in range(n_pages):
            for j in range(i+1, n_pages):
                similarity = self._calculate_page_similarity(page_features[i], page_features[j])
                similarity_matrix[i][j] = similarity
                similarity_matrix[j][i] = similarity
        
        # Set diagonal to 1.0
        np.fill_diagonal(similarity_matrix, 1.0)
        
        return similarity_matrix
    
    def _calculate_page_similarity(self, features1: Dict[str, Any], features2: Dict[str, Any]) -> float:
        """Calculate similarity between two pages based on their features"""
        similarities = []
        
        # Tag structure similarity
        tag_sim = self._calculate_dict_similarity(features1['tag_structure'], features2['tag_structure'])
        similarities.append(tag_sim * 0.3)  # Weight: 30%
        
        # Class pattern similarity
        class_sim = self._calculate_dict_similarity(features1['class_patterns'], features2['class_patterns'])
        similarities.append(class_sim * 0.25)  # Weight: 25%
        
        # Layout signature similarity
        layout_sim = 1.0 if features1['layout_signature'] == features2['layout_signature'] else 0.0
        similarities.append(layout_sim * 0.2)  # Weight: 20%
        
        # Component count similarity
        comp_sim = 1.0 - abs(features1['component_count'] - features2['component_count']) / max(features1['component_count'], features2['component_count'], 1)
        similarities.append(comp_sim * 0.15)  # Weight: 15%
        
        # Content structure similarity
        content_sim = self._calculate_content_similarity(features1['content_structure'], features2['content_structure'])
        similarities.append(content_sim * 0.1)  # Weight: 10%
        
        return sum(similarities)
    
    def _calculate_dict_similarity(self, dict1: Dict[str, int], dict2: Dict[str, int]) -> float:
        """Calculate similarity between two dictionaries based on key overlap and value similarity"""
        if not dict1 and not dict2:
            return 1.0
        if not dict1 or not dict2:
            return 0.0
        
        # Get all unique keys
        all_keys = set(dict1.keys()) | set(dict2.keys())
        
        # Calculate Jaccard similarity for keys
        key_similarity = len(set(dict1.keys()) & set(dict2.keys())) / len(all_keys)
        
        # Calculate value similarity for common keys
        common_keys = set(dict1.keys()) & set(dict2.keys())
        if not common_keys:
            return key_similarity * 0.5
        
        value_similarities = []
        for key in common_keys:
            val1, val2 = dict1[key], dict2[key]
            max_val = max(val1, val2)
            if max_val == 0:
                value_similarities.append(1.0)
            else:
                value_similarities.append(1.0 - abs(val1 - val2) / max_val)
        
        value_similarity = np.mean(value_similarities)
        
        # Combine key and value similarity
        return key_similarity * 0.3 + value_similarity * 0.7
    
    def _calculate_content_similarity(self, content1: Dict[str, Any], content2: Dict[str, Any]) -> float:
        """Calculate similarity between content structures"""
        similarities = []
        
        for key in content1.keys():
            if key in content2:
                val1, val2 = content1[key], content2[key]
                if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                    max_val = max(val1, val2)
                    if max_val == 0:
                        similarities.append(1.0)
                    else:
                        similarities.append(1.0 - abs(val1 - val2) / max_val)
                else:
                    similarities.append(1.0 if val1 == val2 else 0.0)
            else:
                similarities.append(0.0)
        
        return np.mean(similarities) if similarities else 0.0
    
    def _generate_clustering_recommendations(self, clusters: Dict, similarity_matrix: np.ndarray, pages: List[Page]) -> List[Dict[str, Any]]:
        """Generate recommendations based on clustering results"""
        recommendations = []
        
        for cluster_name, cluster_pages in clusters.items():
            if len(cluster_pages) > 1:
                # Calculate average similarity within cluster
                cluster_urls = [page['url'] for page in cluster_pages]
                cluster_indices = [i for i, page in enumerate(pages) if page.url in cluster_urls]
                
                if len(cluster_indices) > 1:
                    cluster_similarities = []
                    for i in cluster_indices:
                        for j in cluster_indices:
                            if i != j:
                                cluster_similarities.append(similarity_matrix[i][j])
                    
                    avg_similarity = np.mean(cluster_similarities) if cluster_similarities else 0.0
                    
                    # Determine page types in cluster
                    page_types = Counter(page['page_type'] for page in cluster_pages)
                    dominant_type = page_types.most_common(1)[0][0] if page_types else 'unknown'
                    
                    recommendation = {
                        'cluster': cluster_name,
                        'page_count': len(cluster_pages),
                        'average_similarity': round(avg_similarity, 3),
                        'dominant_page_type': dominant_type,
                        'recommendation': f"Create a single template for {dominant_type} pages with {len(cluster_pages)} variations",
                        'template_suggestions': self._generate_template_suggestions(cluster_pages, dominant_type)
                    }
                    
                    recommendations.append(recommendation)
        
        return recommendations
    
    def _generate_template_suggestions(self, cluster_pages: List[Dict], page_type: str) -> List[str]:
        """Generate template suggestions for a cluster"""
        suggestions = []
        
        if page_type == 'homepage':
            suggestions.extend([
                "Use a hero section with dynamic content",
                "Implement a grid-based content layout",
                "Add navigation and footer components"
            ])
        elif page_type == 'blog_post':
            suggestions.extend([
                "Create a content template with title, author, and body",
                "Add related posts section",
                "Include social sharing components"
            ])
        elif page_type == 'product_page':
            suggestions.extend([
                "Use a product image gallery component",
                "Add product details and specifications",
                "Include related products section"
            ])
        else:
            suggestions.extend([
                "Create a flexible content template",
                "Add navigation and breadcrumb components",
                "Include footer and social media links"
            ])
        
        return suggestions
    
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
