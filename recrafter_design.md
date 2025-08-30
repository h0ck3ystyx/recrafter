This Python application is designed to crawl a website starting from a given URL, download its contents (including HTML pages, images, CSS, JavaScript, and other assets), and store the data in a structured format. The primary goal is to facilitate website migration to Crafter CMS by enabling an AI or another Python application to analyze the stored data and generate page templates, content models, and components. The storage format should be machine-readable (e.g., JSON or YAML files) to map website elements to Crafter CMS structures, such as content types, templates (in Freemarker or Groovy), and assets.The app should be command-line based for ease of use in automation pipelines, with configurable options for depth, domains, and file types. It must handle common web crawling challenges like relative links, redirects, and duplicates.Functional Requirements1. Crawling and DownloadingStarting URL Input: Accept a starting URL as a command-line argument or configuration file input. The crawler should begin from this URL and discover linked pages recursively.
Link Discovery: Parse HTML to extract internal links (e.g., <a href>, <link>, <script src>, <img src>). Support relative and absolute URLs, and resolve them to full URLs.
Depth Control: Allow configuration of crawl depth (e.g., maximum levels from the starting URL) to prevent infinite crawling. Default to a depth of 3.
Domain Restriction: Limit crawling to the same domain as the starting URL by default, with an option to include subdomains or specific external domains.
Asset Downloading: Download and save linked assets (e.g., images, CSS, JS, PDFs) alongside HTML pages. Rewrite asset URLs in saved HTML to point to local copies for offline viewing.
Duplicate Prevention: Use a set or database to track visited URLs and avoid re-crawling duplicates.

2. Storage and StructuringOutput Directory: Save all downloaded content in a user-specified output directory, organized by URL structure (e.g., mirroring the site's folder hierarchy).
HTML Storage: Save raw HTML for each page, with an option to clean it (e.g., remove scripts or ads if configured).
Structured Data Extraction: For each page, extract and store metadata in JSON files, including:Page title, meta descriptions, keywords.
Main content sections (e.g., using heuristics like <main>, <article>, or readability libraries to identify body content).
Components: Identify reusable elements like headers, footers, navigation, forms, and carousels via CSS selectors or DOM analysis.
Assets list: Mapping of embedded assets and their local paths.

Site Map Generation: Create a JSON or XML sitemap of all crawled pages, including hierarchy, links, and page types (e.g., classify as "homepage", "blog post", "product page" based on URL patterns or content).
Content Model Inference: Generate a preliminary content model in JSON format, suggesting fields like "title", "body", "images", "related_links" based on parsed page structures. This should aid in mapping to Crafter CMS content types.
Export for CMS: Provide an export mode that bundles data into a format suitable for Crafter CMS import (e.g., zipped folder with content XML/JSON and assets).

3. Configuration and User InterfaceCommand-Line Interface (CLI): Use libraries like argparse or click for CLI options, including:--start-url: Required starting URL.
--output-dir: Directory to save files (default: ./crawl_output).
--max-depth: Crawl depth (default: 3).
--user-agent: Custom user agent string (default: something like "MigrationSpider/1.0").
--delay: Delay between requests in seconds to avoid rate limiting (default: 1).

Configuration File: Support a YAML or INI config file for advanced settings, overriding CLI args.
Logging: Implement verbose logging (e.g., using logging module) to track progress, errors, and skipped pages. Output a summary report at the end (e.g., number of pages crawled, assets downloaded).

4. Error Handling and RobustnessHTTP Error Handling: Gracefully handle 4xx/5xx errors, redirects, and timeouts. Retry failed requests up to a configurable number of times.
Robots.txt Compliance: Parse and respect robots.txt rules for the domain, including crawl delays and disallowed paths.
Encoding Support: Handle various character encodings (e.g., UTF-8, ISO-8859-1) to ensure proper text extraction.

Non-Functional RequirementsPerformance: The app should be efficient for sites with up to 1,000 pages, using asynchronous requests (e.g., via aiohttp or scrapy) for parallel crawling. Limit concurrent requests to avoid overwhelming servers (default: 5).
Dependencies: Use standard Python libraries where possible (e.g., requests, beautifulsoup4 for parsing). For advanced crawling, integrate scrapy as the core framework. Keep dependencies minimal and list them in requirements.txt.
Security: Do not execute downloaded JavaScript. Sanitize file names to prevent path traversal issues.
Portability: Compatible with Python 3.8+, runnable on Windows, macOS, and Linux.
Scalability: Design for extensibility, e.g., plugins for custom parsers or storage backends.
Testing: Include unit tests for key components (e.g., link extraction, storage) using pytest. Provide sample test cases for a small site.
Documentation: Include a README.md with usage examples, setup instructions, and extension points for AI integration.

