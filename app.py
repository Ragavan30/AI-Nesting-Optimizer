import streamlit as st
import pandas as pd
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Polygon as MplPolygon
import numpy as np
from nesting_optimizer import NestingOptimizer
from geometry_utils import create_part_from_dict
import io

def main():
    st.set_page_config(
        page_title="AI-Powered Sheet Nesting Optimizer",
        page_icon="🔧",
        layout="wide"
    )
    
    st.title("🔧 AI-Powered Sheet Nesting Optimizer")
    st.markdown("*Optimize sheet metal cutting layouts using Genetic Algorithms*")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # Sheet dimensions
        st.subheader("Sheet Dimensions (mm)")
        sheet_width = st.number_input("Width", value=2000, min_value=100, max_value=5000)
        sheet_height = st.number_input("Height", value=1000, min_value=100, max_value=3000)
        
        # Optimization parameters
        st.subheader("Optimization Settings")
        population_size = st.slider("Population Size", 20, 100, 50)
        generations = st.slider("Generations", 10, 100, 30)
        mutation_rate = st.slider("Mutation Rate", 0.01, 0.3, 0.1)
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("Part Input")
        
        # Input method selection
        input_method = st.radio("Choose input method:", ["Upload JSON/CSV", "Manual Entry", "Use Sample Data"])
        
        parts_data = []
        
        if input_method == "Upload JSON/CSV":
            uploaded_file = st.file_uploader("Upload parts file", type=['json', 'csv'])
            
            if uploaded_file is not None:
                try:
                    if uploaded_file.name.endswith('.json'):
                        parts_data = json.load(uploaded_file)
                    else:
                        df = pd.read_csv(uploaded_file)
                        parts_data = df.to_dict('records')
                    
                    st.success(f"Loaded {len(parts_data)} parts")
                    st.dataframe(pd.DataFrame(parts_data))
                    
                except Exception as e:
                    st.error(f"Error loading file: {str(e)}")
        
        elif input_method == "Manual Entry":
            st.subheader("Add Parts Manually")
            
            with st.form("add_part_form"):
                col_a, col_b = st.columns(2)
                
                with col_a:
                    part_type = st.selectbox("Shape", ["rectangle", "circle", "triangle"])
                    part_id = st.text_input("Part ID", value=f"part_{len(st.session_state.get('manual_parts', []))+1}")
                
                with col_b:
                    quantity = st.number_input("Quantity", min_value=1, max_value=100, value=1)
                
                # Shape-specific parameters
                part_params = {}
                if part_type == "rectangle":
                    width = st.number_input("Width (mm)", min_value=1.0, value=100.0)
                    height = st.number_input("Height (mm)", min_value=1.0, value=50.0)
                    part_params = {"width": width, "height": height}
                
                elif part_type == "circle":
                    radius = st.number_input("Radius (mm)", min_value=1.0, value=25.0)
                    part_params = {"radius": radius}
                
                elif part_type == "triangle":
                    base = st.number_input("Base (mm)", min_value=1.0, value=60.0)
                    height = st.number_input("Height (mm)", min_value=1.0, value=40.0)
                    part_params = {"base": base, "height": height}
                
                if st.form_submit_button("Add Part"):
                    if 'manual_parts' not in st.session_state:
                        st.session_state.manual_parts = []
                    
                    new_part = {
                        "id": part_id,
                        "type": part_type,
                        "quantity": quantity,
                        **part_params
                    }
                    st.session_state.manual_parts.append(new_part)
                    st.success("Part added!")
                    st.rerun()
            
            if 'manual_parts' in st.session_state and st.session_state.manual_parts:
                parts_data = st.session_state.manual_parts
                st.subheader("Added Parts")
                st.dataframe(pd.DataFrame(parts_data))
                
                if st.button("Clear All Parts"):
                    st.session_state.manual_parts = []
                    st.rerun()
        
        elif input_method == "Use Sample Data":
            with open('sample_parts.json', 'r') as f:
                parts_data = json.load(f)
            
            st.success(f"Loaded {len(parts_data)} sample parts")
            st.dataframe(pd.DataFrame(parts_data))
    
    with col2:
        st.header("Optimization Results")
        
        if parts_data and st.button("🚀 Optimize Nesting", type="primary"):
            with st.spinner("Running optimization..."):
                try:
                    # Initialize optimizer
                    optimizer = NestingOptimizer(
                        sheet_width=sheet_width,
                        sheet_height=sheet_height,
                        population_size=population_size,
                        generations=generations,
                        mutation_rate=mutation_rate
                    )
                    
                    # Run optimization
                    best_layout, stats = optimizer.optimize(parts_data)
                    
                    # Display results
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        st.metric("Material Utilization", f"{stats['utilization']:.1f}%")
                        st.metric("Parts Placed", f"{stats['parts_placed']}/{stats['total_parts']}")
                    
                    with col_b:
                        st.metric("Waste Area", f"{stats['waste_area']:.0f} mm²")
                        st.metric("Sheet Area", f"{stats['sheet_area']:.0f} mm²")
                    
                    # Create visualization
                    fig = create_nesting_visualization(best_layout, sheet_width, sheet_height, parts_data)
                    st.pyplot(fig)
                    
                    # Show comparison with random placement
                    st.subheader("Comparison: Random vs Optimized")
                    random_layout, random_stats = optimizer.create_random_layout(parts_data)
                    
                    col_c, col_d = st.columns(2)
                    
                    with col_c:
                        st.markdown("**Random Placement**")
                        st.metric("Utilization", f"{random_stats['utilization']:.1f}%")
                        fig_random = create_nesting_visualization(random_layout, sheet_width, sheet_height, parts_data, title="Random Placement")
                        st.pyplot(fig_random)
                    
                    with col_d:
                        st.markdown("**AI-Optimized Placement**")
                        improvement = stats['utilization'] - random_stats['utilization']
                        st.metric("Utilization", f"{stats['utilization']:.1f}%", f"+{improvement:.1f}%")
                        fig_opt = create_nesting_visualization(best_layout, sheet_width, sheet_height, parts_data, title="AI-Optimized Placement")
                        st.pyplot(fig_opt)
                    
                    # Performance metrics
                    st.subheader("Optimization Performance")
                    improvement_pct = (improvement / random_stats['utilization']) * 100 if random_stats['utilization'] > 0 else 0
                    
                    metrics_df = pd.DataFrame({
                        'Metric': ['Material Utilization', 'Waste Reduction', 'Parts Placed', 'Optimization Time'],
                        'Random': [f"{random_stats['utilization']:.1f}%", 
                                  f"{100 - random_stats['utilization']:.1f}%",
                                  f"{random_stats['parts_placed']}/{random_stats['total_parts']}",
                                  "N/A"],
                        'AI-Optimized': [f"{stats['utilization']:.1f}%",
                                        f"{100 - stats['utilization']:.1f}%", 
                                        f"{stats['parts_placed']}/{stats['total_parts']}",
                                        f"{stats.get('optimization_time', 0):.2f}s"],
                        'Improvement': [f"+{improvement:.1f}%",
                                       f"-{improvement:.1f}%",
                                       f"+{stats['parts_placed'] - random_stats['parts_placed']}",
                                       f"{improvement_pct:.1f}% better"]
                    })
                    
                    st.dataframe(metrics_df, hide_index=True)
                    
                except Exception as e:
                    st.error(f"Optimization failed: {str(e)}")
                    st.exception(e)
        
        elif not parts_data:
            st.info("Please add parts to begin optimization")

def create_nesting_visualization(layout, sheet_width, sheet_height, parts_data, title="Nesting Layout"):
    """Create matplotlib visualization of the nesting layout"""
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    
    # Draw sheet boundary
    sheet_rect = patches.Rectangle((0, 0), sheet_width, sheet_height, 
                                  linewidth=2, edgecolor='black', facecolor='lightgray', alpha=0.3)
    ax.add_patch(sheet_rect)
    
    # Color map for different part types
    colors = {'rectangle': 'lightblue', 'circle': 'lightgreen', 'triangle': 'lightsalmon'}
    
    # Draw placed parts
    for i, (part_info, x, y, rotation) in enumerate(layout):
        part_type = part_info['type']
        color = colors.get(part_type, 'lightgray')
        
        if part_type == 'rectangle':
            width = part_info['width']
            height = part_info['height']
            
            # Create rotated rectangle
            rect = patches.Rectangle((x - width/2, y - height/2), width, height,
                                   angle=np.degrees(rotation), rotation_point='center',
                                   facecolor=color, edgecolor='darkblue', alpha=0.7)
            ax.add_patch(rect)
            
        elif part_type == 'circle':
            radius = part_info['radius']
            circle = patches.Circle((x, y), radius, facecolor=color, 
                                  edgecolor='darkgreen', alpha=0.7)
            ax.add_patch(circle)
            
        elif part_type == 'triangle':
            base = part_info['base']
            height = part_info['height']
            
            # Create triangle vertices
            vertices = np.array([
                [-base/2, -height/3],
                [base/2, -height/3],
                [0, 2*height/3]
            ])
            
            # Apply rotation
            cos_r, sin_r = np.cos(rotation), np.sin(rotation)
            rotation_matrix = np.array([[cos_r, -sin_r], [sin_r, cos_r]])
            rotated_vertices = vertices @ rotation_matrix.T
            
            # Translate to position
            rotated_vertices += [x, y]
            
            triangle = MplPolygon(rotated_vertices, facecolor=color, 
                                edgecolor='darkred', alpha=0.7)
            ax.add_patch(triangle)
        
        # Add part label
        ax.text(x, y, f"{part_info['id']}", ha='center', va='center', 
               fontsize=8, weight='bold')
    
    ax.set_xlim(-50, sheet_width + 50)
    ax.set_ylim(-50, sheet_height + 50)
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.set_xlabel('Width (mm)')
    ax.set_ylabel('Height (mm)')
    ax.set_title(title, fontsize=14, weight='bold')
    
    plt.tight_layout()
    return fig

if __name__ == "__main__":
    main()
