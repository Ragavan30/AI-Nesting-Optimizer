import numpy as np
from shapely.geometry import Point, Polygon
from shapely.geometry import box as Box

def create_part_from_dict(part_info):
    """Create a Shapely geometry object from part information"""
    part_type = part_info['type'].lower()
    
    if part_type == 'rectangle':
        width = part_info['width']
        height = part_info['height']
        # Create rectangle centered at origin
        return Box(-width/2, -height/2, width/2, height/2)
    
    elif part_type == 'circle':
        radius = part_info['radius']
        # Create circle as polygon with many sides
        angles = np.linspace(0, 2*np.pi, 32, endpoint=False)
        points = [(radius * np.cos(a), radius * np.sin(a)) for a in angles]
        return Polygon(points)
    
    elif part_type == 'triangle':
        base = part_info['base']
        height = part_info['height']
        # Create triangle centered at origin
        points = [
            (-base/2, -height/3),  # Bottom left
            (base/2, -height/3),   # Bottom right
            (0, 2*height/3)        # Top
        ]
        return Polygon(points)
    
    else:
        raise ValueError(f"Unsupported part type: {part_type}")

def get_part_bounds(part_info):
    """Get bounding box dimensions for a part"""
    part_type = part_info['type'].lower()
    
    if part_type == 'rectangle':
        return part_info['width'], part_info['height']
    
    elif part_type == 'circle':
        radius = part_info['radius']
        return 2 * radius, 2 * radius
    
    elif part_type == 'triangle':
        base = part_info['base']
        height = part_info['height']
        return base, height
    
    else:
        raise ValueError(f"Unsupported part type: {part_type}")

def calculate_part_area(part_info):
    """Calculate the area of a part"""
    part_type = part_info['type'].lower()
    
    if part_type == 'rectangle':
        return part_info['width'] * part_info['height']
    
    elif part_type == 'circle':
        radius = part_info['radius']
        return np.pi * radius * radius
    
    elif part_type == 'triangle':
        base = part_info['base']
        height = part_info['height']
        return 0.5 * base * height
    
    else:
        raise ValueError(f"Unsupported part type: {part_type}")

def check_part_fits_sheet(part_info, sheet_width, sheet_height):
    """Check if a part can physically fit within sheet dimensions"""
    width, height = get_part_bounds(part_info)
    return width <= sheet_width and height <= sheet_height

def rotate_point(x, y, angle, cx=0, cy=0):
    """Rotate a point around a center"""
    cos_angle = np.cos(angle)
    sin_angle = np.sin(angle)
    
    # Translate to origin
    x -= cx
    y -= cy
    
    # Rotate
    new_x = x * cos_angle - y * sin_angle
    new_y = x * sin_angle + y * cos_angle
    
    # Translate back
    new_x += cx
    new_y += cy
    
    return new_x, new_y

def generate_part_variants(part_info, num_rotations=4):
    """Generate rotated variants of a part for better optimization"""
    variants = []
    
    for i in range(num_rotations):
        angle = (2 * np.pi * i) / num_rotations
        variant = part_info.copy()
        variant['rotation'] = angle
        variants.append(variant)
    
    return variants

def optimize_part_orientation(part_info, sheet_width, sheet_height):
    """Find the best orientation for a part to fit in the sheet"""
    part_type = part_info['type'].lower()
    
    if part_type == 'rectangle':
        width = part_info['width']
        height = part_info['height']
        
        # Try both orientations
        if width <= sheet_width and height <= sheet_height:
            if height <= sheet_width and width <= sheet_height:
                # Both orientations fit, choose the one that minimizes wasted space
                waste1 = (sheet_width - width) * (sheet_height - height)
                waste2 = (sheet_width - height) * (sheet_height - width)
                return 0 if waste1 <= waste2 else np.pi/2
            else:
                return 0  # Original orientation
        elif height <= sheet_width and width <= sheet_height:
            return np.pi/2  # Rotated 90 degrees
        else:
            return None  # Doesn't fit in either orientation
    
    elif part_type == 'circle':
        # Circles are rotationally symmetric
        radius = part_info['radius']
        if 2 * radius <= min(sheet_width, sheet_height):
            return 0
        else:
            return None
    
    elif part_type == 'triangle':
        base = part_info['base']
        height = part_info['height']
        
        # Try multiple orientations
        orientations = [0, np.pi/3, 2*np.pi/3, np.pi, 4*np.pi/3, 5*np.pi/3]
        valid_orientations = []
        
        for angle in orientations:
            # Approximate bounding box after rotation
            # This is a simplified check
            if base <= sheet_width and height <= sheet_height:
                valid_orientations.append(angle)
        
        return valid_orientations[0] if valid_orientations else None
    
    return 0  # Default orientation
