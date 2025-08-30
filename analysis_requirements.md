# Analysis Requirements for Recrafter

## Overview

The analysis portion of the application focuses on processing the crawled website data to generate insights and artifacts that facilitate migration to Crafter CMS. This includes clustering pages by structure, detecting reusable components, inferring content models, and producing outputs like reports or export files.

## User Stories

These stories build on the core crawling functionality and incorporate ideas about identifying similar page structures, common components, and layouts. They are prioritized into epics: **Page Structure Analysis**, **Component Detection**, **Content Model Inference**, and **Reporting and Export**.

---

## Epic: Page Structure Analysis

This epic covers analyzing HTML structures to group pages and identify patterns, helping to map site hierarchies to Crafter CMS page templates and navigation.

### Story 1: Identify Similar Page Structures

**As a** migration developer  
**I want** the app to cluster pages based on DOM structure similarity (e.g., using tree edit distance or CSS selector patterns)  
**So that** I can group them into template categories for Crafter CMS.

**Acceptance Criteria:**
- **Input:** Crawled HTML files or parsed DOM trees
- **Output:** A JSON report listing clusters (e.g., `{"cluster_1": ["url1", "url2"], "similarity_metric": 0.85}`)
- **Configurable similarity threshold** (default: 80%)
- **Handle variations** like dynamic content by normalizing (e.g., ignoring inline styles)

### Story 2: Detect Layout Patterns

**As a** CMS architect  
**I want** the app to analyze page layouts (e.g., grid systems, sections like hero, content blocks)  
**So that** I can replicate them in Crafter CMS templates using Freemarker or Groovy.

**Acceptance Criteria:**
- Use libraries like BeautifulSoup to extract layout elements (e.g., `<div class="container">`, Bootstrap classes)
- **Output:** Per-page or aggregated JSON with layout descriptors (e.g., `{"header": "fixed-top", "main": "two-column", "footer": "centered-links"}`)
- **Visualize simple layouts** (e.g., generate ASCII art or Graphviz diagrams)

---

## Epic: Component Detection

This epic focuses on extracting reusable elements like headers, footers, and forms, which can be directly mapped to Crafter CMS components (draggable/reusable blocks).

### Story 3: Identify Common Page Components

**As a** frontend developer  
**I want** the app to detect reusable components across pages (e.g., navigation bars, carousels, forms)  
**So that** I can create corresponding components in Crafter Studio.

**Acceptance Criteria:**
- Scan for repeated HTML snippets using hashing or selector matching
- **Output:** A JSON file with components (e.g., `{"component_name": "global_header", "html_snippet": "<header>...</header>", "occurrences": ["url1", "url2"]}`)
- **Flag variations** (e.g., "header v1" vs. "header v2") and suggest normalization

### Story 4: Extract Interactive Elements

**As a** migration specialist  
**I want** the app to identify forms, modals, and scripts  
**So that** I can integrate them with Crafter's form builder or external services like HubSpot.

**Acceptance Criteria:**
- Parse for `<form>`, `<input>`, and JS event handlers
- **Output:** Dedicated JSON section (e.g., `{"forms": [{"action": "/submit", "fields": ["email", "name"]}]}`)
- **Option to simulate form rendering** if using a headless browser

---

## Epic: Content Model Inference

This epic infers schemas from content, aiding in defining Crafter CMS content types with fields, data types, and relationships.

### Story 5: Infer Content Models from Pages

**As a** content modeler  
**I want** the app to suggest content types and fields based on extracted data (e.g., titles, bodies, images)  
**So that** I can quickly set up models in Crafter Studio.

**Acceptance Criteria:**
- Analyze page content using heuristics or ML (e.g., via NLTK for entity recognition)
- **Output:** YAML/JSON schemas (e.g., `{"content_type": "resort_page", "fields": [{"name": "title", "type": "string"}, {"name": "images", "type": "array"}]}`)
- **Support relationships** (e.g., "related_pages" as links)

### Story 6: Map Assets and Metadata

**As a** SEO specialist  
**I want** the app to extract and suggest metadata fields (e.g., meta tags, OpenGraph)  
**So that** I can preserve SEO in Crafter CMS configurations.

**Acceptance Criteria:**
- Pull from `<head>` and other tags
- **Output:** Integrated into content models (e.g., add "seo_title" field) or separate metadata JSON

---

## Epic: Reporting and Export

This epic handles generating outputs tailored for Crafter CMS import, making the migration actionable.

### Story 7: Generate Migration Reports

**As a** project manager  
**I want** comprehensive reports on analysis results  
**So that** I can review and plan the Crafter CMS build.

**Acceptance Criteria:**
- Compile all analysis into a Markdown or PDF report with summaries, visualizations, and recommendations
- **Include stats** (e.g., "80% of pages match template X")

### Story 8: Export Data for Crafter CMS Import

**As an** importer  
**I want** the app to package analyzed data into Crafter-compatible formats (e.g., XML for content, folders for assets)  
**So that** I can bulk-import via Crafter's APIs or tools.

**Acceptance Criteria:**
- Create a zip file with structured folders (e.g., `/content-types/`, `/templates/`, `/assets/`)
- **Option for custom mappings** via config file

---

## Suggested Outputs for Crafter CMS

Based on Crafter CMS's architecture (headless-capable, with content models, templates, components, and Git-based workflows), the analysis outputs should bridge the gap between the source site's raw data and Crafter's artifacts.

### Core Outputs

1. **Structured JSON/YAML Exports**
   - Core output for automation
   - Example: `content_models.yaml` with inferred types (e.g., fields like `"hero_image": {type: "asset", multiple: true}`)
   - Can be directly copied into Crafter Studio's model editor

2. **Template Suggestions**
   - Generate skeleton Freemarker templates (`.ftl` files) based on layout analysis
   - Example: `<#include "header.ftl"> <main>${content.body}</main>`
   - Include placeholders for dynamic content

3. **Component Library**
   - Directory of extracted HTML/JS snippets as reusable components
   - Metadata like "usage_frequency" to prioritize implementation

4. **Site Hierarchy Map**
   - JSON tree or visual diagram showing page relationships
   - Useful for setting up navigation and folders in Crafter

5. **Similarity Heatmap or Clustering Visualization**
   - Use libraries like Matplotlib to output images or interactive HTML (e.g., via Plotly)
   - Shows page groups, helping decide on template variants

6. **Migration Recommendations Report**
   - Human-readable Markdown file with insights like "Cluster 1 (landing pages) shares 90% structure—recommend one template with optional fields"
   - Include warnings for unsupported features (e.g., heavy JS needing headless handling)

7. **Asset Inventory**
   - CSV/JSON list of all downloaded assets with mappings to pages
   - Ensures easy upload to Crafter's asset manager

8. **Integration Suggestions**
   - For detected forms or APIs, output notes like "Embed HubSpot form in component X"
   - Guides custom integrations

---

## Implementation Notes

- Each story includes acceptance criteria for clarity
- These can be refined based on implementation details
- The system should be configurable to handle different site types and complexity levels
- Consider performance implications for large sites (1000+ pages)
- Ensure outputs are compatible with Crafter CMS version requirements

