"""
Comprehensive analysis engine for Recrafter
"""

import json
import os
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from collections import defaultdict, Counter
from bs4 import BeautifulSoup

from .analyzer import ContentAnalyzer
from .storage import StorageManager
from .models import Page, Component, ContentModel
from .config import Config


class AnalysisEngine:
    """Comprehensive analysis engine for crawled website data"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger("recrafter.analysis_engine")
        self.analyzer = ContentAnalyzer(config.analysis)
        self.storage = StorageManager(config.storage)
    
    async def run_comprehensive_analysis(self, input_dir: str, output_file: Optional[str] = None) -> Dict[str, Any]:
        """Run comprehensive analysis on crawled data"""
        try:
            self.logger.info(f"Starting comprehensive analysis of {input_dir}")
            
            # Load crawled data
            crawled_data = self.storage.load_crawled_data()
            if not crawled_data['pages']:
                raise ValueError("No pages found in crawled data")
            
            # Convert to Page objects for analysis
            pages = self._convert_to_page_objects(crawled_data['pages'])
            
            # Run analysis
            analysis_results = {
                'analysis_timestamp': datetime.now().isoformat(),
                'input_directory': input_dir,
                'total_pages': len(pages),
                'total_assets': len(crawled_data['assets']),
                'page_clustering': await self._analyze_page_clustering(pages),
                'component_analysis': await self._analyze_components(pages),
                'content_models': await self._generate_content_models(pages),
                'layout_analysis': await self._analyze_layouts(pages),
                'migration_recommendations': await self._generate_migration_recommendations(pages, crawled_data),
                'asset_inventory': self._create_asset_inventory(crawled_data['assets']),
                'site_structure': self._analyze_site_structure(pages)
            }
            
            # Save analysis results
            if output_file:
                self._save_analysis_results(analysis_results, output_file)
            
            self.logger.info("Comprehensive analysis completed successfully")
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"Analysis failed: {e}")
            raise
    
    def _convert_to_page_objects(self, page_data: List[Dict[str, Any]]) -> List[Page]:
        """Convert page data dictionaries to Page objects"""
        pages = []
        
        for data in page_data:
            try:
                # Create PageMetadata
                from .models import PageMetadata
                metadata = PageMetadata(
                    title=data.get('title', ''),
                    description=data.get('metadata', {}).get('description', ''),
                    keywords=data.get('metadata', {}).get('keywords', []),
                    page_type=data.get('metadata', {}).get('page_type', 'general_page')
                )
                
                # Create Page object
                page = Page(
                    url=data['url'],
                    local_path=data['local_path'],
                    depth=data['depth'],
                    title=data['title'],
                    html_content=data['html_content'],
                    metadata=metadata,
                    size=data['size'],
                    status_code=data['status_code'],
                    content_type=data['content_type'],
                    crawled_at=datetime.fromisoformat(data['crawled_at'])
                )
                
                pages.append(page)
                
            except Exception as e:
                self.logger.warning(f"Failed to convert page data: {e}")
                continue
        
        return pages
    
    async def _analyze_page_clustering(self, pages: List[Page]) -> Dict[str, Any]:
        """Analyze page clustering based on structure similarity"""
        try:
            self.logger.info("Analyzing page clustering...")
            
            # Run clustering analysis
            clustering_results = self.analyzer.cluster_pages_by_structure(
                pages, 
                similarity_threshold=0.8
            )
            
            # Add additional insights
            clustering_results['page_type_distribution'] = self._get_page_type_distribution(pages)
            clustering_results['depth_distribution'] = self._get_depth_distribution(pages)
            
            return clustering_results
            
        except Exception as e:
            self.logger.error(f"Page clustering analysis failed: {e}")
            return {'error': str(e)}
    
    async def _analyze_components(self, pages: List[Page]) -> Dict[str, Any]:
        """Analyze components across all pages"""
        try:
            self.logger.info("Analyzing components...")
            
            # Analyze each page
            for page in pages:
                await self.analyzer.analyze_page(page)
            
            # Aggregate component information
            all_components = []
            component_frequency = Counter()
            component_by_page_type = defaultdict(list)
            
            for page in pages:
                for component in page.components:
                    # Create component signature
                    component_sig = self._create_component_signature(component)
                    component_frequency[component_sig] += 1
                    
                    # Add page context
                    component_with_context = {
                        'selector': component.selector,
                        'tag_name': component.tag_name,
                        'classes': component.classes,
                        'attributes': component.attributes,
                        'content_sample': component.content_sample,
                        'page_url': page.url,
                        'page_type': page.metadata.page_type or 'unknown',
                        'frequency': component_frequency[component_sig]
                    }
                    
                    all_components.append(component_with_context)
                    component_by_page_type[page.metadata.page_type or 'unknown'].append(component_with_context)
            
            # Find reusable components
            reusable_components = [
                comp for comp in all_components 
                if comp['frequency'] > 1
            ]
            
            # Group by frequency
            frequency_groups = defaultdict(list)
            for comp in reusable_components:
                freq = comp['frequency']
                if freq >= 5:
                    freq_group = 'high'
                elif freq >= 3:
                    freq_group = 'medium'
                else:
                    freq_group = 'low'
                frequency_groups[freq_group].append(comp)
            
            return {
                'total_components': len(all_components),
                'unique_components': len(component_frequency),
                'reusable_components': len(reusable_components),
                'frequency_distribution': dict(component_frequency.most_common(20)),
                'frequency_groups': dict(frequency_groups),
                'components_by_page_type': dict(component_by_page_type),
                'top_components': component_frequency.most_common(10)
            }
            
        except Exception as e:
            self.logger.error(f"Component analysis failed: {e}")
            return {'error': str(e)}
    
    async def _generate_content_models(self, pages: List[Page]) -> List[Dict[str, Any]]:
        """Generate content models for different page types"""
        try:
            self.logger.info("Generating content models...")
            
            # Generate models using analyzer
            content_models = self.analyzer.generate_content_models(pages)
            
            # Convert to dictionaries for serialization
            model_dicts = []
            for model in content_models:
                # Check if model is already a dict or a ContentModel object
                if isinstance(model, dict):
                    self.logger.warning(f"Model is already a dict: {model}")
                    model_dicts.append(model)
                else:
                    try:
                        model_dict = {
                            'name': model.name,
                            'page_type': model.page_type,
                            'description': model.description,
                            'fields': model.fields,  # Fields are already in the correct format
                            'sample_pages': model.sample_pages
                        }
                        model_dicts.append(model_dict)
                    except AttributeError as attr_error:
                        self.logger.error(f"Model object missing attribute: {attr_error}")
                        self.logger.error(f"Model object: {model}")
                        # Try to convert using to_dict method if available
                        if hasattr(model, 'to_dict'):
                            model_dicts.append(model.to_dict())
                        else:
                            # Fallback: create a basic dict
                            model_dicts.append({
                                'name': str(model),
                                'page_type': 'unknown',
                                'description': 'Error processing model',
                                'fields': [],
                                'sample_pages': []
                            })
            
            return model_dicts
            
        except Exception as e:
            self.logger.error(f"Content model generation failed: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    async def _analyze_layouts(self, pages: List[Page]) -> Dict[str, Any]:
        """Analyze layout patterns across pages"""
        try:
            self.logger.info("Analyzing layout patterns...")
            
            # Analyze layouts for each page
            for page in pages:
                if not page.layout_info:
                    soup = BeautifulSoup(page.html_content, 'html.parser')
                    page.layout_info = self.analyzer.extract_layout_patterns(soup)
            
            # Aggregate layout information
            css_frameworks = Counter()
            grid_systems = Counter()
            responsive_patterns = Counter()
            layout_structures = defaultdict(int)
            
            for page in pages:
                if page.layout_info:
                    # CSS frameworks
                    if page.layout_info.get('css_framework'):
                        css_frameworks[page.layout_info['css_framework']] += 1
                    
                    # Grid systems
                    for grid_class in page.layout_info.get('grid_system', []):
                        grid_systems[grid_class] += 1
                    
                    # Responsive patterns
                    for resp_class in page.layout_info.get('responsive_classes', []):
                        responsive_patterns[resp_class] += 1
                    
                    # Layout structures
                    layout_sig = page.layout_info.get('layout_signature', '')
                    if layout_sig:
                        layout_structures[layout_sig] += 1
            
            return {
                'css_frameworks': dict(css_frameworks),
                'grid_systems': dict(grid_systems.most_common(10)),
                'responsive_patterns': dict(responsive_patterns.most_common(10)),
                'layout_structures': dict(layout_structures),
                'layout_analysis': {
                    'pages_with_header': sum(1 for p in pages if p.layout_info and p.layout_info.get('layout_structure', {}).get('header_present')),
                    'pages_with_footer': sum(1 for p in pages if p.layout_info and p.layout_info.get('layout_structure', {}).get('footer_present')),
                    'pages_with_sidebar': sum(1 for p in pages if p.layout_info and p.layout_info.get('layout_structure', {}).get('sidebar_present')),
                    'pages_with_forms': sum(1 for p in pages if p.layout_info and p.layout_info.get('layout_structure', {}).get('form_elements')),
                    'pages_with_navigation': sum(1 for p in pages if p.layout_info and p.layout_info.get('layout_structure', {}).get('navigation_elements'))
                }
            }
            
        except Exception as e:
            self.logger.error(f"Layout analysis failed: {e}")
            return {'error': str(e)}
    
    async def _generate_migration_recommendations(self, pages: List[Page], crawled_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate migration recommendations for Crafter CMS"""
        try:
            self.logger.info("Generating migration recommendations...")
            
            recommendations = []
            
            # Template recommendations based on clustering
            clustering_results = await self._analyze_page_clustering(pages)
            if 'recommendations' in clustering_results:
                for rec in clustering_results['recommendations']:
                    recommendations.append({
                        'type': 'template_optimization',
                        'priority': 'high' if rec['average_similarity'] > 0.9 else 'medium',
                        'title': f"Template for {rec['dominant_page_type']} pages",
                        'description': rec['recommendation'],
                        'details': rec,
                        'estimated_effort': 'medium' if rec['page_count'] > 5 else 'low'
                    })
            
            # Component recommendations
            component_results = await self._analyze_components(pages)
            if 'frequency_groups' in component_results:
                high_freq_components = component_results['frequency_groups'].get('high', [])
                if high_freq_components:
                    recommendations.append({
                        'type': 'component_priority',
                        'priority': 'high',
                        'title': "High-frequency components",
                        'description': f"Prioritize {len(high_freq_components)} high-frequency components for Crafter Studio",
                        'details': {
                            'components': high_freq_components[:5],
                            'total_occurrences': sum(comp['frequency'] for comp in high_freq_components)
                        },
                        'estimated_effort': 'medium'
                    })
            
            # Layout recommendations
            layout_results = await self._analyze_layouts(pages)
            if 'css_frameworks' in layout_results:
                frameworks = layout_results['css_frameworks']
                if frameworks:
                    dominant_framework = max(frameworks.items(), key=lambda x: x[1])[0]
                    recommendations.append({
                        'type': 'framework_migration',
                        'priority': 'medium',
                        'title': f"CSS Framework: {dominant_framework}",
                        'description': f"Site uses {dominant_framework} - consider Crafter's built-in components or custom CSS",
                        'details': {
                            'framework': dominant_framework,
                            'usage_percentage': round(frameworks[dominant_framework] / len(pages) * 100, 1)
                        },
                        'estimated_effort': 'high' if dominant_framework != 'bootstrap' else 'medium'
                    })
            
            # Asset recommendations
            asset_count = len(crawled_data['assets'])
            if asset_count > 100:
                recommendations.append({
                    'type': 'asset_management',
                    'priority': 'medium',
                    'title': "Asset Management",
                    'description': f"Large number of assets ({asset_count}) - implement proper asset organization in Crafter",
                    'details': {
                        'total_assets': asset_count,
                        'asset_types': Counter(asset['asset_type'] for asset in crawled_data['assets'])
                    },
                    'estimated_effort': 'medium'
                })
            
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Migration recommendations generation failed: {e}")
            return []
    
    def _create_asset_inventory(self, assets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create comprehensive asset inventory"""
        try:
            asset_types = Counter(asset['asset_type'] for asset in assets)
            extensions = Counter(asset['extension'] for asset in assets)
            
            # Group assets by type
            assets_by_type = defaultdict(list)
            for asset in assets:
                assets_by_type[asset['asset_type']].append({
                    'filename': asset['filename'],
                    'size': asset['size'],
                    'extension': asset['extension'],
                    'local_path': asset['local_path']
                })
            
            # Calculate total sizes
            total_size = sum(asset['size'] for asset in assets)
            size_by_type = defaultdict(int)
            for asset in assets:
                size_by_type[asset['asset_type']] += asset['size']
            
            return {
                'total_assets': len(assets),
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'asset_types': dict(asset_types),
                'file_extensions': dict(extensions),
                'size_by_type': dict(size_by_type),
                'assets_by_type': dict(assets_by_type)
            }
            
        except Exception as e:
            self.logger.error(f"Asset inventory creation failed: {e}")
            return {}
    
    def _analyze_site_structure(self, pages: List[Page]) -> Dict[str, Any]:
        """Analyze overall site structure"""
        try:
            # Depth analysis
            depth_distribution = Counter(page.depth for page in pages)
            
            # URL pattern analysis
            url_patterns = []
            for page in pages:
                path = page.url
                if path.startswith('/'):
                    path = path[1:]
                if path:
                    url_patterns.append(path)
            
            # Page type distribution
            page_type_dist = Counter(page.metadata.page_type or 'unknown' for page in pages)
            
            # Internal link analysis
            total_links = sum(len(page.links) for page in pages)
            internal_links = sum(1 for page in pages for link in page.links if link.is_internal)
            
            return {
                'depth_distribution': dict(depth_distribution),
                'url_patterns': url_patterns[:20],  # Top 20 patterns
                'page_type_distribution': dict(page_type_dist),
                'link_analysis': {
                    'total_links': total_links,
                    'internal_links': internal_links,
                    'external_links': total_links - internal_links,
                    'avg_links_per_page': round(total_links / len(pages), 2) if pages else 0
                },
                'site_complexity': {
                    'complexity_score': self._calculate_complexity_score(pages),
                    'navigation_depth': max(depth_distribution.keys()) if depth_distribution else 0,
                    'content_variety': len(page_type_dist)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Site structure analysis failed: {e}")
            return {}
    
    def _get_page_type_distribution(self, pages: List[Page]) -> Dict[str, int]:
        """Get distribution of page types"""
        return Counter(page.metadata.page_type or 'unknown' for page in pages)
    
    def _get_depth_distribution(self, pages: List[Page]) -> Dict[int, int]:
        """Get distribution of page depths"""
        return Counter(page.depth for page in pages)
    
    def _create_component_signature(self, component: Component) -> str:
        """Create a unique signature for a component"""
        signature_parts = [
            component.tag_name,
            '|'.join(sorted(component.classes)),
            '|'.join(f"{k}={v}" for k, v in sorted(component.attributes.items()))
        ]
        return '::'.join(signature_parts)
    
    def _calculate_complexity_score(self, pages: List[Page]) -> float:
        """Calculate a complexity score for the site"""
        if not pages:
            return 0.0
        
        # Factors: depth, variety, components, links
        max_depth = max(page.depth for page in pages)
        page_types = len(set(page.metadata.page_type or 'unknown' for page in pages))
        avg_components = sum(len(page.components) for page in pages) / len(pages)
        avg_links = sum(len(page.links) for page in pages) / len(pages)
        
        # Normalize and weight
        depth_score = min(max_depth / 5.0, 1.0)  # Normalize to 0-1
        type_score = min(page_types / 10.0, 1.0)
        component_score = min(avg_components / 20.0, 1.0)
        link_score = min(avg_links / 50.0, 1.0)
        
        # Weighted average
        complexity = (
            depth_score * 0.3 +
            type_score * 0.25 +
            component_score * 0.25 +
            link_score * 0.2
        )
        
        return round(complexity, 3)
    
    def _save_analysis_results(self, results: Dict[str, Any], output_file: str) -> None:
        """Save analysis results to file"""
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            
            self.logger.info(f"Analysis results saved to {output_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save analysis results: {e}")
            raise
