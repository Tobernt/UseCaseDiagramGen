import matplotlib.pyplot as plt
import networkx as nx
import gradio as gr
from matplotlib.patches import Ellipse
import math

def adjust_arrow_positions(pos, edge, width=400, height=160):
    """
    Adjusts arrow positions so they start and end at the edges of the ellipses.
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
    """
    temp_text = ax.text(x, y, text, ha="center", va="center", fontsize=font_size, fontweight="bold")
    renderer = ax.figure.canvas.get_renderer()

    while temp_text.get_window_extent(renderer).width > ellipse_width and font_size > min_font_size:
        font_size -= decrement_step
        temp_text.set_fontsize(font_size)

    temp_text.remove()
    ax.text(x, y, text, ha="center", va="center", fontsize=font_size, fontweight="bold")

def calculate_tree_positions(nodes, edges, actor_position="top-center", width=200, height=80, spacing_factor=1.5):
    """
    Calculates tree-based positions for nodes, dynamically placing actors closest to their connected nodes.
    """
    actor_nodes = [node for node in nodes if "<<" in node and ">>" in node]
    non_actor_nodes = [node for node in nodes if node not in actor_nodes]

    # Initialize positions
    pos = {}
    x_spacing = width * spacing_factor
    y_spacing = height * spacing_factor

    tree = nx.DiGraph()
    tree.add_edges_from(edges)

    if actor_position == "top-center":
        # Determine actor placement (top or bottom) based on closest connected nodes
        top_actors = []
        bottom_actors = []

        for actor in actor_nodes:
            connected_nodes = [target for source, target in edges if source == actor]
            avg_y = sum(pos.get(node, (0, 0))[1] for node in connected_nodes if node in pos) / len(connected_nodes) if connected_nodes else 0
            if avg_y >= 0:
                top_actors.append(actor)
            else:
                bottom_actors.append(actor)

        # Place actors at the top
        for i, actor in enumerate(top_actors):
            pos[actor] = (i * x_spacing - (len(top_actors) - 1) * x_spacing / 2, 0)

        # Place actors at the bottom
        for i, actor in enumerate(bottom_actors):
            pos[actor] = (i * x_spacing - (len(bottom_actors) - 1) * x_spacing / 2, -len(non_actor_nodes) * y_spacing)

        # Position non-actor nodes
        levels = {}
        for actor in actor_nodes:
            if actor in tree:
                levels.update(nx.single_source_shortest_path_length(tree, actor))

        grouped_nodes = {}
        for node, level in levels.items():
            if node not in pos:
                grouped_nodes.setdefault(level, []).append(node)

        for level, level_nodes in grouped_nodes.items():
            for i, node in enumerate(level_nodes):
                x = i * x_spacing - (len(level_nodes) - 1) * x_spacing / 2
                y = -level * y_spacing
                pos[node] = (x, y)

    elif actor_position == "center-left":
        # Determine actor placement (left or right) based on closest connected nodes
        left_actors = []
        right_actors = []

        for actor in actor_nodes:
            connected_nodes = [target for source, target in edges if source == actor]
            avg_x = sum(pos.get(node, (0, 0))[0] for node in connected_nodes if node in pos) / len(connected_nodes) if connected_nodes else 0
            if avg_x <= 0:
                left_actors.append(actor)
            else:
                right_actors.append(actor)

        # Place actors on the left
        for i, actor in enumerate(left_actors):
            pos[actor] = (0, -i * y_spacing)

        # Place actors on the right
        for i, actor in enumerate(right_actors):
            pos[actor] = ((len(non_actor_nodes) + 1) * x_spacing, -i * y_spacing)

        # Position non-actor nodes
        levels = {}
        for actor in actor_nodes:
            if actor in tree:
                levels.update(nx.single_source_shortest_path_length(tree, actor))

        grouped_nodes = {}
        for node, level in levels.items():
            if node not in pos:
                grouped_nodes.setdefault(level, []).append(node)

        for level, level_nodes in grouped_nodes.items():
            for i, node in enumerate(level_nodes):
                x = level * x_spacing
                y = -i * y_spacing + (len(level_nodes) - 1) * y_spacing / 2
                pos[node] = (x, y)

    return pos

def generate_use_case_diagram(ascii_description, diagram_title, actor_position="top-center", output_format="png"):
    """
    Generates a use case diagram with support for dashed and solid lines.
    """
    edges = []
    nodes = set()
    edge_styles = {}  # Dictionary to store edge styles

    for line in ascii_description.strip().split("\n"):
        if "-->" in line:  # Dashed line
            source, target = map(str.strip, line.split("-->"))
            edges.append((source, target))
            edge_styles[(source, target)] = "dashed"
            nodes.update([source, target])
        elif "->" in line:  # Solid line
            source, target = map(str.strip, line.split("->"))
            edges.append((source, target))
            edge_styles[(source, target)] = "solid"
            nodes.update([source, target])
        else:
            nodes.add(line.strip())

    ellipse_width = 400  # Ellipse width in pixels
    ellipse_height = 160  # Ellipse height in pixels

    pos = calculate_tree_positions(list(nodes), edges, actor_position=actor_position, width=ellipse_width, height=ellipse_height)

    # Dynamically determine the figure size
    x_positions = [x for x, y in pos.values()]
    y_positions = [y for x, y in pos.values()]
    figure_width = (max(x_positions) - min(x_positions) + 2 * ellipse_width) / 100  # Convert to inches
    figure_height = (max(y_positions) - min(y_positions) + 2 * ellipse_height) / 100  # Convert to inches

    plt.figure(figsize=(figure_width, figure_height), dpi=100)
    ax = plt.gca()

    # Draw the arrows first (behind ellipses)
    for edge in edges:
        if edge[0] in pos and edge[1] in pos:
            # Adjusted positions for line to start and end at ellipse edges
            (start_x, start_y), (end_x, end_y) = adjust_arrow_positions(
                pos, edge, width=ellipse_width, height=ellipse_height
            )
            linestyle = "--" if edge_styles[edge] == "dashed" else "-"
            
            # Draw the line up to the edge of the ellipse
            ax.plot(
                [start_x, end_x],
                [start_y, end_y],
                linestyle=linestyle,
                color="black",
                lw=1.5,
                zorder=1,  # Ensure it is behind ellipses
            )
            
            # Add arrowhead starting exactly at the adjusted `end_x, end_y`
            arrow_dx = end_x - start_x
            arrow_dy = end_y - start_y
            arrow_length = math.sqrt(arrow_dx**2 + arrow_dy**2)

            # Normalize the arrow direction and scale for the arrowhead
            arrow_dx /= arrow_length
            arrow_dy /= arrow_length
            ax.arrow(
                end_x - arrow_dx * 10,  # Move back slightly for better positioning
                end_y - arrow_dy * 10,
                arrow_dx * 10,
                arrow_dy * 10,
                head_width=15,
                head_length=15,
                fc="black",
                ec="black",
                length_includes_head=True,
                zorder=1,
            )


    # Draw the ellipses on top of the arrows
    for node, (x, y) in pos.items():
        display_text = node.replace("<<Actor>> ", "")
        color = "lightgreen" if "<<Actor>>" in node else "lightblue"
        ellipse = Ellipse((x, y), width=ellipse_width, height=ellipse_height, color=color, alpha=0.8, zorder=2)
        ax.add_patch(ellipse)
        fit_text_in_ellipse(ax, display_text, x, y, ellipse_width)

    plt.title(diagram_title or "Use Case Diagram", fontsize=18, fontweight="bold")
    plt.axis("off")

    ax.set_xlim(min(x_positions) - ellipse_width, max(x_positions) + ellipse_width)
    ax.set_ylim(min(y_positions) - ellipse_height, max(y_positions) + ellipse_height)

    output_file = f"use_case_diagram.{output_format}"
    plt.savefig(output_file, format=output_format, bbox_inches="tight")
    plt.close()

    return output_file


# Gradio UI
user_guide = """
# Use Case Diagram Guide
**Instructions for Input**:
- Use `<<Actor>>` to define actors.
- Define relationships using `->` for solid lines.
- Use `-->` to define relationships with dashed lines.
- Example:
- `<<Actor>>` User `->` Click
- Click `-->` Starts
"""

with gr.Blocks() as app:
    with gr.Tab("Diagram Generator"):
        gr.Markdown("# Use Case Diagram Generator")
        ascii_input = gr.TextArea(label="ASCII Input", lines=15, placeholder="<<Actor>> User -> Click\nClick --> Starts")
        diagram_title = gr.Textbox(label="Diagram Title", placeholder="Optional Title")
        actor_position = gr.Radio(["top-center", "center-left"], label="Actor Layout", value="top-center")
        format_choice = gr.Radio(["png", "pdf"], label="Output Format", value="png")
        generate_button = gr.Button("Generate Diagram")
        output_file = gr.File(label="Download Diagram")

        generate_button.click(
            generate_use_case_diagram,
            inputs=[ascii_input, diagram_title, actor_position, format_choice],
            outputs=output_file,
        )

    with gr.Tab("Guide"):
        gr.Markdown(user_guide)

app.launch()
