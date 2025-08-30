"""
Tests for configuration management
"""

import pytest
import tempfile
import os
from recrafter.config import Config, CrawlerConfig, StorageConfig, AnalysisConfig


class TestConfig:
    """Test configuration classes"""
    
    def test_default_config(self):
        """Test default configuration creation"""
        config = Config.default()
        
        assert config.crawler.max_depth == 3
        assert config.crawler.delay == 1.0
        assert config.crawler.max_concurrent == 5
        assert config.storage.output_dir == "./crawl_output"
        assert config.analysis.extract_components is True
    
    def test_config_validation(self):
        """Test configuration validation"""
        config = Config.default()
        
        # Valid config should not raise
        config.validate()
        
        # Invalid config should raise
        config.crawler.max_depth = 0
        with pytest.raises(ValueError, match="max_depth must be at least 1"):
            config.validate()
    
    def test_config_serialization(self):
        """Test config to/from dictionary conversion"""
        config = Config.default()
        config_dict = config.to_dict()
        
        # Convert back to config
        new_config = Config.from_dict(config_dict)
        
        assert new_config.crawler.max_depth == config.crawler.max_depth
        assert new_config.crawler.delay == config.crawler.delay
        assert new_config.storage.output_dir == config.storage.output_dir
    
    def test_config_file_operations(self):
        """Test configuration file save/load"""
        config = Config.default()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            temp_path = f.name
        
        try:
            # Save config
            config.save_to_file(temp_path)
            assert os.path.exists(temp_path)
            
            # Load config
            loaded_config = Config.from_file(temp_path)
            
            assert loaded_config.crawler.max_depth == config.crawler.max_depth
            assert loaded_config.crawler.delay == config.crawler.delay
            assert loaded_config.storage.output_dir == config.storage.output_dir
            
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_config_override(self):
        """Test configuration override functionality"""
        config = Config.default()
        
        # Override some values
        config.crawler.max_depth = 10
        config.crawler.delay = 2.5
        config.storage.output_dir = "/custom/output"
        
        assert config.crawler.max_depth == 10
        assert config.crawler.delay == 2.5
        assert config.storage.output_dir == "/custom/output"
    
    def test_invalid_config_file(self):
        """Test loading from non-existent config file"""
        with pytest.raises(FileNotFoundError):
            Config.from_file("/non/existent/config.yaml")


class TestCrawlerConfig:
    """Test crawler configuration"""
    
    def test_crawler_config_defaults(self):
        """Test crawler config default values"""
        config = CrawlerConfig()
        
        assert config.max_depth == 3
        assert config.delay == 1.0
        assert config.max_concurrent == 5
        assert config.user_agent == "Recrafter/1.0"
        assert config.respect_robots_txt is True
        assert config.timeout == 30
        assert config.max_retries == 3


class TestStorageConfig:
    """Test storage configuration"""
    
    def test_storage_config_defaults(self):
        """Test storage config default values"""
        config = StorageConfig()
        
        assert config.output_dir == "./crawl_output"
        assert config.save_assets is True
        assert config.clean_html is False
        assert config.create_backup is True
        assert config.max_file_size == 100 * 1024 * 1024  # 100MB


class TestAnalysisConfig:
    """Test analysis configuration"""
    
    def test_analysis_config_defaults(self):
        """Test analysis config default values"""
        config = AnalysisConfig()
        
        assert config.extract_components is True
        assert config.generate_sitemap is True
        assert config.create_content_models is True
        assert config.extract_metadata is True
        assert config.identify_page_types is True
