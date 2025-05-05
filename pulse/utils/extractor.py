import os
import json
import logging
from openai import OpenAI
import time
from urllib.parse import urlparse
import re
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ModuleExtractor:
    def __init__(self, api_key=None, model="gpt-3.5-turbo"):
        """Initialize the module extractor with OpenAI API key"""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set it using the OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        logging.info(f"Using OpenAI model: {self.model}")
    
    def _chunk_text(self, text, max_tokens=6000):
        """Split text into chunks to fit within token limits"""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            # Approximate token count (words / 0.75)
            word_tokens = len(word) / 0.75
            
            if current_length + word_tokens > max_tokens and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_length = word_tokens
            else:
                current_chunk.append(word)
                current_length += word_tokens
                
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        return chunks
    
    def _identify_potential_modules(self, hierarchy, titles, structure):
        """
        Identify potential modules based on site structure and document organization.
        Uses both site hierarchy and heading structure within pages.
        """
        potential_modules = {}
        
        # APPROACH 1: Use site hierarchy to identify modules
        # Get entry points (URLs that are parents but not children)
        entry_points = set(hierarchy.keys())
        all_children = set()
        for children in hierarchy.values():
            all_children.update(children)
        
        root_urls = entry_points - all_children
        
        # Track depth of each URL from root
        url_depth = {}
        for root in root_urls:
            url_depth[root] = 0
            self._calculate_depth(root, hierarchy, url_depth, depth=0)
        
        # Group URLs by depth
        urls_by_depth = {}
        for url, depth in url_depth.items():
            if depth not in urls_by_depth:
                urls_by_depth[depth] = []
            urls_by_depth[depth].append(url)
        
        # First level URLs are likely to be modules
        if 1 in urls_by_depth:
            for url in urls_by_depth[1]:
                if url in titles:
                    potential_modules[url] = {
                        "title": titles[url],
                        "child_urls": hierarchy.get(url, []),
                        "source": "hierarchy"
                    }
        
        # If no first level URLs, use root URLs
        if not potential_modules and 0 in urls_by_depth:
            for url in urls_by_depth[0]:
                if url in titles:
                    potential_modules[url] = {
                        "title": titles[url],
                        "child_urls": hierarchy.get(url, []),
                        "source": "hierarchy"
                    }
        
        # APPROACH 2: Use headings within documents to identify modules
        # This is particularly useful for single-page documentation
        for url, page_structure in structure.items():
            if "headings" in page_structure and page_structure["headings"]:
                # Group headings by level
                headings_by_level = defaultdict(list)
                for heading in page_structure["headings"]:
                    headings_by_level[heading["level"]].append(heading)
                
                # Find the highest level with multiple headings
                for level in range(1, 4):  # Check h1, h2, h3
                    level_headings = headings_by_level[level]
                    if len(level_headings) >= 2:  # Need at least 2 headings to form modules
                        # Create a module for each heading at this level
                        for heading in level_headings:
                            module_id = f"{url}#{heading['id']}" if heading['id'] else f"{url}#{heading['text']}"
                            potential_modules[module_id] = {
                                "title": heading["text"],
                                "url": url,
                                "heading_level": level,
                                "source": "heading"
                            }
                        break
        
        return potential_modules
    
    def _calculate_depth(self, url, hierarchy, url_depth, depth):
        """Calculate depth of each URL in the hierarchy"""
        for child in hierarchy.get(url, []):
            if child not in url_depth or depth + 1 < url_depth[child]:
                url_depth[child] = depth + 1
                self._calculate_depth(child, hierarchy, url_depth, depth + 1)
    
    def _group_urls_by_module(self, potential_modules, content_map, structure):
        """Group URLs and content by module with enhanced structure awareness"""
        modules_content = {}
        
        for module_id, module_info in potential_modules.items():
            module_title = module_info["title"]
            source_type = module_info.get("source", "unknown")
            
            if source_type == "hierarchy":
                # Handle modules from site hierarchy
                module_url = module_id
                
                # Get module content
                module_content = content_map.get(module_url, "")
                
                # Get child page contents
                child_contents = {}
                for child_url in module_info["child_urls"]:
                    if child_url in content_map:
                        child_contents[child_url] = content_map[child_url]
                
                # Add structured data for the module itself
                module_structured_data = {}
                if module_url in structure:
                    module_structured_data = self._extract_structured_content_summary(structure[module_url])
                
                # Add structured data for each child
                child_structured_data = {}
                for child_url in module_info["child_urls"]:
                    if child_url in structure:
                        child_structured_data[child_url] = self._extract_structured_content_summary(structure[child_url])
                
                modules_content[module_title] = {
                    "main_content": module_content,
                    "child_contents": child_contents,
                    "module_structure": module_structured_data,
                    "child_structures": child_structured_data,
                    "source_type": source_type
                }
            
            elif source_type == "heading":
                # Handle modules from document headings
                module_url = module_info["url"]
                heading_text = module_title
                heading_level = module_info["heading_level"]
                
                # Extract content related to this heading
                section_content = self._extract_section_content(
                    content_map.get(module_url, ""),
                    heading_text,
                    heading_level
                )
                
                # Get subheadings if available
                subheadings = self._extract_subheadings(
                    structure.get(module_url, {}).get("headings", []),
                    heading_text,
                    heading_level
                )
                
                # Create a pseudo-hierarchy for this heading-based module
                modules_content[module_title] = {
                    "main_content": section_content,
                    "subheadings": subheadings,
                    "source_type": source_type,
                    "url": module_url
                }
        
        return modules_content
    
    def _extract_structured_content_summary(self, page_structure):
        """Create a summary of structured content elements from a page"""
        summary = {}
        
        # Count and categorize headings by level
        heading_counts = defaultdict(int)
        headings_sample = []
        if "headings" in page_structure:
            for heading in page_structure["headings"]:
                level = heading["level"]
                heading_counts[level] += 1
                # Keep a sample of headings for each level (up to 3 per level)
                if heading_counts[level] <= 3:
                    headings_sample.append(f"H{level}: {heading['text']}")
        
        summary["heading_counts"] = dict(heading_counts)
        summary["headings_sample"] = headings_sample
        
        # Summarize lists
        if "lists" in page_structure:
            list_count = len(page_structure["lists"])
            summary["list_count"] = list_count
            
            # Sample of list items
            if list_count > 0:
                list_samples = []
                for i, list_obj in enumerate(page_structure["lists"]):
                    if i >= 2:  # Limit to 2 lists
                        break
                    list_type = list_obj["type"]
                    items = [item["text"] for item in list_obj["items"][:3]]  # Up to 3 items
                    list_samples.append({
                        "type": list_type,
                        "items": items
                    })
                summary["list_samples"] = list_samples
        
        # Summarize tables
        if "tables" in page_structure:
            table_count = len(page_structure["tables"])
            summary["table_count"] = table_count
            
            # Sample of table headers
            if table_count > 0:
                table_samples = []
                for i, table in enumerate(page_structure["tables"]):
                    if i >= 2:  # Limit to 2 tables
                        break
                    headers = table["headers"]
                    table_samples.append({
                        "headers": headers,
                        "row_count": len(table["rows"])
                    })
                summary["table_samples"] = table_samples
        
        # Summarize code blocks
        if "code_blocks" in page_structure:
            code_count = len(page_structure["code_blocks"])
            summary["code_block_count"] = code_count
        
        return summary
    
    def _extract_section_content(self, content, heading_text, heading_level):
        """
        Extract content for a specific section based on its heading
        This is used for heading-based modules
        """
        if not content:
            return ""
            
        # Create a regex pattern that will match the heading
        # This handles Markdown/HTML headings
        heading_patterns = [
            r'#{%d} %s\s*\n' % (heading_level, re.escape(heading_text)),  # Markdown
            r'<h%d[^>]*>%s</h%d>' % (heading_level, re.escape(heading_text), heading_level)  # HTML
        ]
        
        # Find the heading position
        start_pos = -1
        for pattern in heading_patterns:
            match = re.search(pattern, content)
            if match:
                start_pos = match.end()
                break
        
        if start_pos == -1:
            # Try a more relaxed pattern that ignores formatting
            pattern = re.escape(heading_text)
            match = re.search(pattern, content)
            if match:
                start_pos = match.end()
            else:
                return ""  # Heading not found
        
        # Find where this section ends (at the next heading of same or higher level)
        next_heading_pattern = r'#{1,%d} |<h[1-%d][^>]*>' % (heading_level, heading_level)
        end_match = re.search(next_heading_pattern, content[start_pos:])
        
        if end_match:
            end_pos = start_pos + end_match.start()
            section_content = content[start_pos:end_pos].strip()
        else:
            section_content = content[start_pos:].strip()
            
        return section_content
    
    def _extract_subheadings(self, headings, parent_heading, parent_level):
        """Extract subheadings under a given parent heading"""
        subheadings = []
        
        # First find the parent heading in the list
        parent_index = -1
        for i, heading in enumerate(headings):
            if heading["level"] == parent_level and heading["text"] == parent_heading:
                parent_index = i
                break
        
        if parent_index == -1:
            return subheadings
            
        # Now collect all headings that are one level deeper until we hit another heading at the same or higher level
        i = parent_index + 1
        while i < len(headings):
            heading = headings[i]
            if heading["level"] <= parent_level:
                # Same or higher level heading - end of section
                break
            elif heading["level"] == parent_level + 1:
                # Direct child heading
                subheadings.append(heading["text"])
            i += 1
            
        return subheadings
    
    def extract_modules(self, crawl_results):
        """
        Extract modules and submodules from crawled content using OpenAI
        with enhanced structure awareness
        """
        content_map = crawl_results["content"]
        hierarchy = crawl_results["hierarchy"]
        titles = crawl_results["titles"]
        structure = crawl_results["structure"]
        
        # Identify potential modules based on site structure and document organization
        potential_modules = self._identify_potential_modules(hierarchy, titles, structure)
        
        # If no modules identified from structure, use all content
        if not potential_modules:
            logging.info("No clear modules identified from site structure. Processing all content together.")
            return self._extract_from_unstructured_content(content_map)
        
        # Group content by module
        modules_content = self._group_urls_by_module(potential_modules, content_map, structure)
        
        all_modules = []
        
        # Process each module
        for module_title, module_data in modules_content.items():
            logging.info(f"Processing module: {module_title}")
            
            source_type = module_data.get("source_type", "unknown")
            
            if source_type == "hierarchy":
                # Format content for hierarchy-based module
                module_content = self._format_hierarchy_module(module_title, module_data)
            elif source_type == "heading":
                # Format content for heading-based module
                module_content = self._format_heading_module(module_title, module_data)
            else:
                # Fallback generic formatting
                module_content = f"MODULE: {module_title}\n\n"
                module_content += f"CONTENT:\n{module_data.get('main_content', '')}"
            
            # Process in chunks if content is too large
            content_chunks = self._chunk_text(module_content)
            
            module_results = []
            # Process each chunk
            for i, chunk in enumerate(content_chunks):
                try:
                    chunk_result = self._extract_module_with_submodules(
                        module_title, 
                        chunk, 
                        source_type,
                        module_data
                    )
                    module_results.append(chunk_result)
                    
                    # Rate limiting
                    if i < len(content_chunks) - 1:
                        time.sleep(1)
                        
                except Exception as e:
                    logging.error(f"Error processing chunk for module {module_title}: {e}")
            
            # Merge results for this module
            if module_results:
                merged_module = self._merge_module_results(module_results)
                all_modules.append(merged_module)
            
        return all_modules
    
    def _format_hierarchy_module(self, module_title, module_data):
        """Format content for a hierarchy-based module (from site structure)"""
        module_content = f"MODULE: {module_title}\n\n"
        
        # Add main module content
        module_content += f"MAIN CONTENT:\n{module_data['main_content']}\n\n"
        
        # Add structure information if available
        if module_data.get("module_structure"):
            structure_info = module_data["module_structure"]
            
            if "headings_sample" in structure_info and structure_info["headings_sample"]:
                module_content += "HEADINGS IN MAIN CONTENT:\n"
                for heading in structure_info["headings_sample"]:
                    module_content += f"- {heading}\n"
                module_content += "\n"
        
        # Add child page contents with their structure information
        if module_data["child_contents"]:
            module_content += "SUBMODULE CONTENTS:\n\n"
            for url, content in module_data["child_contents"].items():
                title = url.split("/")[-1].replace("-", " ").title()
                if url in module_data["child_structures"]:
                    structure_info = module_data["child_structures"][url]
                    
                    # Add heading information for better context
                    if "headings_sample" in structure_info and structure_info["headings_sample"]:
                        title_candidates = [h.split(": ", 1)[1] for h in structure_info["headings_sample"] 
                                           if h.startswith("H1:") or h.startswith("H2:")]
                        if title_candidates:
                            title = title_candidates[0]
                
                module_content += f"--- SUBMODULE: {title} ---\n{content}\n\n"
        
        return module_content
    
    def _format_heading_module(self, module_title, module_data):
        """Format content for a heading-based module (from document structure)"""
        module_content = f"MODULE: {module_title}\n\n"
        
        # Add section content
        module_content += f"CONTENT:\n{module_data['main_content']}\n\n"
        
        # Add subheadings as potential submodules
        if module_data.get("subheadings"):
            module_content += "SUBHEADINGS:\n"
            for subheading in module_data["subheadings"]:
                module_content += f"- {subheading}\n"
            module_content += "\n"
            
        # Add source URL for reference
        if module_data.get("url"):
            module_content += f"SOURCE: {module_data['url']}\n\n"
            
        return module_content
    
    def _extract_page_title_from_url(self, url):
        """Extract a readable title from URL when title is not available"""
        path = urlparse(url).path
        segments = [s for s in path.split('/') if s]
        
        if segments:
            # Use the last segment as title
            last_segment = segments[-1]
            # Convert hyphens and underscores to spaces and capitalize
            title = last_segment.replace('-', ' ').replace('_', ' ').title()
            return title
        
        return "Untitled Page"
    
    def _extract_from_unstructured_content(self, content_map):
        """Extract modules from unstructured content"""
        # Combine all content
        all_content = "\n\n".join([
            f"URL: {url}\nCONTENT:\n{content}"
            for url, content in content_map.items()
        ])
        
        # Process in chunks if content is too large
        content_chunks = self._chunk_text(all_content)
        logging.info(f"Processing unstructured content in {len(content_chunks)} chunks")
        
        all_modules = []
        
        # Process each chunk
        for i, chunk in enumerate(content_chunks):
            try:
                logging.info(f"Processing chunk {i+1}/{len(content_chunks)}")
                
                modules = self._extract_from_chunk(chunk)
                all_modules.extend(modules)
                
                # Rate limiting
                if i < len(content_chunks) - 1:
                    time.sleep(1)
                    
            except Exception as e:
                logging.error(f"Error processing chunk {i+1}: {e}")
        
        # Merge and deduplicate modules
        merged_modules = self._merge_modules(all_modules)
        return merged_modules
    
    def _extract_module_with_submodules(self, module_title, content, source_type, module_data=None):
        """Extract a single module with its submodules from content with enhanced context"""
        # Create a prompt based on the source type and available structure
        if source_type == "hierarchy":
            prompt = self._create_hierarchy_module_prompt(module_title, content, module_data)
        elif source_type == "heading":
            prompt = self._create_heading_module_prompt(module_title, content, module_data)
        else:
            # Default generic prompt
            prompt = f"""
            Analyze the following documentation content for the module '{module_title}'.
            Extract details about this module and identify its submodules.
            
            Guidelines:
            1. Focus on the specific functionality of this module
            2. Identify submodules (specific features or capabilities within this module)
            3. Generate detailed descriptions for the module and each submodule
            4. Use only information from the provided content
            
            CONTENT:
            {content}
            
            Output the module in the following JSON format:
            {{
              "module": "{module_title}",
              "Description": "Detailed description of the module",
              "Submodules": {{
                "Submodule 1": "Detailed description of submodule 1",
                "Submodule 2": "Detailed description of submodule 2"
              }}
            }}
            """
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert AI assistant that extracts structured information from documentation."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=4000
        )
        
        try:
            result_text = response.choices[0].message.content.strip()
            
            # Extract JSON part from response
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = result_text[json_start:json_end]
                module = json.loads(json_str)
                return module
            else:
                logging.error("Could not extract JSON from response")
                return {
                    "module": module_title,
                    "Description": "No description available",
                    "Submodules": {}
                }
                
        except json.JSONDecodeError as e:
            logging.error(f"JSON decoding error: {e}")
            logging.error(f"Response text: {result_text}")
            return {
                "module": module_title,
                "Description": "No description available",
                "Submodules": {}
            }
        except Exception as e:
            logging.error(f"Error parsing response: {e}")
            return {
                "module": module_title,
                "Description": "No description available",
                "Submodules": {}
            }
    
    def _create_hierarchy_module_prompt(self, module_title, content, module_data):
        """Create a specialized prompt for hierarchy-based modules"""
        # Extract additional context from the module data
        submodule_hint = ""
        
        if module_data:
            # Add hints about child pages as potential submodules
            if module_data.get("child_structures"):
                submodule_candidates = []
                for url, structure in module_data["child_structures"].items():
                    if "headings_sample" in structure and structure["headings_sample"]:
                        # Use first heading as submodule name candidate
                        heading = structure["headings_sample"][0].split(": ", 1)[1] if ": " in structure["headings_sample"][0] else structure["headings_sample"][0]
                        submodule_candidates.append(heading)
                    else:
                        # Use URL as fallback
                        name = self._extract_page_title_from_url(url)
                        submodule_candidates.append(name)
                        
                if submodule_candidates:
                    submodule_hint = "Potential submodules based on structure:\n"
                    for candidate in submodule_candidates:
                        submodule_hint += f"- {candidate}\n"
        
        # Create a comprehensive prompt
        prompt = f"""
        Analyze the following documentation content for the module '{module_title}'.
        This module was identified from the website's hierarchy structure.
        
        Guidelines:
        1. Focus on the specific functionality of this module
        2. Identify submodules (specific features or capabilities within this module)
        3. Generate detailed descriptions for the module and each submodule
        4. Use only information from the provided content
        
        {submodule_hint}
        
        CONTENT:
        {content}
        
        Output the module in the following JSON format:
        {{
          "module": "{module_title}",
          "Description": "Detailed description of the module",
          "Submodules": {{
            "Submodule 1": "Detailed description of submodule 1",
            "Submodule 2": "Detailed description of submodule 2"
          }}
        }}
        """
        
        return prompt
    
    def _create_heading_module_prompt(self, module_title, content, module_data):
        """Create a specialized prompt for heading-based modules"""
        # Extract additional context from the module data
        submodule_hint = ""
        
        if module_data and module_data.get("subheadings"):
            submodule_hint = "Potential submodules based on subheadings:\n"
            for subheading in module_data["subheadings"]:
                submodule_hint += f"- {subheading}\n"
        
        # Create a comprehensive prompt
        prompt = f"""
        Analyze the following documentation content for the module '{module_title}'.
        This module was identified from a heading in the documentation.
        
        Guidelines:
        1. Focus on the specific functionality described in this section
        2. Identify submodules (specific features or capabilities within this module)
        3. Generate detailed descriptions for the module and each submodule
        4. Use only information from the provided content
        
        {submodule_hint}
        
        CONTENT:
        {content}
        
        Output the module in the following JSON format:
        {{
          "module": "{module_title}",
          "Description": "Detailed description of the module",
          "Submodules": {{
            "Submodule 1": "Detailed description of submodule 1",
            "Submodule 2": "Detailed description of submodule 2"
          }}
        }}
        """
        
        return prompt
    
    def _extract_from_chunk(self, content):
        """Extract modules from a single content chunk"""
        prompt = f"""
        Analyze the following help documentation content and identify key modules and submodules.
        Each module should represent a major feature or category, and submodules should represent specific functionalities within that module.
        
        Guidelines:
        1. Identify main features/categories as modules
        2. Group related functionalities as submodules under each module
        3. Generate detailed descriptions for each
        4. Use only information from the provided content
        
        CONTENT:
        {content}
        
        Output a list of modules in the following JSON format:
        [
          {{
            "module": "Module Name",
            "Description": "Detailed description of the module",
            "Submodules": {{
              "Submodule 1": "Detailed description of submodule 1",
              "Submodule 2": "Detailed description of submodule 2"
            }}
          }}
        ]
        """
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are an expert AI assistant that extracts structured information from documentation."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=4000
        )
        
        try:
            result_text = response.choices[0].message.content.strip()
            
            # Extract JSON part from response
            json_start = result_text.find('[')
            json_end = result_text.rfind(']') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = result_text[json_start:json_end]
                modules = json.loads(json_str)
                return modules
            else:
                logging.error("Could not extract JSON from response")
                return []
                
        except json.JSONDecodeError as e:
            logging.error(f"JSON decoding error: {e}")
            logging.error(f"Response text: {result_text}")
            return []
        except Exception as e:
            logging.error(f"Error parsing response: {e}")
            return []
    
    def _merge_module_results(self, module_results):
        """Merge results for a single module from multiple chunks"""
        if not module_results:
            return None
            
        # Use the first result as a base
        merged = module_results[0].copy()
        
        # Merge descriptions and submodules from other results
        for result in module_results[1:]:
            # Merge descriptions (take the longer one)
            if len(result.get("Description", "")) > len(merged.get("Description", "")):
                merged["Description"] = result["Description"]
                
            # Merge submodules
            for subname, subdesc in result.get("Submodules", {}).items():
                if subname not in merged.get("Submodules", {}):
                    if "Submodules" not in merged:
                        merged["Submodules"] = {}
                    merged["Submodules"][subname] = subdesc
                elif len(subdesc) > len(merged["Submodules"][subname]):
                    merged["Submodules"][subname] = subdesc
                    
        return merged
    
    def _merge_modules(self, all_modules):
        """Merge and deduplicate modules from multiple chunks"""
        module_dict = {}
        
        for module_item in all_modules:
            module_name = module_item["module"]
            
            if module_name not in module_dict:
                module_dict[module_name] = module_item
            else:
                # Module exists, merge submodules
                existing_module = module_dict[module_name]
                
                # Update description if current one is more detailed
                if len(module_item["Description"]) > len(existing_module["Description"]):
                    existing_module["Description"] = module_item["Description"]
                
                # Merge submodules
                for submodule_name, submodule_desc in module_item["Submodules"].items():
                    if submodule_name not in existing_module["Submodules"]:
                        existing_module["Submodules"][submodule_name] = submodule_desc
                    elif len(submodule_desc) > len(existing_module["Submodules"][submodule_name]):
                        existing_module["Submodules"][submodule_name] = submodule_desc
        
        return list(module_dict.values()) 