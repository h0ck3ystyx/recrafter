#!/usr/bin/env python3
"""
Example usage of Recrafter as a Python library
"""

import asyncio
import sys
import os

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from recrafter.config import Config
from recrafter.crawler import CrawlerEngine
from recrafter.utils import setup_logging


async def main():
    """Example of using Recrafter programmatically"""
    
    # Setup logging
    logger = setup_logging("INFO")
    logger.info("Starting Recrafter example")
    
    # Create configuration
    config = Config.default()
    
    # Customize configuration
    config.crawler.max_depth = 2
    config.crawler.delay = 1.0
    config.crawler.max_concurrent = 3
    config.storage.output_dir = "./example_output"
    config.analysis.extract_components = True
    config.analysis.create_content_models = True
    
    # Validate configuration
    config.validate()
    
    # Starting URL (replace with your target website)
    start_url = "https://example.com"
    
    logger.info(f"Configuration:")
    logger.info(f"  Max depth: {config.crawler.max_depth}")
    logger.info(f"  Delay: {config.crawler.delay}s")
    logger.info(f"  Max concurrent: {config.crawler.max_concurrent}")
    logger.info(f"  Output directory: {config.storage.output_dir}")
    
    try:
        # Run crawler
        async with CrawlerEngine(config) as crawler:
            logger.info(f"Starting crawl of {start_url}")
            
            result = await crawler.crawl(start_url)
            
            # Save metadata
            await crawler.storage.save_metadata(result)
            
            # Print results
            logger.info("Crawling completed!")
            logger.info(f"Total pages crawled: {result.statistics['total_pages']}")
            logger.info(f"Total assets downloaded: {result.statistics['total_assets']}")
            logger.info(f"Total links found: {result.statistics['total_links']}")
            logger.info(f"Content models generated: {result.statistics['content_models']}")
            
            if result.errors:
                logger.warning(f"Errors encountered: {len(result.errors)}")
                for error in result.errors[:3]:
                    logger.warning(f"  - {error}")
            
            logger.info(f"Output saved to: {config.storage.output_dir}")
            
    except Exception as e:
        logger.error(f"Crawling failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    # Run the example
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
