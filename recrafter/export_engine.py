"""
Export engine for Recrafter - generates Crafter CMS compatible outputs
"""

import json
import yaml
import os
import shutil
import zipfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from collections import defaultdict

from .models import Page, Component, ContentModel
from .config import Config


class ExportEngine:
    """Export engine for generating Crafter CMS compatible outputs"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger("recrafter.export_engine")
    
    async def export_data(self, input_dir: str, output_dir: str, format: str = 'cms') -> str:
        """Export crawled data in the specified format"""
        try:
            self.logger.info(f"Exporting data from {input_dir} to {output_dir} in {format} format")
            
            if format == 'cms':
                return await self._export_for_cms(input_dir, output_dir)
            elif format == 'json':
                return await self._export_as_json(input_dir, output_dir)
            elif format == 'yaml':
                return await self._export_as_yaml(input_dir, output_dir)
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            self.logger.error(f"Export failed: {e}")
            raise
    
    async def _export_for_cms(self, input_dir: str, output_dir: str) -> str:
        """Export data in Crafter CMS compatible format"""
        try:
            # Create output directory structure
            cms_output = Path(output_dir)
            cms_output.mkdir(parents=True, exist_ok=True)
            
            # Create CMS directory structure
            cms_dirs = [
                'content-types',
                'templates',
                'components',
                'assets',
                'navigation',
                'workflows',
                'scripts'
            ]
            
            for dir_name in cms_dirs:
                (cms_output / dir_name).mkdir(exist_ok=True)
            
            # Export content types
            await self._export_content_types(input_dir, cms_output / 'content-types')
            
            # Export templates
            await self._export_templates(input_dir, cms_output / 'templates')
            
            # Export components
            await self._export_components(input_dir, cms_output / 'components')
            
            # Export assets
            await self._export_assets(input_dir, cms_output / 'assets')
            
            # Export navigation
            await self._export_navigation(input_dir, cms_output / 'navigation')
            
            # Export workflows
            await self._export_workflows(cms_output / 'workflows')
            
            # Export scripts
            await self._export_scripts(cms_output / 'scripts')
            
            # Create README and documentation
            await self._create_cms_documentation(cms_output, input_dir)
            
            # Create zip file
            zip_path = await self._create_cms_package(cms_output)
            
            self.logger.info(f"CMS export completed: {zip_path}")
            return zip_path
            
        except Exception as e:
            self.logger.error(f"CMS export failed: {e}")
            raise
    
    async def _export_content_types(self, input_dir: str, output_dir: Path) -> None:
        """Export content types as Crafter CMS model definitions"""
        try:
            # Load analysis results if available
            analysis_file = Path(input_dir) / 'metadata' / 'analysis_results.json'
            if analysis_file.exists():
                with open(analysis_file, 'r', encoding='utf-8') as f:
                    analysis_data = json.load(f)
                
                content_models = analysis_data.get('content_models', [])
                
                for model in content_models:
                    model_file = output_dir / f"{model['page_type']}_model.xml"
                    
                    # Generate Crafter CMS content model XML
                    xml_content = self._generate_content_model_xml(model)
                    
                    with open(model_file, 'w', encoding='utf-8') as f:
                        f.write(xml_content)
                    
                    self.logger.debug(f"Exported content model: {model_file}")
            else:
                # Create default content models
                default_models = [
                    {
                        'name': 'Page Model',
                        'page_type': 'general_page',
                        'description': 'General page content model',
                        'fields': [
                            {'name': 'title', 'type': 'text', 'required': True},
                            {'name': 'content', 'type': 'rich_text', 'required': False},
                            {'name': 'metadata', 'type': 'metadata_group', 'required': False}
                        ]
                    }
                ]
                
                for model in default_models:
                    model_file = output_dir / f"{model['page_type']}_model.xml"
                    xml_content = self._generate_content_model_xml(model)
                    
                    with open(model_file, 'w', encoding='utf-8') as f:
                        f.write(xml_content)
                    
        except Exception as e:
            self.logger.error(f"Content type export failed: {e}")
    
    def _generate_content_model_xml(self, model: Dict[str, Any]) -> str:
        """Generate Crafter CMS content model XML"""
        xml_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<content-type>
    <display-name>{model['name']}</display-name>
    <description>{model.get('description', '')}</description>
    <model-id>{model['page_type']}</model-id>
    <model-name>{model['page_type']}</model-name>
    <version>1</version>
    <form>
        <field-group>
            <title>Content</title>
            <fields>"""
        
        for field in model.get('fields', []):
            field_type = self._map_field_type_to_crafter(field['type'])
            required = 'true' if field.get('required', False) else 'false'
            
            xml_template += f"""
                <field>
                    <name>{field['name']}</name>
                    <type>{field_type}</type>
                    <required>{required}</required>
                    <label>{field['name'].replace('_', ' ').title()}</label>
                    <help>{field.get('description', '')}</help>
                </field>"""
        
        xml_template += """
            </fields>
        </field-group>
    </form>
</content-type>"""
        
        return xml_template
    
    def _map_field_type_to_crafter(self, field_type: str) -> str:
        """Map field types to Crafter CMS field types"""
        type_mapping = {
            'text': 'input-text',
            'rich_text': 'rich-text',
            'number': 'input-number',
            'date': 'input-date',
            'image': 'input-image',
            'image_list': 'input-image',
            'text_list': 'input-text',
            'content_reference': 'input-content',
            'metadata_group': 'input-text',
            'form_field_list': 'input-text',
            'key_value_list': 'input-text'
        }
        
        return type_mapping.get(field_type, 'input-text')
    
    async def _export_templates(self, input_dir: str, output_dir: Path) -> None:
        """Export Freemarker templates based on page analysis"""
        try:
            # Load analysis results
            analysis_file = Path(input_dir) / 'metadata' / 'analysis_results.json'
            if analysis_file.exists():
                with open(analysis_file, 'r', encoding='utf-8') as f:
                    analysis_data = json.load(f)
                
                # Generate templates based on clustering
                clustering = analysis_data.get('page_clustering', {})
                clusters = clustering.get('clusters', {})
                
                for cluster_name, cluster_pages in clusters.items():
                    if cluster_pages:
                        # Get dominant page type
                        page_types = [page['page_type'] for page in cluster_pages]
                        dominant_type = max(set(page_types), key=page_types.count)
                        
                        # Generate template
                        template_file = output_dir / f"{dominant_type}_template.ftl"
                        template_content = self._generate_freemarker_template(dominant_type, cluster_pages)
                        
                        with open(template_file, 'w', encoding='utf-8') as f:
                            f.write(template_content)
                        
                        self.logger.debug(f"Exported template: {template_file}")
            else:
                # Create default templates
                default_templates = [
                    ('homepage', self._generate_homepage_template()),
                    ('general_page', self._generate_general_template()),
                    ('blog_post', self._generate_blog_template())
                ]
                
                for template_name, template_content in default_templates:
                    template_file = output_dir / f"{template_name}_template.ftl"
                    with open(template_file, 'w', encoding='utf-8') as f:
                        f.write(template_content)
                    
        except Exception as e:
            self.logger.error(f"Template export failed: {e}")
    
    def _generate_freemarker_template(self, page_type: str, cluster_pages: List[Dict]) -> str:
        """Generate Freemarker template for a page type"""
        if page_type == 'homepage':
            return self._generate_homepage_template()
        elif page_type == 'blog_post':
            return self._generate_blog_template()
        else:
            return self._generate_general_template()
    
    def _generate_homepage_template(self) -> str:
        """Generate homepage Freemarker template"""
        return """<#include "header.ftl">

<main class="homepage">
    <section class="hero">
        <div class="container">
            <h1>${content.title!''}</h1>
            <#if content.hero_content??>
                <div class="hero-content">
                    ${content.hero_content!''}
                </div>
            </#if>
        </div>
    </section>
    
    <#if content.featured_content??>
        <section class="featured-content">
            <div class="container">
                <h2>Featured Content</h2>
                <div class="content-grid">
                    ${content.featured_content!''}
                </div>
            </div>
        </section>
    </#if>
</main>

<#include "footer.ftl">"""
    
    def _generate_blog_template(self) -> str:
        """Generate blog post Freemarker template"""
        return """<#include "header.ftl">

<main class="blog-post">
    <article>
        <header class="post-header">
            <div class="container">
                <h1>${content.title!''}</h1>
                <#if content.author??>
                    <p class="author">By ${content.author!''}</p>
                </#if>
                <#if content.publish_date??>
                    <p class="date">${content.publish_date!''}</p>
                </#if>
            </div>
        </header>
        
        <div class="post-content">
            <div class="container">
                ${content.content!''}
            </div>
        </div>
        
        <#if content.tags??>
            <footer class="post-footer">
                <div class="container">
                    <div class="tags">
                        <#list content.tags as tag>
                            <span class="tag">${tag!''}</span>
                        </#list>
                    </div>
                </div>
            </footer>
        </#if>
    </article>
</main>

<#include "footer.ftl">"""
    
    def _generate_general_template(self) -> str:
        """Generate general page Freemarker template"""
        return """<#include "header.ftl">

<main class="general-page">
    <div class="container">
        <header class="page-header">
            <h1>${content.title!''}</h1>
        </header>
        
        <div class="page-content">
            ${content.content!''}
        </div>
    </div>
</main>

<#include "footer.ftl">"""
    
    async def _export_components(self, input_dir: str, output_dir: Path) -> None:
        """Export reusable components"""
        try:
            # Load analysis results
            analysis_file = Path(input_dir) / 'metadata' / 'analysis_results.json'
            if analysis_file.exists():
                with open(analysis_file, 'r', encoding='utf-8') as f:
                    analysis_data = json.load(f)
                
                component_analysis = analysis_data.get('component_analysis', {})
                frequency_groups = component_analysis.get('frequency_groups', {})
                
                # Export high-frequency components
                high_freq_components = frequency_groups.get('high', [])
                
                for i, component in enumerate(high_freq_components[:10]):  # Top 10
                    component_file = output_dir / f"component_{i+1}_{component['tag_name']}.ftl"
                    
                    component_content = self._generate_component_template(component)
                    
                    with open(component_file, 'w', encoding='utf-8') as f:
                        f.write(component_content)
                    
                    self.logger.debug(f"Exported component: {component_file}")
            else:
                # Create default components
                default_components = [
                    ('header', self._generate_header_component()),
                    ('footer', self._generate_footer_component()),
                    ('navigation', self._generate_navigation_component())
                ]
                
                for comp_name, comp_content in default_components:
                    component_file = output_dir / f"{comp_name}_component.ftl"
                    with open(component_file, 'w', encoding='utf-8') as f:
                        f.write(comp_content)
                    
        except Exception as e:
            self.logger.error(f"Component export failed: {e}")
    
    def _generate_component_template(self, component: Dict[str, Any]) -> str:
        """Generate Freemarker component template"""
        tag_name = component['tag_name']
        classes = ' '.join(component['classes']) if component['classes'] else ''
        
        template = f"""<{tag_name} class="{classes}">
    <#-- Component: {component['selector']} -->
    <#-- Original content sample: {component.get('content_sample', 'N/A')} -->
    
    <#-- Add your component logic here -->
    <#-- This component was found on {component.get('frequency', 0)} pages -->
    
</{tag_name}>"""
        
        return template
    
    def _generate_header_component(self) -> str:
        """Generate header component template"""
        return """<header class="site-header">
    <div class="container">
        <div class="header-content">
            <div class="logo">
                <a href="/">
                    <img src="/assets/images/logo.png" alt="Site Logo">
                </a>
            </div>
            
            <nav class="main-navigation">
                <#include "navigation.ftl">
            </nav>
        </div>
    </div>
</header>"""
    
    def _generate_footer_component(self) -> str:
        """Generate footer component template"""
        return """<footer class="site-footer">
    <div class="container">
        <div class="footer-content">
            <div class="footer-section">
                <h3>About Us</h3>
                <p>Your company description here.</p>
            </div>
            
            <div class="footer-section">
                <h3>Contact</h3>
                <p>Email: info@example.com</p>
                <p>Phone: (555) 123-4567</p>
            </div>
            
            <div class="footer-section">
                <h3>Follow Us</h3>
                <div class="social-links">
                    <a href="#" class="social-link">Facebook</a>
                    <a href="#" class="social-link">Twitter</a>
                    <a href="#" class="social-link">LinkedIn</a>
                </div>
            </div>
        </div>
        
        <div class="footer-bottom">
            <p>&copy; ${.now?string("yyyy")} Your Company. All rights reserved.</p>
        </div>
    </div>
</footer>"""
    
    def _generate_navigation_component(self) -> str:
        """Generate navigation component template"""
        return """<ul class="main-menu">
    <li><a href="/">Home</a></li>
    <li><a href="/about">About</a></li>
    <li><a href="/services">Services</a></li>
    <li><a href="/contact">Contact</a></li>
</ul>"""
    
    async def _export_assets(self, input_dir: str, output_dir: Path) -> None:
        """Export assets with proper organization"""
        try:
            source_assets = Path(input_dir) / 'assets'
            if source_assets.exists():
                # Copy assets maintaining structure
                for asset_type_dir in ['images', 'css', 'js', 'fonts', 'documents']:
                    source_type_dir = source_assets / asset_type_dir
                    target_type_dir = output_dir / asset_type_dir
                    
                    if source_type_dir.exists():
                        target_type_dir.mkdir(exist_ok=True)
                        
                        for asset_file in source_type_dir.rglob('*'):
                            if asset_file.is_file():
                                relative_path = asset_file.relative_to(source_type_dir)
                                target_file = target_type_dir / relative_path
                                
                                # Ensure target directory exists
                                target_file.parent.mkdir(parents=True, exist_ok=True)
                                
                                # Copy file
                                shutil.copy2(asset_file, target_file)
                                self.logger.debug(f"Copied asset: {asset_file} -> {target_file}")
                
                self.logger.info("Assets exported successfully")
            else:
                self.logger.warning("No assets directory found")
                
        except Exception as e:
            self.logger.error(f"Asset export failed: {e}")
    
    async def _export_navigation(self, input_dir: str, output_dir: Path) -> None:
        """Export navigation structure"""
        try:
            # Load analysis results
            analysis_file = Path(input_dir) / 'metadata' / 'analysis_results.json'
            if analysis_file.exists():
                with open(analysis_file, 'r', encoding='utf-8') as f:
                    analysis_data = json.load(f)
                
                site_structure = analysis_data.get('site_structure', {})
                depth_distribution = site_structure.get('depth_distribution', {})
                page_type_distribution = site_structure.get('page_type_distribution', {})
                
                # Create navigation configuration
                navigation_config = {
                    'site_structure': {
                        'max_depth': max(depth_distribution.keys()) if depth_distribution else 0,
                        'page_types': page_type_distribution,
                        'navigation_elements': site_structure.get('link_analysis', {})
                    },
                    'recommended_navigation': self._generate_navigation_structure(site_structure)
                }
                
                # Save navigation config
                nav_file = output_dir / 'navigation_config.json'
                with open(nav_file, 'w', encoding='utf-8') as f:
                    json.dump(navigation_config, f, indent=2, ensure_ascii=False)
                
                # Create navigation template
                nav_template_file = output_dir / 'navigation_structure.ftl'
                nav_template = self._generate_navigation_template(navigation_config)
                
                with open(nav_template_file, 'w', encoding='utf-8') as f:
                    f.write(nav_template)
                
                self.logger.info("Navigation exported successfully")
                
        except Exception as e:
            self.logger.error(f"Navigation export failed: {e}")
    
    def _generate_navigation_structure(self, site_structure: Dict[str, Any]) -> Dict[str, Any]:
        """Generate recommended navigation structure"""
        return {
            'primary_navigation': [
                {'label': 'Home', 'url': '/', 'type': 'homepage'},
                {'label': 'About', 'url': '/about', 'type': 'information_page'},
                {'label': 'Services', 'url': '/services', 'type': 'category_page'},
                {'label': 'Contact', 'url': '/contact', 'type': 'form_page'}
            ],
            'secondary_navigation': [
                {'label': 'Blog', 'url': '/blog', 'type': 'blog_post'},
                {'label': 'Resources', 'url': '/resources', 'type': 'category_page'}
            ],
            'footer_navigation': [
                {'label': 'Privacy Policy', 'url': '/privacy', 'type': 'information_page'},
                {'label': 'Terms of Service', 'url': '/terms', 'type': 'information_page'}
            ]
        }
    
    def _generate_navigation_template(self, navigation_config: Dict[str, Any]) -> str:
        """Generate navigation template"""
        return """<#-- Navigation Structure Template -->
<#-- Generated from site analysis -->

<#macro renderNavigation items>
    <ul class="navigation-menu">
        <#list items as item>
            <li class="nav-item nav-item-${item.type!''}">
                <a href="${item.url!''}" class="nav-link">
                    ${item.label!''}
                </a>
            </li>
        </#list>
    </ul>
</#macro>

<#-- Primary Navigation -->
<nav class="primary-navigation">
    <@renderNavigation navigation_config.primary_navigation />
</nav>

<#-- Secondary Navigation -->
<nav class="secondary-navigation">
    <@renderNavigation navigation_config.secondary_navigation />
</nav>

<#-- Footer Navigation -->
<nav class="footer-navigation">
    <@renderNavigation navigation_config.footer_navigation />
</nav>"""
    
    async def _export_workflows(self, output_dir: Path) -> None:
        """Export workflow configurations"""
        try:
            # Create default workflow
            workflow_file = output_dir / 'default_workflow.xml'
            
            workflow_content = """<?xml version="1.0" encoding="UTF-8"?>
<workflow>
    <name>Default Content Workflow</name>
    <description>Default workflow for content approval</description>
    <states>
        <state>
            <name>Draft</name>
            <description>Content in draft state</description>
        </state>
        <state>
            <name>In Review</name>
            <description>Content under review</description>
        </state>
        <state>
            <name>Approved</name>
            <description>Content approved for publishing</description>
        </state>
        <state>
            <name>Published</name>
            <description>Content published live</description>
        </state>
    </states>
</workflow>"""
            
            with open(workflow_file, 'w', encoding='utf-8') as f:
                f.write(workflow_content)
            
            self.logger.info("Workflows exported successfully")
            
        except Exception as e:
            self.logger.error(f"Workflow export failed: {e}")
    
    async def _export_scripts(self, output_dir: Path) -> None:
        """Export Groovy scripts for Crafter CMS"""
        try:
            # Create content creation script
            content_script = output_dir / 'create_content.groovy'
            
            script_content = """// Groovy script for creating content in Crafter CMS
// Generated by Recrafter

import org.craftercms.studio.api.v1.service.content.ContentService
import org.craftercms.studio.api.v1.to.Result

def contentService = applicationContext.getBean("contentService")

// Example: Create a new page
def createPage(String siteId, String path, String content) {
    try {
        def result = contentService.createContent(siteId, path, content)
        if (result.successful) {
            println "Content created successfully: ${path}"
        } else {
            println "Failed to create content: ${result.message}"
        }
        return result
    } catch (Exception e) {
        println "Error creating content: ${e.message}"
        return new Result(false, e.message)
    }
}

// Example: Update existing content
def updatePage(String siteId, String path, String content) {
    try {
        def result = contentService.updateContent(siteId, path, content)
        if (result.successful) {
            println "Content updated successfully: ${path}"
        } else {
            println "Failed to update content: ${result.message}"
        }
        return result
    } catch (Exception e) {
        println "Error updating content: ${e.message}"
        return new Result(false, e.message)
    }
}

println "Content management scripts loaded successfully"
"""
            
            with open(content_script, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            self.logger.info("Scripts exported successfully")
            
        except Exception as e:
            self.logger.error(f"Script export failed: {e}")
    
    async def _create_cms_documentation(self, output_dir: Path, input_dir: str) -> None:
        """Create documentation for the CMS export"""
        try:
            # Create README
            readme_file = output_dir / 'README.md'
            
            readme_content = f"""# Crafter CMS Migration Package

This package was generated by Recrafter for migrating your website to Crafter CMS.

## Package Contents

- **content-types/**: Content model definitions
- **templates/**: Freemarker templates
- **components/**: Reusable component templates
- **assets/**: Website assets (images, CSS, JS, etc.)
- **navigation/**: Navigation structure and configuration
- **workflows/**: Content approval workflows
- **scripts/**: Groovy scripts for automation

## Installation Instructions

1. Extract this package to your Crafter Studio workspace
2. Import content types from the `content-types/` directory
3. Upload templates from the `templates/` directory
4. Configure components from the `components/` directory
5. Upload assets from the `assets/` directory
6. Configure navigation using the `navigation/` directory
7. Set up workflows from the `workflows/` directory
8. Review and customize scripts in the `scripts/` directory

## Migration Notes

- This package was generated from: {input_dir}
- Generated on: {datetime.now().isoformat()}
- Review all templates and components before deployment
- Test workflows and scripts in a development environment
- Customize content models as needed for your specific requirements

## Support

For questions about this migration package, refer to the Recrafter documentation.
"""
            
            with open(readme_file, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            # Create migration guide
            guide_file = output_dir / 'MIGRATION_GUIDE.md'
            
            guide_content = """# Migration Guide

## Step-by-Step Migration Process

### 1. Content Types Setup
- Import content model definitions
- Customize field types and validation rules
- Set up required vs. optional fields

### 2. Template Implementation
- Review generated Freemarker templates
- Customize styling and layout
- Test with sample content

### 3. Component Library
- Review extracted components
- Implement high-frequency components first
- Test component reusability

### 4. Asset Management
- Upload all assets to Crafter's asset manager
- Update asset references in templates
- Optimize images and other media

### 5. Navigation Configuration
- Set up site navigation structure
- Configure breadcrumbs
- Test navigation functionality

### 6. Workflow Configuration
- Set up content approval workflows
- Configure user roles and permissions
- Test workflow processes

### 7. Content Migration
- Create content using new models
- Import existing content data
- Validate content display

### 8. Testing and Validation
- Test all page types
- Validate responsive design
- Check accessibility compliance

## Best Practices

- Start with a small subset of content
- Test thoroughly in development environment
- Plan for content migration downtime
- Train content editors on new system
- Document customizations and configurations
"""
            
            with open(guide_file, 'w', encoding='utf-8') as f:
                f.write(guide_content)
            
            self.logger.info("Documentation created successfully")
            
        except Exception as e:
            self.logger.error(f"Documentation creation failed: {e}")
    
    async def _create_cms_package(self, output_dir: Path) -> str:
        """Create a zip package of the CMS export"""
        try:
            zip_path = output_dir.parent / f"crafter_cms_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in output_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(output_dir)
                        zipf.write(file_path, arcname)
            
            self.logger.info(f"CMS package created: {zip_path}")
            return str(zip_path)
            
        except Exception as e:
            self.logger.error(f"Failed to create CMS package: {e}")
            raise
    
    async def _export_as_json(self, input_dir: str, output_dir: str) -> str:
        """Export data as JSON format"""
        try:
            # Load analysis results
            analysis_file = Path(input_dir) / 'metadata' / 'analysis_results.json'
            if analysis_file.exists():
                # Copy analysis results
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                
                shutil.copy2(analysis_file, output_path / 'analysis_results.json')
                
                return str(output_path / 'analysis_results.json')
            else:
                raise FileNotFoundError("Analysis results not found")
                
        except Exception as e:
            self.logger.error(f"JSON export failed: {e}")
            raise
    
    async def _export_as_yaml(self, input_dir: str, output_dir: str) -> str:
        """Export data as YAML format"""
        try:
            # Load analysis results
            analysis_file = Path(input_dir) / 'metadata' / 'analysis_results.json'
            if analysis_file.exists():
                with open(analysis_file, 'r', encoding='utf-8') as f:
                    analysis_data = json.load(f)
                
                # Convert to YAML
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                
                yaml_file = output_path / 'analysis_results.yaml'
                with open(yaml_file, 'w', encoding='utf-8') as f:
                    yaml.dump(analysis_data, f, default_flow_style=False, allow_unicode=True)
                
                return str(yaml_file)
            else:
                raise FileNotFoundError("Analysis results not found")
                
        except Exception as e:
            self.logger.error(f"YAML export failed: {e}")
            raise
