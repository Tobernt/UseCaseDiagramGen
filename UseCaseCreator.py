import matplotlib.pyplot as plt
import networkx as nx
import gradio as gr
from matplotlib.patches import Ellipse
import math


def adjust_arrow_positions(pos, edge, width=2.5, height=1.0):
    """
    Adjusts arrow positions so they start and end at the edges of the ellipses.

    Args:
        pos (dict): Node positions.
        edge (tuple): Edge as (source, target).
        width (float): Width of the ellipse.
        height (float): Height of the ellipse.

    Returns:
        tuple: Adjusted positions for arrow start and end.
    """
    x1, y1 = pos[edge[0]]  # Source position
    x2, y2 = pos[edge[1]]  # Target position

    # Compute angle of the line connecting source and target
    angle = math.atan2(y2 - y1, x2 - x1)

    # Adjust positions to the edge of the ellipses
    x1_adjusted = x1 + (width / 2) * math.cos(angle)
    y1_adjusted = y1 + (height / 2) * math.sin(angle)

    x2_adjusted = x2 - (width / 2) * math.cos(angle)
    y2_adjusted = y2 - (height / 2) * math.sin(angle)

    return (x1_adjusted, y1_adjusted), (x2_adjusted, y2_adjusted)


def fit_text_in_ellipse(ax, text, x, y, ellipse_width, font_size=12, min_font_size=8, decrement_step=0.5):
    """
    Dynamically scales the font size to fit the text within the ellipse.

    Args:
        ax (matplotlib.axes.Axes): The matplotlib axis to draw on.
        text (str): The text to fit.
        x (float): The x-coordinate of the ellipse center.
        y (float): The y-coordinate of the ellipse center.
        ellipse_width (float): The width of the ellipse.
        font_size (int): Initial font size.
        min_font_size (int): Minimum font size to prevent excessive shrinking.
        decrement_step (float): Step by which the font size is reduced during fitting.

    Returns:
        None
    """
    # Create a temporary text artist
    temp_text = ax.text(x, y, text, ha="center", va="center", fontsize=font_size, fontweight="bold")
    renderer = ax.figure.canvas.get_renderer()

    while temp_text.get_window_extent(renderer).width > ellipse_width * ax.figure.dpi / 2 and font_size > min_font_size:
        # Reduce font size by a smaller decrement step
        font_size -= decrement_step
        temp_text.set_fontsize(font_size)

    # Remove the temporary text artist
    temp_text.remove()

    # Draw the final text with the adjusted font size
    ax.text(x, y, text, ha="center", va="center", fontsize=font_size, fontweight="bold")


def calculate_tree_positions(nodes, edges, actor_position="top-center", width=2.5, height=1.0, spacing_factor=2.0):
    """
    Calculates tree-based positions for nodes, ensuring no duplication and proper actor placement.

    Args:
        nodes (list): List of nodes.
        edges (list): List of edges.
        actor_position (str): Actor position for tree layout ('top-center' or 'center-left').
        width (float): Width of the ellipses.
        height (float): Height of the ellipses.
        spacing_factor (float): Multiplier for spacing.

    Returns:
        dict: Node positions.
    """
    # Identify unique actor nodes
    actor_nodes = [node for node in nodes if "<<" in node and ">>" in node]
    non_actor_nodes = [node for node in nodes if node not in actor_nodes]

    # Initialize positions
    pos = {}

    # Place actors at the top or left
    x_spacing = width * spacing_factor
    y_spacing = height * spacing_factor

    if actor_position == "top-center":
        # Position actors side by side at the top
        for i, actor in enumerate(sorted(actor_nodes)):
            pos[actor] = (i * x_spacing - (len(actor_nodes) - 1) * x_spacing / 2, 0)

        # Create a directed graph and compute levels for non-actor nodes
        tree = nx.DiGraph()
        tree.add_edges_from(edges)
        levels = {}
        for actor in actor_nodes:
            if actor in tree:
                levels.update(nx.single_source_shortest_path_length(tree, actor))

        # Group nodes by levels
        grouped_nodes = {}
        for node, level in levels.items():
            if node not in pos:  # Skip already-positioned actor nodes
                grouped_nodes.setdefault(level, []).append(node)

        # Position non-actor nodes by levels
        for level, level_nodes in grouped_nodes.items():
            for i, node in enumerate(level_nodes):
                x = i * x_spacing - (len(level_nodes) - 1) * x_spacing / 2
                y = -level * y_spacing
                pos[node] = (x, y)

    elif actor_position == "center-left":
        # Position actors vertically on the left
        for i, actor in enumerate(sorted(actor_nodes)):
            pos[actor] = (0, -i * y_spacing)

        # Create a directed graph and compute levels for non-actor nodes
        tree = nx.DiGraph()
        tree.add_edges_from(edges)
        levels = {}
        for actor in actor_nodes:
            if actor in tree:
                levels.update(nx.single_source_shortest_path_length(tree, actor))

        # Group nodes by levels
        grouped_nodes = {}
        for node, level in levels.items():
            if node not in pos:  # Skip already-positioned actor nodes
                grouped_nodes.setdefault(level, []).append(node)

        # Position non-actor nodes by levels
        for level, level_nodes in grouped_nodes.items():
            for i, node in enumerate(level_nodes):
                x = level * x_spacing
                y = -i * y_spacing + (len(level_nodes) - 1) * y_spacing / 2
                pos[node] = (x, y)

    return pos


def generate_use_case_diagram(ascii_description, diagram_title, actor_position="top-center", output_format="png"):
    """
    Generates a clean and structured use case diagram with support for multiple actors and a custom title.

    Args:
        ascii_description (str): ASCII description of the use case diagram.
        diagram_title (str): Title of the use case diagram.
        actor_position (str): Actor position for tree layout ('top-center' or 'center-left').
        output_format (str): Output file format ('png' or 'pdf').

    Returns:
        str: Path to the generated diagram file.
    """
    # Parse ASCII input
    edges = []
    nodes = set()
    for line in ascii_description.strip().split("\n"):
        if "->" in line:
            source, target = map(str.strip, line.split("->"))
            edges.append((source, target))
            nodes.update([source, target])
        else:
            nodes.add(line.strip())

    # Determine positions
    pos = calculate_tree_positions(list(nodes), edges, actor_position=actor_position)

    # Draw the graph structure (edges only)
    plt.figure(figsize=(18, 12))  # Increased figure size
    ax = plt.gca()

    # Draw ellipses for nodes
    ellipse_width = 2.5
    for node, (x, y) in pos.items():
        # Remove "<<Actor>>" and adjust node color
        display_text = node.replace("<<Actor>> ", "")
        color = "lightgreen" if "<<Actor>>" in node else "lightblue"
        ellipse = Ellipse((x, y), width=ellipse_width, height=ellipse_width / 2, color=color, alpha=0.8)
        ax.add_patch(ellipse)
        fit_text_in_ellipse(ax, display_text, x, y, ellipse_width)

    # Draw arrows with adjusted positions
    for edge in edges:
        if edge[0] in pos and edge[1] in pos:  # Ensure both nodes exist in pos
            (start_x, start_y), (end_x, end_y) = adjust_arrow_positions(
                pos, edge, width=ellipse_width, height=ellipse_width / 2
            )
            ax.annotate(
                "",
                xy=(end_x, end_y),
                xytext=(start_x, start_y),
                arrowprops=dict(arrowstyle="->", color="black", lw=1.5),
            )

    # Add title
    plt.title(diagram_title or "Use Case Diagram", fontsize=18, fontweight="bold")
    plt.axis("off")

    # Set axis limits dynamically to fit all nodes and ellipses
    x_values = [x for x, y in pos.values()]
    y_values = [y for x, y in pos.values()]
    ax.set_xlim(min(x_values) - ellipse_width, max(x_values) + ellipse_width)
    ax.set_ylim(min(y_values) - ellipse_width, max(y_values) + ellipse_width)

    # Save diagram
    output_file = f"use_case_diagram.{output_format}"
    plt.savefig(output_file, format=output_format, bbox_inches="tight")
    plt.close()

    return output_file


def generate_diagram_ui(ascii_input, diagram_title, actor_position, format_choice):
    """
    Wrapper function for Gradio interface.

    Args:
        ascii_input (str): ASCII input for the use case diagram.
        diagram_title (str): Title of the diagram.
        actor_position (str): Actor position ('top-center' or 'center-left').
        format_choice (str): Chosen format for output ('png' or 'pdf').

    Returns:
        str: Path to the generated diagram file.
    """
    file_path = generate_use_case_diagram(
        ascii_input, diagram_title=diagram_title, actor_position=actor_position, output_format=format_choice
    )
    return file_path


# Example ASCII description
example_ascii = """
<<Actor>> Customer -> Browse Products
<<Actor>> Customer -> Place Order
Browse Products -> Add to Cart
Add to Cart -> Place Order
Place Order -> Payment
Payment -> Generate Invoice
Generate Invoice -> Send Confirmation
"""

user_guide = """
# Use Case Diagram Guide
**Instructions for Input**:
1. **Actor**: Start the actor nodes with `<<Actor>>`. Example: `<<Actor>> Customer`.
2. **Use Cases**: Connect use cases with `->` to define relationships. Example: `Browse Products -> Add to Cart`.
3. **Multiple Actors**: Define multiple actors with their use cases.

**Layout Options**:
- **Top-Center**: Actor is at the top, with use cases branching downward.
- **Center-Left**: Actor is at the left, with use cases branching to the right.

**Output Options**:
- Choose between PNG or PDF format.
"""

# Gradio UI
with gr.Blocks() as app:
    with gr.Tab("Diagram Generator"):
        gr.Markdown("# Use Case Diagram Generator")
        gr.Markdown("Enter an ASCII description of your use case diagram:")
        ascii_input = gr.TextArea(label="ASCII Use Case Diagram", value=example_ascii, lines=15)
        diagram_title = gr.Textbox(label="Diagram Title", placeholder="Enter the title of your diagram (optional)")
        actor_position = gr.Radio(["top-center", "center-left"], label="Actor Position (Tree Layout)", value="top-center")
        format_choice = gr.Radio(["png", "pdf"], label="Output Format", value="png")
        generate_button = gr.Button("Generate Diagram")
        output_file = gr.File(label="Download Diagram")

        generate_button.click(
            generate_diagram_ui,
            inputs=[ascii_input, diagram_title, actor_position, format_choice],
            outputs=output_file,
        )

    with gr.Tab("Guide"):
        gr.Markdown(user_guide)

# Launch the app
app.launch()
