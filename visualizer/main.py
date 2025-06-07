from __future__ import annotations
import json
import sys
from typing import Dict, Any, List, Tuple
import hashlib

from pyvis.network import Network
import networkx as nx

# ────────────────────────────────────────────────────────────────
# Configurable appearance
# ────────────────────────────────────────────────────────────────
ROLE_COLOURS = {
    "system": "#999999",
    "user": "#0066CC",
    "assistant": "#3AAA35",
    "function_call": "#E67E22",
    "start": "#FF1493",  # Deep pink for start nodes
}

ROLE_SHAPES = {
    "system": "box",
    "user": "circle",
    "assistant": "ellipse",
    "function_call": "diamond",
    "start": "star",  # Star shape for start nodes
}

MAX_LABEL_CHARS = 40  # truncate long node values for readability


# Function to generate a color based on name
def get_color_for_name(name: str) -> str:
    """Generate a consistent color for a given name using hash."""
    if not name:
        return "#CCCCCC"  # Default color for unnamed nodes

    # Use hash to generate consistent colors
    hash_obj = hashlib.md5(name.encode())
    hash_hex = hash_obj.hexdigest()

    # Take first 6 characters as RGB color
    color = f"#{hash_hex[:6]}"
    return color


def calculate_luminance(hex_color: str) -> float:
    """Calculate the relative luminance of a hex color."""
    # Remove # if present
    hex_color = hex_color.lstrip("#")

    # Convert to RGB
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0

    # Apply gamma correction
    def gamma_correct(c):
        if c <= 0.03928:
            return c / 12.92
        else:
            return pow((c + 0.055) / 1.055, 2.4)

    r = gamma_correct(r)
    g = gamma_correct(g)
    b = gamma_correct(b)

    # Calculate luminance using standard formula
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def get_text_color_for_background(bg_color: str) -> str:
    """Get appropriate text color (black or white) for given background color."""
    luminance = calculate_luminance(bg_color)
    # Use white text for dark backgrounds (luminance < 0.5), black for light backgrounds
    return "#FFFFFF" if luminance < 0.5 else "#000000"


# ──────────────────────────────────────────────────────────────────────────────
# 1.  Load JSON (file or built-in sample)
# ──────────────────────────────────────────────────────────────────────────────
def load_graph_json(path: str | None = None) -> Dict[str, Any]:
    if path:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)


def build_networkx(
    root: Dict[str, Any],
) -> Tuple[nx.DiGraph, Dict[str, Dict[str, Any]]]:
    """Convert nested dict structure to a NetworkX DiGraph, separating function_call sub-graphs."""
    G = nx.DiGraph()
    function_call_subgraphs = {}  # Store sub-graphs keyed by parent node ID

    # Add a special start node for the main graph
    start_node_id = "MAIN_START"
    G.add_node(
        start_node_id,
        role="start",
        label="",
        name="main_start",
        full_value="Entry point for the main conversation graph",
        is_truncated=False,
        has_subgraph=False,
    )

    def build_subgraph(
        node: Dict[str, Any], parent: str | None = None, parent_name: str = ""
    ) -> Tuple[List[Dict], List[Dict], Dict[str, Dict[str, Any]]]:
        """Build a sub-graph from a function_call node, now supporting nested sub-graphs."""
        nodes = []
        edges = []
        nested_subgraphs = {}  # Store nested sub-graphs

        # Only add a special start node for this sub-graph if this is the root of a new sub-graph (parent is None)
        subgraph_start_id = None
        if parent is None:
            subgraph_start_id = f"START_{node['nodeId']}"
            start_node_config = {
                "id": subgraph_start_id,
                "label": "",
                "color": "#FF1493",  # Deep pink for start nodes
                "shape": "star",
                "font": {"size": 14, "color": "#FFFFFF"},
                "name": "subgraph_start",
                "full_value": f"Entry point for sub-graph starting with {node['nodeId']}",
                "is_truncated": False,
                "has_subgraph": False,
            }
            nodes.append(start_node_config)

        nid = node["nodeId"]
        role = node.get("role", "unknown")
        value = (
            node.get("toolArgs", "")
            if role == "function_call"
            else node.get("value", "")
        )
        name = node.get("name", "")
        tool_name = node.get("toolName", "")
        tool_result = node.get("toolResult", "")

        # Format label with role on top, name (if present), and value below
        truncated_value = (
            f"{value[:MAX_LABEL_CHARS]}{'…' if len(value) > MAX_LABEL_CHARS else ''}"
        )

        # Check if this node has function_call children
        function_call_children = [
            child
            for child in node.get("pointingToNode", [])
            if child.get("role") == "function_call"
        ]
        has_subgraph = len(function_call_children) > 0

        # Build label with role, tool name (for function calls), name, and value
        label_parts = [f"<b>{role.upper()}</b>"]
        if role == "function_call" and tool_name:
            label_parts.append(f"<b>Tool: {tool_name}</b>")
        if has_subgraph:
            label_parts.append("<b>🔧 toolUse: yes</b>")
        if name:
            label_parts.append(f"<i>{name}</i>")
        if truncated_value:
            label_parts.append(truncated_value)

        label = "\n".join(label_parts)

        # Check if content is truncated
        is_truncated = len(value) > MAX_LABEL_CHARS

        # Special styling for function_call nodes (similar to tool result nodes)
        if role == "function_call":
            # Use a distinct color for function calls
            color = "#E67E22"  # Orange color for function calls
            shape = "box"  # Use box shape like tool result nodes
            text_color = get_text_color_for_background(color)
        else:
            color = get_color_for_name(name)
            shape = ROLE_SHAPES.get(role, "ellipse")
            text_color = get_text_color_for_background(color)

        node_config = {
            "id": nid,
            "label": label,
            "color": color,
            "shape": shape,
            "font": {"size": 14, "color": text_color},
            "name": name,
            "full_value": value,
            "is_truncated": is_truncated,
            "has_subgraph": has_subgraph,
            "role": role,  # Add role so we can filter function_call nodes
        }

        # Add tool-related properties for function_call nodes
        if role == "function_call":
            node_config["toolName"] = node.get("toolName", "")
            node_config["toolArgs"] = node.get("toolArgs", "")
            node_config["toolResult"] = node.get("toolResult", "")
            node_config["toolCallIteration"] = node.get("toolCallIteration", 1)

        # Add border for nodes with sub-graphs
        if has_subgraph:
            node_config["borderWidth"] = 3
            node_config["borderColor"] = "#FF0000"

        nodes.append(node_config)

        # Connect start node to the first function_call node ONLY if we added a start node
        if subgraph_start_id:
            edges.append(
                {"from": subgraph_start_id, "to": nid, "arrows": "to", "dashes": False}
            )

        if parent:
            # Check if parent and child have same name for edge styling
            edge_style = "solid" if parent_name == name else "dashes"
            edges.append(
                {
                    "from": parent,
                    "to": nid,
                    "arrows": "to",
                    "dashes": edge_style == "dashes",
                }
            )

        # Keep track of the last node in the chain to add tool result
        last_node_id = nid

        # Process children - separate function_call from regular children
        regular_children = [
            child
            for child in node.get("pointingToNode", [])
            if child.get("role") != "function_call"
        ]

        # Add regular children to this sub-graph
        for child in regular_children:
            child_nodes, child_edges, child_nested_subgraphs = build_subgraph(
                child, nid, name
            )
            nodes.extend(child_nodes)
            edges.extend(child_edges)
            # Merge nested subgraphs from children
            nested_subgraphs.update(child_nested_subgraphs)
            # Update last node to be the last child processed
            if child_nodes:
                last_node_id = child_nodes[-1]["id"]

        # Handle function_call children as nested sub-graphs
        if function_call_children:
            subgraph_data = {"nodes": [], "edges": [], "subgraphs": {}}

            for fc_child in function_call_children:
                fc_nodes, fc_edges, fc_nested_subgraphs = build_subgraph(
                    fc_child, None, name
                )
                subgraph_data["nodes"].extend(fc_nodes)
                subgraph_data["edges"].extend(fc_edges)
                subgraph_data["subgraphs"].update(fc_nested_subgraphs)

            nested_subgraphs[nid] = subgraph_data

        # Add tool result node if this is a function_call with toolResult
        if role == "function_call" and tool_result:
            result_node_id = f"{nid}_result"

            # Format tool result for display
            truncated_result = f"{tool_result[:MAX_LABEL_CHARS]}{'…' if len(tool_result) > MAX_LABEL_CHARS else ''}"
            result_label = f"<b>TOOL RESULT</b>\n{truncated_result}"

            # Use a different color for tool result nodes
            result_color = "#28A745"  # Green color for results
            result_text_color = get_text_color_for_background(result_color)

            nodes.append(
                {
                    "id": result_node_id,
                    "label": result_label,
                    "color": result_color,
                    "shape": "box",
                    "font": {"size": 14, "color": result_text_color},
                    "name": "tool_result",
                    "full_value": tool_result,
                    "is_truncated": len(tool_result) > MAX_LABEL_CHARS,
                    "has_subgraph": False,
                }
            )

            # Connect the last node in the chain to the result node
            edges.append(
                {
                    "from": last_node_id,
                    "to": result_node_id,
                    "arrows": "to",
                    "dashes": False,
                }
            )

        return nodes, edges, nested_subgraphs

    def walk(node: Dict[str, Any], parent: str | None = None):
        nid = node["nodeId"]
        role = node.get("role", "unknown")
        value = node.get("value", "")
        name = node.get("name", "")
        tool_name = node.get("toolName", "")
        tool_args = node.get("toolArgs", "")

        # Format label with role on top, name (if present), and value below
        truncated_value = (
            f"{value[:MAX_LABEL_CHARS]}{'…' if len(value) > MAX_LABEL_CHARS else ''}"
        )

        # Build label with role, name, and value
        label_parts = [f"<b>{role.upper()}</b>"]
        if role == "function_call" and tool_name:
            label_parts.append(f"<b>Tool: {tool_name}</b>")
        if role == "function_call" and tool_args:
            # Parse and format tool args nicely
            try:
                parsed_args = json.loads(tool_args)
                args_str = json.dumps(parsed_args, indent=None, separators=(",", ":"))
                truncated_args = f"{args_str[:MAX_LABEL_CHARS]}{'…' if len(args_str) > MAX_LABEL_CHARS else ''}"
                label_parts.append(f"<b>Args: {truncated_args}</b>")
            except json.JSONDecodeError:
                # If parsing fails, just show the raw args (truncated)
                truncated_args = f"{tool_args[:MAX_LABEL_CHARS]}{'…' if len(tool_args) > MAX_LABEL_CHARS else ''}"
                label_parts.append(f"<b>Args: {truncated_args}</b>")
        if name:
            label_parts.append(f"<i>{name}</i>")
        if truncated_value:
            label_parts.append(truncated_value)

        label = "\n".join(label_parts)

        # Check if content is truncated
        is_truncated = len(value) > MAX_LABEL_CHARS

        # Add node to main graph with name information and full value
        G.add_node(
            nid,
            role=role,
            label=label,
            name=name,
            full_value=value,
            is_truncated=is_truncated,
        )
        if parent:
            G.add_edge(parent, nid)

        # Process children
        function_call_children = []
        regular_children = []

        for child in node.get("pointingToNode", []):
            if child.get("role") == "function_call":
                function_call_children.append(child)
            else:
                regular_children.append(child)

        # Add regular children to main graph
        for child in regular_children:
            walk(child, nid)

        # Store function_call children as sub-graphs
        if function_call_children:
            # Mark this node as having sub-graphs
            G.nodes[nid]["has_subgraph"] = True

            # Update the label to include toolUse indicator
            updated_label_parts = [f"<b>{role.upper()}</b>"]
            if role == "function_call" and tool_name:
                updated_label_parts.append(f"<b>Tool: {tool_name}</b>")
            if role == "function_call" and tool_args:
                # Parse and format tool args nicely
                try:
                    parsed_args = json.loads(tool_args)
                    args_str = json.dumps(
                        parsed_args, indent=None, separators=(",", ":")
                    )
                    truncated_args = f"{args_str[:MAX_LABEL_CHARS]}{'…' if len(args_str) > MAX_LABEL_CHARS else ''}"
                    updated_label_parts.append(f"<b>Args: {truncated_args}</b>")
                except json.JSONDecodeError:
                    # If parsing fails, just show the raw args (truncated)
                    truncated_args = f"{tool_args[:MAX_LABEL_CHARS]}{'…' if len(tool_args) > MAX_LABEL_CHARS else ''}"
                    updated_label_parts.append(f"<b>Args: {truncated_args}</b>")
            updated_label_parts.append("<b>🔧 toolUse: yes</b>")
            if name:
                updated_label_parts.append(f"<i>{name}</i>")
            if truncated_value:
                updated_label_parts.append(truncated_value)

            updated_label = "\n".join(updated_label_parts)
            G.nodes[nid]["label"] = updated_label

            # Create sub-graph for function_call children
            subgraph_data = {
                "nodes": [],
                "edges": [],
                "subgraphs": {},  # Add nested subgraphs support
            }

            for fc_child in function_call_children:
                # Build sub-graph from function_call node
                subgraph_nodes, subgraph_edges, nested_subgraphs = build_subgraph(
                    fc_child, None, name
                )
                subgraph_data["nodes"].extend(subgraph_nodes)
                subgraph_data["edges"].extend(subgraph_edges)
                # Merge nested subgraphs
                subgraph_data["subgraphs"].update(nested_subgraphs)

            function_call_subgraphs[nid] = subgraph_data
        else:
            # Mark this node as not having sub-graphs
            G.nodes[nid]["has_subgraph"] = False

    # Start walking from the root, with the start node as parent
    walk(root, start_node_id)

    return G, function_call_subgraphs


def to_pyvis(G: nx.DiGraph, out_html: str = "llm_graph.html") -> None:
    """Convert the NetworkX graph to PyVis and write an HTML file."""
    net = Network(height="750px", width="100%", directed=True, bgcolor="#FFFFFF")

    # Transfer nodes and edges with styling
    for node_id, data in G.nodes(data=True):
        role = data.get("role", "unknown")
        color = ROLE_COLOURS.get(role, "#CCCCCC")
        net.add_node(
            node_id,
            label=data["label"],
            title=data["label"],  # tooltip
            color=color,
            shape=ROLE_SHAPES.get(role, "ellipse"),
            font={"size": 14},
        )

    for src, dst in G.edges():
        net.add_edge(src, dst, arrows="to")

    net.toggle_physics(True)  # enable force-directed layout in browser

    # Fix for PyVis template issue - use write_html with notebook=False
    try:
        net.write_html(out_html, notebook=False)
        print(f"Graph written to {out_html}")
    except AttributeError as e:
        print(f"PyVis template error: {e}")
        print("Trying alternative approach...")
        # Alternative: save the network data and create a simple HTML file
        create_simple_html_graph(G, out_html)


def create_simple_html_graph(
    G: nx.DiGraph,
    out_html: str = "llm_graph.html",
    subgraphs: Dict[str, Dict[str, Any]] = None,
) -> None:
    """Create a simple HTML visualization using vis.js directly with sub-graph support."""

    # Prepare nodes and edges data
    nodes_data = []
    edges_data = []

    for node_id, data in G.nodes(data=True):
        role = data.get("role", "unknown")
        name = data.get("name", "")
        full_value = data.get("full_value", "")
        is_truncated = data.get("is_truncated", False)
        has_subgraph = data.get("has_subgraph", False)

        # Use name-based color instead of role-based, but special styling for function_call and start nodes
        if role == "function_call":
            # Use a distinct color for function calls (same as in subgraphs)
            color = "#E67E22"  # Orange color for function calls
            shape = "box"  # Use box shape like tool result nodes
        elif role == "start":
            # Use special styling for start nodes
            color = "#FF1493"  # Deep pink for start nodes
            shape = "star"  # Star shape for start nodes
        else:
            color = get_color_for_name(name)
            shape = ROLE_SHAPES.get(role, "ellipse")

        text_color = get_text_color_for_background(color)

        # Create enhanced label with toolUse indicator if needed
        original_label = data["label"]
        if has_subgraph and "🔧 toolUse: yes" not in original_label:
            # Split the original label and insert toolUse indicator after role
            label_lines = original_label.split("\n")
            enhanced_label_parts = [label_lines[0]]  # Role line
            enhanced_label_parts.append("<b>🔧 toolUse: yes</b>")
            enhanced_label_parts.extend(label_lines[1:])  # Rest of the label
            enhanced_label = "\n".join(enhanced_label_parts)
        else:
            enhanced_label = original_label

        # Highlight nodes that have sub-graphs with a border
        node_config = {
            "id": node_id,
            "label": enhanced_label,
            "color": color,
            "shape": shape,
            "font": {"size": 14, "align": "center", "color": text_color},
            "has_subgraph": has_subgraph,
            "name": name,
            "full_value": full_value,
            "is_truncated": is_truncated,
        }

        if has_subgraph:
            node_config["borderWidth"] = 5  # Thicker border
            node_config["borderColor"] = "#FF0000"
            # Make the entire node slightly larger to draw attention
            node_config["size"] = 30
        elif is_truncated:
            # Add a different border style for truncated content
            node_config["borderWidth"] = 2
            node_config["borderColor"] = "#FFA500"  # Orange border

        nodes_data.append(node_config)

    for src, dst in G.edges():
        src_name = G.nodes[src].get("name", "")
        dst_name = G.nodes[dst].get("name", "")

        # Use solid line for same name, dotted for different names
        edge_config = {"from": src, "to": dst, "arrows": "to"}

        if src_name != dst_name:
            edge_config["dashes"] = True

        edges_data.append(edge_config)

    # Convert subgraphs to JSON for inclusion in HTML
    subgraphs_json = json.dumps(subgraphs if subgraphs else {})

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>LLM Graph Visualization</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style type="text/css">
        #mynetworkid {{
            width: 100%;
            height: 750px;
            border: 1px solid lightgray;
        }}
        #tooluse-table-modal {{
            display: none;
            position: fixed;
            z-index: 1001;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }}
        #tooluse-table-content {{
            background-color: #fefefe;
            margin: 5% auto;
            padding: 20px;
            border: 1px solid #888;
            width: 90%;
            height: 80%;
            position: relative;
            overflow-y: auto;
        }}
        #tooluse-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        #tooluse-table th, #tooluse-table td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
            vertical-align: top;
        }}
        #tooluse-table th {{
            background-color: #f2f2f2;
            font-weight: bold;
            position: sticky;
            top: 0;
        }}
        #tooluse-table tr:hover {{
            background-color: #f5f5f5;
            cursor: pointer;
        }}
        #tooluse-table tr.selected {{
            background-color: #e3f2fd;
        }}
        .tool-args {{
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-family: monospace;
            font-size: 12px;
        }}
        .tool-result {{
            max-width: 400px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-family: monospace;
            font-size: 12px;
        }}
        .iteration-badge {{
            background-color: #007bff;
            color: white;
            padding: 2px 6px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
        }}
        #subgraph-modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }}
        #subgraph-content {{
            background-color: #fefefe;
            margin: 5% auto;
            padding: 20px;
            border: 1px solid #888;
            width: 90%;
            height: 80%;
            position: relative;
        }}
        #subgraph-network {{
            width: 100%;
            height: calc(100% - 50px);
            border: 1px solid lightgray;
        }}
        #fullcontent-modal {{
            display: none;
            position: fixed;
            z-index: 1002;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }}
        #fullcontent-content {{
            background-color: #fefefe;
            margin: 10% auto;
            padding: 20px;
            border: 1px solid #888;
            width: 80%;
            max-height: 70%;
            position: relative;
            overflow-y: auto;
        }}
        #fullcontent-text {{
            font-family: monospace;
            white-space: pre-wrap;
            word-wrap: break-word;
            background-color: #f5f5f5;
            padding: 15px;
            border: 1px solid #ddd;
            border-radius: 4px;
            max-height: 400px;
            overflow-y: auto;
        }}
        #choice-modal {{
            display: none;
            position: fixed;
            z-index: 1003;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
        }}
        #choice-content {{
            background-color: #fefefe;
            margin: 20% auto;
            padding: 30px;
            border: 1px solid #888;
            width: 400px;
            position: relative;
            text-align: center;
            border-radius: 8px;
        }}
        .choice-button {{
            background-color: #0066CC;
            color: white;
            border: none;
            padding: 12px 24px;
            margin: 10px;
            cursor: pointer;
            border-radius: 4px;
            font-size: 14px;
        }}
        .choice-button:hover {{
            background-color: #0052A3;
        }}
        .choice-button.secondary {{
            background-color: #28A745;
        }}
        .choice-button.secondary:hover {{
            background-color: #218838;
        }}
        .close {{
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
            cursor: pointer;
        }}
        .close:hover,
        .close:focus {{
            color: black;
            text-decoration: none;
        }}
        #instructions {{
            background-color: #f0f8ff;
            padding: 10px;
            margin: 10px 0;
            border-left: 4px solid #0066CC;
            font-size: 14px;
        }}
        #legend {{
            background-color: #f9f9f9;
            padding: 10px;
            margin: 10px 0;
            border: 1px solid #ddd;
            font-size: 12px;
        }}
        #subgraph-breadcrumb {{
            background-color: #e9ecef;
            padding: 5px 10px;
            margin-bottom: 10px;
            border-radius: 4px;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div id="legend">
        <strong>Legend:</strong> Nodes are colored by their "name" property. Role is displayed at the top of each node, above the value. Function call nodes also show the tool name and arguments. Shapes: System=box, User=circle, Assistant=ellipse, Function Call=box, Start=star (deep pink). Nodes with "🔧 toolUse: yes" contain function call sub-graphs (larger size) - click to see tool usage table.
    </div>
    <div id="mynetworkid"></div>
    
    <!-- Modal for tool use table -->
    <div id="tooluse-table-modal">
        <div id="tooluse-table-content">
            <span class="close">&times;</span>
            <h3 id="tooluse-table-title">Tool Usage List</h3>
            <p>Click on a row to view the sub-graph for that specific tool call:</p>
            <table id="tooluse-table">
                <thead>
                    <tr>
                        <th>Iteration</th>
                        <th>Tool Name</th>
                        <th>Arguments</th>
                        <th>Result</th>
                    </tr>
                </thead>
                <tbody id="tooluse-table-body">
                </tbody>
            </table>
        </div>
    </div>
    
    <!-- Modal for sub-graph display -->
    <div id="subgraph-modal">
        <div id="subgraph-content">
            <span class="close">&times;</span>
            <div id="subgraph-breadcrumb"></div>
            <h3 id="subgraph-title">Function Call Sub-graph</h3>
            <div id="subgraph-network"></div>
        </div>
    </div>
    
    <!-- Modal for full content display -->
    <div id="fullcontent-modal">
        <div id="fullcontent-content">
            <span class="close">&times;</span>
            <h3 id="fullcontent-title">Full Content</h3>
            <div id="fullcontent-text"></div>
        </div>
    </div>

    <!-- Modal for choice between subgraph and full content -->
    <div id="choice-modal">
        <div id="choice-content">
            <span class="close">&times;</span>
            <h3>What would you like to view?</h3>
            <p>This node has both a sub-graph and truncated content.</p>
            <button class="choice-button" onclick="choiceSubgraph()">View Tool Usage Table</button>
            <button class="choice-button secondary" onclick="choiceFullContent()">View Full Content</button>
        </div>
    </div>

    <script type="text/javascript">
        // Main graph data
        var nodes = new vis.DataSet({json.dumps(nodes_data)});
        var edges = new vis.DataSet({json.dumps(edges_data)});
        var container = document.getElementById('mynetworkid');
        var data = {{
            nodes: nodes,
            edges: edges
        }};
        var options = {{
            physics: {{
                enabled: true,
                solver: 'barnesHut',
                barnesHut: {{
                    gravitationalConstant: -8000,
                    centralGravity: 0.1,
                    springLength: 200,
                    springConstant: 0.05,
                    damping: 0.09,
                    avoidOverlap: 1
                }},
                stabilization: {{
                    iterations: 100,
                    onlyDynamicEdges: false,
                    fit: true
                }}
            }},
            layout: {{
                improvedLayout: true,
                randomSeed: 42  // Fixed seed for deterministic layout
            }},
            nodes: {{
                font: {{
                    multi: 'html'
                }}
            }}
        }};
        var network = new vis.Network(container, data, options);
        
        // Disable physics after stabilization to keep nodes static
        network.once('stabilizationIterationsDone', function() {{
            network.setOptions({{physics: {{enabled: false}}}});
        }});
        
        // Sub-graph data
        var subgraphs = {subgraphs_json};
        
        // Modal stack for navigation
        var modalStack = [];
        
        // Modal elements
        var toolTableModal = document.getElementById('tooluse-table-modal');
        var subgraphModal = document.getElementById('subgraph-modal');
        var fullcontentModal = document.getElementById('fullcontent-modal');
        var choiceModal = document.getElementById('choice-modal');
        var toolTableSpan = document.querySelector('#tooluse-table-modal .close');
        var subgraphSpan = document.querySelector('#subgraph-modal .close');
        var fullcontentSpan = document.querySelector('#fullcontent-modal .close');
        var choiceSpan = document.querySelector('#choice-modal .close');
        var subgraphContainer = document.getElementById('subgraph-network');
        var subgraphTitle = document.getElementById('subgraph-title');
        var subgraphBreadcrumb = document.getElementById('subgraph-breadcrumb');
        var fullcontentTitle = document.getElementById('fullcontent-title');
        var fullcontentText = document.getElementById('fullcontent-text');
        var toolTableTitle = document.getElementById('tooluse-table-title');
        var toolTableBody = document.getElementById('tooluse-table-body');
        
        // Variables to store choice modal context
        var choiceNodeId = null;
        var choiceNodeData = null;
        var choiceAvailableSubgraphs = null;
        
        // Modal stack management functions
        function pushModal(modalInfo) {{
            modalStack.push(modalInfo);
            showCurrentModal();
            updateBreadcrumb();
        }}
        
        function popModal() {{
            if (modalStack.length > 0) {{
                var currentModal = modalStack[modalStack.length - 1];
                hideModal(currentModal.type);
                modalStack.pop();
            }}
            
            if (modalStack.length > 0) {{
                showCurrentModal();
            }}
            updateBreadcrumb();
        }}
        
        function clearModalStack() {{
            while (modalStack.length > 0) {{
                var currentModal = modalStack[modalStack.length - 1];
                hideModal(currentModal.type);
                modalStack.pop();
            }}
            updateBreadcrumb();
        }}
        
        function showCurrentModal() {{
            if (modalStack.length === 0) return;
            
            var currentModal = modalStack[modalStack.length - 1];
            
            // For choice and fullContent modals, don't hide underlying modals - just show on top
            if (currentModal.type !== 'choice' && currentModal.type !== 'fullContent') {{
                hideAllModals();
            }}
            
            switch (currentModal.type) {{
                case 'toolTable':
                    showToolTableModal(currentModal.data);
                    break;
                case 'subgraph':
                    showSubgraphModal(currentModal.data);
                    break;
                case 'fullContent':
                    showFullContentModal(currentModal.data);
                    break;
                case 'choice':
                    showChoiceModal(currentModal.data);
                    break;
            }}
        }}
        
        function hideAllModals() {{
            toolTableModal.style.display = "none";
            subgraphModal.style.display = "none";
            fullcontentModal.style.display = "none";
            choiceModal.style.display = "none";
        }}
        
        function hideModal(modalType) {{
            switch (modalType) {{
                case 'toolTable':
                    toolTableModal.style.display = "none";
                    break;
                case 'subgraph':
                    subgraphModal.style.display = "none";
                    break;
                case 'fullContent':
                    fullcontentModal.style.display = "none";
                    break;
                case 'choice':
                    choiceModal.style.display = "none";
                    break;
            }}
        }}
        
        // Handle main graph node clicks
        network.on("click", function (params) {{
            if (params.nodes.length > 0) {{
                var nodeId = params.nodes[0];
                var nodeData = nodes.get(nodeId);
                handleNodeClick(nodeId, nodeData, subgraphs);
            }}
        }});
        
        // Generic function to handle node clicks
        function handleNodeClick(nodeId, nodeData, availableSubgraphs) {{
            var hasSubgraph = nodeData.has_subgraph && availableSubgraphs[nodeId];
            var isTruncated = nodeData.is_truncated;
            
            if (hasSubgraph && isTruncated) {{
                // Push choice modal onto stack
                pushModal({{
                    type: 'choice',
                    data: {{
                        nodeId: nodeId,
                        nodeData: nodeData,
                        availableSubgraphs: availableSubgraphs
                    }}
                }});
            }} else if (hasSubgraph) {{
                // Push tool table modal onto stack
                pushModal({{
                    type: 'toolTable',
                    data: {{
                        parentNodeId: nodeId,
                        subgraphData: availableSubgraphs[nodeId],
                        availableSubgraphs: availableSubgraphs
                    }}
                }});
            }} else if (isTruncated) {{
                // Push full content modal onto stack
                pushModal({{
                    type: 'fullContent',
                    data: {{
                        nodeId: nodeId,
                        nodeData: nodeData
                    }}
                }});
            }}
        }}
        
        // Function to extract tool call information from subgraph data
        function extractToolCallsFromSubgraph(subgraphData) {{
            var toolCalls = [];
            
            // Parse nodes to find function_call nodes with tool information
            if (subgraphData.nodes) {{
                for (var i = 0; i < subgraphData.nodes.length; i++) {{
                    var node = subgraphData.nodes[i];
                    var nodeId = node.id;
                    
                    // Only process function_call nodes
                    if (node.role !== 'function_call') {{
                        continue;
                    }}
                    
                    // Extract tool information from the node data
                    var toolName = node.toolName || 'Unknown Tool';
                    var toolArgs = node.toolArgs || '';
                    var toolResult = node.toolResult || '';
                    var iteration = node.toolCallIteration || 1;
                    
                    // Add this tool call to our list
                    toolCalls.push({{
                        nodeId: nodeId,
                        toolName: toolName,
                        toolArgs: toolArgs,
                        toolResult: toolResult,
                        iteration: iteration,
                        subgraphData: subgraphData
                    }});
                }}
            }}
            
            return toolCalls;
        }}
        
        // Function to show tool table modal
        function showToolTableModal(modalData) {{
            var parentNodeId = modalData.parentNodeId;
            var subgraphData = modalData.subgraphData;
            var availableSubgraphs = modalData.availableSubgraphs;
            
            toolTableTitle.textContent = `Tool Usage for Node: ${{parentNodeId}}`;
            
            // Extract tool calls from subgraph data
            var toolCalls = extractToolCallsFromSubgraph(subgraphData);
            
            // Clear existing table rows
            toolTableBody.innerHTML = '';
            
            // Populate table with tool calls
            for (var i = 0; i < toolCalls.length; i++) {{
                var toolCall = toolCalls[i];
                var row = document.createElement('tr');
                row.setAttribute('data-node-id', toolCall.nodeId);
                row.style.cursor = 'pointer';
                
                // Add click handler to the row
                row.addEventListener('click', function(event) {{
                    var clickedNodeId = event.currentTarget.getAttribute('data-node-id');
                    
                    // Remove selection from other rows
                    var allRows = toolTableBody.querySelectorAll('tr');
                    for (var j = 0; j < allRows.length; j++) {{
                        allRows[j].classList.remove('selected');
                    }}
                    
                    // Add selection to clicked row
                    event.currentTarget.classList.add('selected');
                    
                    // Push specific tool subgraph modal onto stack
                    pushModal({{
                        type: 'subgraph',
                        data: {{
                            toolNodeId: clickedNodeId,
                            subgraphData: subgraphData,
                            availableSubgraphs: availableSubgraphs,
                            parentNodeId: parentNodeId
                        }}
                    }});
                }});
                
                // Create table cells
                var iterationCell = document.createElement('td');
                iterationCell.innerHTML = `<span class="iteration-badge">${{toolCall.iteration}}</span>`;
                
                var toolNameCell = document.createElement('td');
                toolNameCell.textContent = toolCall.toolName;
                toolNameCell.style.fontWeight = 'bold';
                
                var argsCell = document.createElement('td');
                argsCell.textContent = toolCall.toolArgs || 'N/A';
                argsCell.className = 'tool-args';
                argsCell.title = toolCall.toolArgs || 'N/A'; // Show full text on hover
                
                var resultCell = document.createElement('td');
                resultCell.textContent = toolCall.toolResult || 'N/A';
                resultCell.className = 'tool-result';
                resultCell.title = toolCall.toolResult || 'N/A'; // Show full text on hover
                
                row.appendChild(iterationCell);
                row.appendChild(toolNameCell);
                row.appendChild(argsCell);
                row.appendChild(resultCell);
                
                toolTableBody.appendChild(row);
            }}
            
            toolTableModal.style.display = "block";
        }}
        
        // Function to show subgraph modal
        function showSubgraphModal(modalData) {{
            var toolNodeId = modalData.toolNodeId;
            var subgraphData = modalData.subgraphData;
            var availableSubgraphs = modalData.availableSubgraphs;
            var parentNodeId = modalData.parentNodeId;
            
            // Find the tool node to get its name for the title
            var toolNode = subgraphData.nodes.find(function(n) {{ return n.id === toolNodeId; }});
            if (!toolNode) {{
                console.error("Tool node not found:", toolNodeId);
                return;
            }}
            
            // Filter nodes and edges to show only the specific tool and its descendants
            function findDescendants(nodeId, edges) {{
                var descendants = new Set([nodeId]);
                var toVisit = [nodeId];
                
                while (toVisit.length > 0) {{
                    var currentId = toVisit.pop();
                    
                    // Find all edges where this node is the source
                    for (var i = 0; i < edges.length; i++) {{
                        var edge = edges[i];
                        if (edge.from === currentId && !descendants.has(edge.to)) {{
                            descendants.add(edge.to);
                            toVisit.push(edge.to);
                        }}
                    }}
                }}
                
                return Array.from(descendants);
            }}
            
            // Get all descendants of the tool node
            var relevantNodeIds = findDescendants(toolNodeId, subgraphData.edges);
            
            // Filter nodes to only include the tool node and its descendants
            var filteredNodes = subgraphData.nodes.filter(function(node) {{
                return relevantNodeIds.includes(node.id);
            }});
            
            // Filter edges to only include connections between the filtered nodes
            var filteredEdges = subgraphData.edges.filter(function(edge) {{
                return relevantNodeIds.includes(edge.from) && relevantNodeIds.includes(edge.to);
            }});
            
            // Filter subgraphs to only include those from the filtered nodes
            var filteredSubgraphs = {{}};
            if (subgraphData.subgraphs) {{
                for (var nodeId in subgraphData.subgraphs) {{
                    if (relevantNodeIds.includes(nodeId)) {{
                        filteredSubgraphs[nodeId] = subgraphData.subgraphs[nodeId];
                    }}
                }}
            }}
            
            var toolName = toolNode.toolName || toolNode.name || toolNodeId;
            subgraphTitle.textContent = `Tool Call Sub-graph: ${{toolName}}`;
            
            var subNodes = new vis.DataSet(filteredNodes);
            var subEdges = new vis.DataSet(filteredEdges);
            
            var subData = {{
                nodes: subNodes,
                edges: subEdges
            }};
            
            var subOptions = {{
                physics: {{
                    enabled: true,
                    solver: 'barnesHut',
                    barnesHut: {{
                        gravitationalConstant: -8000,
                        centralGravity: 0.1,
                        springLength: 200,
                        springConstant: 0.05,
                        damping: 0.09,
                        avoidOverlap: 1
                    }},
                    stabilization: {{
                        iterations: 50,
                        onlyDynamicEdges: false,
                        fit: true
                    }}
                }},
                layout: {{
                    improvedLayout: true,
                    randomSeed: 42  // Fixed seed for deterministic layout
                }},
                nodes: {{
                    font: {{
                        multi: 'html'
                    }}
                }}
            }};
            
            var subgraphNetwork = new vis.Network(subgraphContainer, subData, subOptions);
            
            // Disable physics after stabilization to keep nodes static
            subgraphNetwork.once('stabilizationIterationsDone', function() {{
                subgraphNetwork.setOptions({{physics: {{enabled: false}}}});
            }});
            
            // Handle clicks within the sub-graph
            subgraphNetwork.on("click", function (params) {{
                if (params.nodes.length > 0) {{
                    var subNodeId = params.nodes[0];
                    var subNodeData = subNodes.get(subNodeId);
                    handleNodeClick(subNodeId, subNodeData, filteredSubgraphs);
                }}
            }});
            
            subgraphModal.style.display = "block";
        }}
        
        // Function to show full content modal
        function showFullContentModal(modalData) {{
            var nodeId = modalData.nodeId;
            var nodeData = modalData.nodeData;
            
            fullcontentTitle.textContent = `Full Content for Node: ${{nodeId}} (${{nodeData.name || 'Unnamed'}})`;
            fullcontentText.textContent = nodeData.full_value;
            fullcontentModal.style.display = "block";
        }}
        
        // Function to show choice modal
        function showChoiceModal(modalData) {{
            choiceNodeId = modalData.nodeId;
            choiceNodeData = modalData.nodeData;
            choiceAvailableSubgraphs = modalData.availableSubgraphs;
            choiceModal.style.display = "block";
        }}
        
        // Function to update breadcrumb trail
        function updateBreadcrumb() {{
            if (modalStack.length === 0) {{
                subgraphBreadcrumb.style.display = "none";
                return;
            }}
            
            subgraphBreadcrumb.style.display = "block";
            var breadcrumbText = "Navigation Stack (depth " + modalStack.length + "): Main";
            
            for (var i = 0; i < modalStack.length; i++) {{
                var modal = modalStack[i];
                switch (modal.type) {{
                    case 'toolTable':
                        breadcrumbText += " → Tool Table (" + modal.data.parentNodeId + ")";
                        break;
                    case 'subgraph':
                        var toolName = modal.data.toolNodeId;
                        breadcrumbText += " → Sub-graph (" + toolName + ")";
                        break;
                    case 'fullContent':
                        breadcrumbText += " → Content (" + modal.data.nodeId + ")";
                        break;
                    case 'choice':
                        breadcrumbText += " → Choice (" + modal.data.nodeId + ")";
                        break;
                }}
            }}
            
            var backButton = modalStack.length > 0 ? '<button onclick="goBack()" style="margin-left: 10px; font-size: 10px;">← Back</button>' : '';
            var closeAllButton = modalStack.length > 1 ? '<button onclick="closeAll()" style="margin-left: 5px; font-size: 10px;">✕ Close All</button>' : '';
            
            subgraphBreadcrumb.innerHTML = breadcrumbText + backButton + closeAllButton;
        }}
        
        // Function to go back one level in the modal stack
        function goBack() {{
            popModal();
        }}
        
        // Function to close all modals
        function closeAll() {{
            clearModalStack();
        }}
        
        // Functions to handle choice modal selections
        function choiceSubgraph() {{
            if (choiceNodeId && choiceAvailableSubgraphs && choiceAvailableSubgraphs[choiceNodeId]) {{
                // Hide choice modal first
                choiceModal.style.display = "none";
                
                // Replace the choice modal with tool table modal
                modalStack[modalStack.length - 1] = {{
                    type: 'toolTable',
                    data: {{
                        parentNodeId: choiceNodeId,
                        subgraphData: choiceAvailableSubgraphs[choiceNodeId],
                        availableSubgraphs: choiceAvailableSubgraphs
                    }}
                }};
                showCurrentModal();
            }}
        }}
        
        function choiceFullContent() {{
            if (choiceNodeId && choiceNodeData) {{
                // Hide choice modal first
                choiceModal.style.display = "none";
                
                // Replace the choice modal with full content modal
                modalStack[modalStack.length - 1] = {{
                    type: 'fullContent',
                    data: {{
                        nodeId: choiceNodeId,
                        nodeData: choiceNodeData
                    }}
                }};
                showCurrentModal();
            }}
        }}
        
        // Close modal handlers
        toolTableSpan.onclick = function() {{
            popModal();
        }}
        
        subgraphSpan.onclick = function() {{
            popModal();
        }}
        
        fullcontentSpan.onclick = function() {{
            popModal();
        }}
        
        choiceSpan.onclick = function() {{
            popModal();
        }}
        
        // Close modal when clicking outside of it
        window.onclick = function(event) {{
            if (event.target == toolTableModal || 
                event.target == subgraphModal || 
                event.target == fullcontentModal || 
                event.target == choiceModal) {{
                popModal();
            }}
        }}
    </script>
</body>
</html>
"""

    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Interactive HTML graph with tool usage table written to {out_html}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <filename>")
        sys.exit(1)

    filename = sys.argv[1]
    data = load_graph_json(filename)
    G, subgraphs = build_networkx(data)

    # Use the enhanced HTML creation function
    create_simple_html_graph(G, "llm_graph.html", subgraphs)

    # Open the generated HTML file in the default browser
    # Try to open in browser but handle errors
    try:
        import webbrowser
        import os

        html_path = os.path.abspath("llm_graph.html")
        if os.path.exists(html_path):
            webbrowser.open(html_path)
        else:
            print(f"Could not find generated file: {html_path}")
    except Exception as e:
        print(f"Could not open browser: {e}")


if __name__ == "__main__":
    main()
