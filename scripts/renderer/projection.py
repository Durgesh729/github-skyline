import math

class IsometricProjector:
    """
    Handles isometric math mapping coordinates in a 3D grid (col, row, height)
    to 2D SVG canvas space coordinates (x, y) with customizable angles and spacing.
    """
    def __init__(self, width=1200, height=800, grid_spacing=20, perspective_angle=30, height_scale=15.0):
        self.width = width
        self.height = height
        self.grid_spacing = grid_spacing
        self.angle_rad = math.radians(perspective_angle)
        self.height_scale = height_scale
        
        # Precompute trigonometric factors
        self.cos_a = math.cos(self.angle_rad)
        self.sin_a = math.sin(self.angle_rad)
        
        # Calculate grid boundaries to center the skyline
        # Grid dimensions: 53 weeks (columns) x 7 days (rows)
        self.cols_count = 53
        self.rows_count = 7
        
        # Grid bounds in isometric space
        min_iso_x = (0 - self.rows_count) * self.grid_spacing * self.cos_a
        max_iso_x = (self.cols_count - 0) * self.grid_spacing * self.cos_a
        min_iso_y = 0
        max_iso_y = (self.cols_count + self.rows_count) * self.grid_spacing * self.sin_a
        
        # Calculate centers
        iso_width = max_iso_x - min_iso_x
        iso_height = max_iso_y - min_iso_y
        
        self.center_x = (self.width - iso_width) / 2 - min_iso_x
        self.center_y = (self.height - iso_height) / 2 + 50  # Give a slight offset downwards for skyline height room

    def project(self, col, row, z=0.0):
        """
        Projects a 3D point (col, row, z) where z is height to 2D screen (x, y).
        - col: week index (0 to 52)
        - row: day index (0 to 6)
        - z: height value (contribution count * scale)
        """
        # Calculate isometric 2D coordinates before translation
        iso_x = (col - row) * self.grid_spacing * self.cos_a
        iso_y = (col + row) * self.grid_spacing * self.sin_a
        
        # Translate to center of canvas and apply height offset
        screen_x = self.center_x + iso_x
        screen_y = self.center_y + iso_y - z
        
        return round(screen_x, 2), round(screen_y, 2)
