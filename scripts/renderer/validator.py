import xml.etree.ElementTree as ET
import re
from scripts.logger import setup_logger

logger = setup_logger()

class SVGValidationError(ValueError):
    """Exception raised when SVG validation fails."""
    pass

def validate_svg(svg_content: str, is_animated: bool = False) -> bool:
    """
    Performs full syntax and structure validation on the generated SVG content.
    Returns True if valid, raises SVGValidationError if invalid.
    """
    if not svg_content or not svg_content.strip():
        raise SVGValidationError("SVG content is empty or only whitespace.")

    # 1. Parse XML to check for well-formedness
    try:
        # Register namespaces to prevent parsing failures or strip them if needed.
        root = ET.fromstring(svg_content)
    except ET.ParseError as e:
        raise SVGValidationError(f"Invalid XML syntax: {e}")

    # Remove namespace prefixes from tags to simplify checks
    # E.g. {http://www.w3.org/2000/svg}svg -> svg
    def clean_tag(tag):
        return tag.split('}')[-1] if '}' in tag else tag

    # Verify root tag is <svg>
    if clean_tag(root.tag) != "svg":
        raise SVGValidationError(f"Root element is not <svg> (found <{clean_tag(root.tag)}>)")

    # 2. Verify viewBox attribute
    viewbox = root.attrib.get("viewBox")
    if not viewbox:
        raise SVGValidationError("Missing 'viewBox' attribute in root <svg> element.")
    
    parts = viewbox.strip().split()
    if len(parts) != 4:
        raise SVGValidationError(f"Invalid 'viewBox' format. Expected 4 values, got: '{viewbox}'")
    
    for p in parts:
        try:
            float(p)
        except ValueError:
            raise SVGValidationError(f"Non-numeric value in 'viewBox': '{p}'")

    # Collect all IDs defined in the document (specifically under defs or anywhere)
    defined_ids = set()
    for elem in root.iter():
        elem_id = elem.attrib.get("id")
        if elem_id:
            defined_ids.add(elem_id)

    # 3. Check paths, gradients, filters
    # Regex to find url(#id) references in style, fill, stroke, filter attributes
    url_ref_pattern = re.compile(r"url\(#([a-zA-Z0-9\-_]+)\)")

    for elem in root.iter():
        tag = clean_tag(elem.tag)

        # Check path elements
        if tag == "path":
            d_attrib = elem.attrib.get("d")
            if not d_attrib or not d_attrib.strip():
                raise SVGValidationError("Broken path: <path> element is missing or has empty 'd' attribute.")
            
            # Basic validation of SVG path command syntax
            d_clean = d_attrib.strip()
            if not re.match(r"^[MmZzLlHhVvCcSsQqTtAa0-9eE\s,\-\.]+$", d_clean):
                raise SVGValidationError(f"Invalid characters or syntax in path 'd': '{d_attrib[:50]}...'")

        # Verify referenced gradients and filters
        for attr in ["fill", "stroke", "filter", "style"]:
            val = elem.attrib.get(attr)
            if val:
                matches = url_ref_pattern.findall(val)
                for ref_id in matches:
                    if ref_id not in defined_ids:
                        raise SVGValidationError(f"Missing resource reference: Element <{tag}> refers to url(#{ref_id}) which is not defined in the SVG.")

    # 4. Check CSS animations if is_animated is True
    if is_animated:
        if "@keyframes rise-up" not in svg_content:
            raise SVGValidationError("Missing animation rules: '@keyframes rise-up' not found in animated SVG.")
        if ".building-group" not in svg_content:
            raise SVGValidationError("Missing animation rules: '.building-group' style class not found in animated SVG.")

    logger.debug("SVG validation completed successfully.")
    return True
