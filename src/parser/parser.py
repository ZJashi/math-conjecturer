import xml.etree.ElementTree as ET
from typing import List, Dict
import re

# --- Helper Functions ---
def escape_slashes(s: str) -> str:
    # to_espace = [r'\n', r'\r', r'\t', r'\b', r'\f']
    # for char in to_espace:
    #     s = s.replace(char, char.replace('\\', '\\\\'))
    return s

def undo_slash_escapes(s: str) -> str:
    """Undo backslash escapes in a string.

    Args:
        s: The input string with backslash escapes.

    Returns:
        The string with backslash escapes removed.
    """
    return s.replace("\\\\", "\\").replace('\\"', '"').replace("\\'", "'")

def trim_quotes(s: str) -> str:
    """Remove surrounding quotes from a string, if present."""
    while (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1]
    return s



def repair_llm_cdata(text):
    """
    Ensures all <![CDATA[ sections are closed before their parent 
    element's closing tag or before the next CDATA starts.
    """
    # Patterns for tags and CDATA markers
    token_pattern = re.compile(r'(<!\[CDATA\[|]]>|</?[a-zA-Z0-9_]+(?:\s+[^>]+)?>)')
    
    parts = []
    cursor = 0
    tag_stack = []
    in_cdata = False

    for match in token_pattern.finditer(text):
        token = match.group(0)
        start, end = match.span()

        # Add the text between the last match and this match
        parts.append(text[cursor:start])

        if token == "<![CDATA[":
            if in_cdata:
                # If we are already in CDATA, close the previous one first
                # to prevent illegal nested CDATA syntax
                parts.append("]]>")
            in_cdata = True
            parts.append(token)
            
        elif token == "]]>":
            if in_cdata:
                parts.append(token)
                in_cdata = False
            else:
                # Ignore stray closing markers
                pass
                
        elif token.startswith("</"):  # Closing Tag
            if in_cdata:
                # Force close CDATA before the element ends
                parts.append("]]>")
                in_cdata = False
            parts.append(token)
            if tag_stack: tag_stack.pop()
            
        elif token.startswith("<"):  # Opening Tag
            # Elements inside CDATA should be treated as text, not tags
            if in_cdata:
                parts.append(token)
            else:
                tag_name = token[1:-1].split()[0]
                tag_stack.append(tag_name)
                parts.append(token)
        
        cursor = end

    # Add remaining text
    parts.append(text[cursor:])

    # Final safety check: if string ends but CDATA is still open
    result = "".join(parts)
    if in_cdata:
        result += "]]>"
        
    return result



def make_sure_top_level_elem_is_closed(xml: str) -> str:
    '''Ensures that the top-level element is properly closed in the XML string.'''
    
    # extract the first tag name as the top-level element
    match = re.search(r'<([a-zA-Z0-9_]+)(\s+[^>]+)?>', xml)
    if match:
        elem_name = match.group(1)
    else:
        return xml 
    
    tag_start = f"<{elem_name}>"
    tag_end = f"</{elem_name}>"
    try:
        assert tag_start in xml and tag_end in xml, f"Element {elem_name} not found in XML."
        start_idx = xml.index(tag_start) + len(tag_start)
        end_idx = xml.index(tag_end)
        final_xml = xml[start_idx:end_idx].strip()
    except AssertionError as e:
        # allows for partial extraction if end tag is missing
        if tag_start in xml:
            start_idx = xml.index(tag_start) + len(tag_start)
            final_xml =  xml[start_idx:].strip()
        else:
            final_xml = xml.strip()
    finally:
        return tag_start + final_xml + tag_end


# ====================================================


def _parse_proposals_xml(xml_string: str) -> List[Dict]:
    """Parses an XML string with multiple root elements and extracts their components.
    Args:
        xml_string: The input XML string.
    Returns:
        A list of dictionaries representing the parsed elements.
    """
    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError as e:
        print(xml_string)
        raise ValueError(f"Error parsing XML: {e}")
    
    parsed_data = []
    for element in root:
        element_data = dict(element.attrib)
        for child in element:
            if child.text:
                element_data[child.tag] = child.text.strip()
        
        element_data['type'] = element.tag
        
        parsed_data.append(element_data)
            
    return parsed_data

def parse_xml_into_proposals(xml_string: str) -> List[Dict]:
    """Pipeline to repair and parse XML string."""
    xml_string = repair_llm_cdata(xml_string)
    xml_string = make_sure_top_level_elem_is_closed(xml_string)
    parsed_data = _parse_proposals_xml(xml_string)
    return parsed_data

def render_xml_in_markdown(xml_string: str, title: str) -> str:
    """Renders proposals from XML string into markdown format"""
    proposals = parse_xml_into_proposals(xml_string)
    output = f"# {title}\n"
    for proposal in proposals:
        p_type = proposal.get('type', 'No Type')
        p_title = proposal.get('title', 'No Title')
        p_id = proposal.get('id', 'No ID')
        output += f"\n## {p_type.title()} ({p_id}): {p_title}\n"
        for key in proposal:
            if key not in ['type', 'title', 'id']:
                output += f"### {key.title()}\n"
                output += f"{proposal[key]}\n\n"
    # remove all CDATA markers for display
    output = output.replace("<![CDATA[", "").replace("]]>", "")
    return output

def sanitize_memory(content: str) -> str:
    # """Make sure memory content is correct and clean to pass to LLMs."""
    # content = trim_quotes(undo_slash_escapes(content)).strip()
    return content