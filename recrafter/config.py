"""
Configuration management for Recrafter
"""

import os
import yaml
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class CrawlerConfig:
    """Configuration for the crawler engine"""
    max_depth: int = 3
    delay: float = 1.0
    max_concurrent: int = 5
    user_agent: str = "Recrafter/1.0"
    respect_robots_txt: bool = True
    timeout: int = 30
    max_retries: int = 3


@dataclass
class StorageConfig:
    """Configuration for storage and file management"""
    output_dir: str = "./crawl_output"
    save_assets: bool = True
    clean_html: bool = False
    create_backup: bool = True
    max_file_size: int = 100 * 1024 * 1024  # 100MB


@dataclass
class AnalysisConfig:
    """Configuration for content analysis"""
    extract_components: bool = True
    generate_sitemap: bool = True
    create_content_models: bool = True
    extract_metadata: bool = True
    identify_page_types: bool = True


@dataclass
class Config:
    """Main configuration class"""
    crawler: CrawlerConfig
    storage: StorageConfig
    analysis: AnalysisConfig
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create config from dictionary"""
        return cls(
            crawler=CrawlerConfig(**data.get('crawler', {})),
            storage=StorageConfig(**data.get('storage', {})),
            analysis=AnalysisConfig(**data.get('analysis', {}))
        )
    
    @classmethod
    def from_file(cls, config_path: str) -> 'Config':
        """Load configuration from YAML file"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return cls.from_dict(data)
    
    @classmethod
    def default(cls) -> 'Config':
        """Create default configuration"""
        return cls(
            crawler=CrawlerConfig(),
            storage=StorageConfig(),
            analysis=AnalysisConfig()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            'crawler': {
                'max_depth': self.crawler.max_depth,
                'delay': self.crawler.delay,
                'max_concurrent': self.crawler.max_concurrent,
                'user_agent': self.crawler.user_agent,
                'respect_robots_txt': self.crawler.respect_robots_txt,
                'timeout': self.crawler.timeout,
                'max_retries': self.crawler.max_retries
            },
            'storage': {
                'output_dir': self.storage.output_dir,
                'save_assets': self.storage.save_assets,
                'clean_html': self.storage.clean_html,
                'create_backup': self.storage.create_backup,
                'max_file_size': self.storage.max_file_size
            },
            'analysis': {
                'extract_components': self.analysis.extract_components,
                'generate_sitemap': self.analysis.generate_sitemap,
                'create_content_models': self.analysis.create_content_models,
                'extract_metadata': self.analysis.extract_metadata,
                'identify_page_types': self.analysis.identify_page_types
            }
        }
    
    def save_to_file(self, config_path: str) -> None:
        """Save configuration to YAML file"""
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False, indent=2)
    
    def validate(self) -> None:
        """Validate configuration values"""
        if self.crawler.max_depth < 1:
            raise ValueError("max_depth must be at least 1")
        
        if self.crawler.delay < 0:
            raise ValueError("delay must be non-negative")
        
        if self.crawler.max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")
        
        if self.storage.max_file_size < 0:
            raise ValueError("max_file_size must be non-negative")
