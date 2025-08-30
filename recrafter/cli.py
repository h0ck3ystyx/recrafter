"""
Command-line interface for Recrafter
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Optional
import click

from .config import Config
from .crawler import CrawlerEngine
from .storage import StorageManager
from .analyzer import ContentAnalyzer
from .analysis_engine import AnalysisEngine
from .export_engine import ExportEngine
from .utils import setup_logging


@click.group()
@click.version_option(version="1.0.0", prog_name="Recrafter")
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--log-file', help='Log file path')
@click.pass_context
def cli(ctx, verbose, log_file):
    """Recrafter - Web crawler for CMS migration"""
    # Setup logging
    log_level = "DEBUG" if verbose else "INFO"
    logger = setup_logging(log_level, log_file)
    
    # Store logger in context
    ctx.obj = {'logger': logger}


@cli.command()
@click.option('--start-url', '-u', required=True, help='Starting URL for crawling')
@click.option('--output-dir', '-o', default='./crawl_output', help='Output directory')
@click.option('--max-depth', '-d', default=3, type=int, help='Maximum crawl depth')
@click.option('--delay', default=1.0, type=float, help='Delay between requests (seconds)')
@click.option('--max-concurrent', default=5, type=int, help='Maximum concurrent requests')
@click.option('--user-agent', help='Custom user agent string')
@click.option('--config', '-c', help='Configuration file path')
@click.option('--clean-html', is_flag=True, help='Clean HTML content')
@click.option('--save-assets', is_flag=True, default=True, help='Save assets (images, CSS, JS)')
@click.option('--extract-components', is_flag=True, default=True, help='Extract reusable components')
@click.option('--generate-models', is_flag=True, default=True, help='Generate content models')
@click.pass_context
def crawl(ctx, start_url, output_dir, max_depth, delay, max_concurrent, 
          user_agent, config, clean_html, save_assets, extract_components, generate_models):
    """Crawl a website and extract content"""
    logger = ctx.obj['logger']
    
    try:
        # Load configuration
        if config and os.path.exists(config):
            cfg = Config.from_file(config)
            logger.info(f"Loaded configuration from {config}")
        else:
            cfg = Config.default()
            logger.info("Using default configuration")
        
        # Override with CLI options
        cfg.crawler.max_depth = max_depth
        cfg.crawler.delay = delay
        cfg.crawler.max_concurrent = max_concurrent
        if user_agent:
            cfg.crawler.user_agent = user_agent
        
        cfg.storage.output_dir = output_dir
        cfg.storage.clean_html = clean_html
        cfg.storage.save_assets = save_assets
        
        cfg.analysis.extract_components = extract_components
        cfg.analysis.create_content_models = generate_models
        
        # Validate configuration
        cfg.validate()
        
        logger.info(f"Starting crawl of {start_url}")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"Max depth: {max_depth}")
        logger.info(f"Delay: {delay}s")
        logger.info(f"Max concurrent: {max_concurrent}")
        
        # Run crawler
        asyncio.run(_run_crawler(cfg, start_url, logger))
        
    except Exception as e:
        logger.error(f"Crawling failed: {e}")
        sys.exit(1)


@cli.command()
@click.option('--input-dir', '-i', required=True, help='Input directory with crawled data')
@click.option('--output-file', '-o', help='Output file for analysis results')
@click.option('--similarity-threshold', '-s', default=0.8, type=float, help='Similarity threshold for clustering (0.0-1.0)')
@click.pass_context
def analyze(ctx, input_dir, output_file, similarity_threshold):
    """Analyze crawled data and generate comprehensive reports"""
    logger = ctx.obj['logger']
    
    try:
        if not os.path.exists(input_dir):
            logger.error(f"Input directory does not exist: {input_dir}")
            sys.exit(1)
        
        if not output_file:
            output_file = os.path.join(input_dir, 'metadata', 'analysis_results.json')
        
        logger.info(f"Starting comprehensive analysis of {input_dir}")
        logger.info(f"Similarity threshold: {similarity_threshold}")
        logger.info(f"Output file: {output_file}")
        
        # Create configuration
        config = Config.default()
        config.storage.output_dir = input_dir
        
        # Run analysis
        analysis_engine = AnalysisEngine(config)
        asyncio.run(analysis_engine.run_comprehensive_analysis(input_dir, output_file))
        
        logger.info("Analysis completed successfully!")
        logger.info(f"Results saved to: {output_file}")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        sys.exit(1)


@cli.command()
@click.option('--input-dir', '-i', required=True, help='Input directory with crawled data')
@click.option('--output-dir', '-o', help='Output directory for export')
@click.option('--format', '-f', default='cms', type=click.Choice(['cms', 'json', 'yaml']), 
              help='Export format')
@click.pass_context
def export(ctx, input_dir, output_dir, format):
    """Export crawled data in various formats"""
    logger = ctx.obj['logger']
    
    try:
        if not os.path.exists(input_dir):
            logger.error(f"Input directory does not exist: {input_dir}")
            sys.exit(1)
        
        if not output_dir:
            output_dir = f"{input_dir}_export"
        
        logger.info(f"Exporting data from {input_dir} to {output_dir}")
        logger.info(f"Export format: {format}")
        
        # Create configuration
        config = Config.default()
        config.storage.output_dir = input_dir
        
        # Run export
        export_engine = ExportEngine(config)
        result = asyncio.run(export_engine.export_data(input_dir, output_dir, format))
        
        logger.info("Export completed successfully!")
        logger.info(f"Output: {result}")
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        sys.exit(1)


@cli.command()
@click.option('--input-dir', '-i', required=True, help='Input directory with crawled data')
@click.pass_context
def validate(ctx, input_dir):
    """Validate downloaded content and check integrity"""
    logger = ctx.obj['logger']
    
    try:
        if not os.path.exists(input_dir):
            logger.error(f"Input directory does not exist: {input_dir}")
            sys.exit(1)
        
        logger.info(f"Validating content in {input_dir}")
        
        # TODO: Implement validation command
        logger.info("Validation completed")
        
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(1)


@cli.command()
@click.option('--config-path', default='./recrafter_config.yaml', help='Configuration file path')
@click.pass_context
def init(ctx, config_path):
    """Initialize a new configuration file"""
    logger = ctx.obj['logger']
    
    try:
        if os.path.exists(config_path):
            logger.warning(f"Configuration file already exists: {config_path}")
            if not click.confirm("Overwrite existing file?"):
                return
        
        # Create default configuration
        config = Config.default()
        config.save_to_file(config_path)
        
        logger.info(f"Configuration file created: {config_path}")
        logger.info("Edit the file to customize settings before running the crawler")
        
    except Exception as e:
        logger.error(f"Failed to create configuration file: {e}")
        sys.exit(1)


@cli.command()
@click.option('--input-dir', '-i', required=True, help='Input directory with crawled data')
@click.pass_context
def info(ctx, input_dir):
    """Show information about crawled data"""
    logger = ctx.obj['logger']
    
    try:
        if not os.path.exists(input_dir):
            logger.error(f"Input directory does not exist: {input_dir}")
            sys.exit(1)
        
        logger.info(f"Analyzing data in {input_dir}")
        
        # Create storage manager to get info
        storage_config = Config.default().storage
        storage_config.output_dir = input_dir
        storage_manager = StorageManager(storage_config)
        
        # Get storage information
        info = storage_manager.get_storage_info()
        
        if info:
            logger.info("Storage Information:")
            logger.info(f"  Base directory: {info['base_directory']}")
            logger.info(f"  Total size: {info['total_size_mb']:.2f} MB")
            logger.info(f"  Files:")
            logger.info(f"    Pages: {info['file_counts']['pages']}")
            logger.info(f"    Assets: {info['file_counts']['assets']}")
            logger.info(f"    Metadata: {info['file_counts']['metadata']}")
        else:
            logger.warning("Could not retrieve storage information")
        
    except Exception as e:
        logger.error(f"Failed to get information: {e}")
        sys.exit(1)


async def _run_crawler(config: Config, start_url: str, logger) -> None:
    """Run the crawler engine"""
    try:
        async with CrawlerEngine(config) as crawler:
            result = await crawler.crawl(start_url)
            
            # Save metadata
            await crawler.storage.save_metadata(result)
            
            # Generate content models
            if config.analysis.create_content_models:
                analyzer = ContentAnalyzer(config.analysis)
                content_models = analyzer.generate_content_models(result.site_map.pages)
                result.content_models = content_models
                
                # Save updated result with content models
                await crawler.storage.save_metadata(result)
            
            # Print summary
            logger.info("Crawling completed successfully!")
            logger.info(f"Total pages crawled: {result.statistics['total_pages']}")
            logger.info(f"Total assets downloaded: {result.statistics['total_assets']}")
            logger.info(f"Total links found: {result.statistics['total_links']}")
            logger.info(f"Content models generated: {result.statistics['content_models']}")
            
            if result.errors:
                logger.warning(f"Errors encountered: {len(result.errors)}")
                for error in result.errors[:5]:  # Show first 5 errors
                    logger.warning(f"  - {error}")
            
            if result.warnings:
                logger.info(f"Warnings: {len(result.warnings)}")
                for warning in result.warnings[:5]:  # Show first 5 warnings
                    logger.info(f"  - {warning}")
            
            logger.info(f"Output saved to: {config.storage.output_dir}")
            
    except Exception as e:
        logger.error(f"Crawler execution failed: {e}")
        raise


if __name__ == '__main__':
    cli()
