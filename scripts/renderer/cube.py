class IsometricCube:
    """
    Computes coordinate paths for an isometric 3D building column.
    Generates paths for the Top, Left, Right faces, ambient shadows,
    and glass floor reflections.
    """
    def __init__(self, col, row, count, height_val, projector, fill_factor=0.82):
        self.col = col
        self.row = row
        self.count = count
        self.height_val = height_val
        self.projector = projector
        self.fill_factor = fill_factor

        # Determine limits in 3D grid space
        offset = (1.0 - self.fill_factor) / 2.0
        self.c_min = col + offset
        self.c_max = col + 1 - offset
        self.r_min = row + offset
        self.r_max = row + 1 - offset

    def get_face_paths(self):
        """
        Calculates screen coordinate paths for Top, Left, and Right faces.
        Returns a dictionary of SVG path string coordinates.
        """
        # Ground corners (z = 0)
        p_back_b = self.projector.project(self.c_min, self.r_min, 0)
        p_left_b = self.projector.project(self.c_min, self.r_max, 0)
        p_front_b = self.projector.project(self.c_max, self.r_max, 0)
        p_right_b = self.projector.project(self.c_max, self.r_min, 0)

        # Top corners (z = height_val)
        p_back_t = self.projector.project(self.c_min, self.r_min, self.height_val)
        p_left_t = self.projector.project(self.c_min, self.r_max, self.height_val)
        p_front_t = self.projector.project(self.c_max, self.r_max, self.height_val)
        p_right_t = self.projector.project(self.c_max, self.r_min, self.height_val)

        # Build SVG path strings
        top_path = f"M {p_back_t[0]},{p_back_t[1]} L {p_left_t[0]},{p_left_t[1]} L {p_front_t[0]},{p_front_t[1]} L {p_right_t[0]},{p_right_t[1]} Z"
        left_path = f"M {p_left_b[0]},{p_left_b[1]} L {p_left_t[0]},{p_left_t[1]} L {p_front_t[0]},{p_front_t[1]} L {p_front_b[0]},{p_front_b[1]} Z"
        right_path = f"M {p_front_b[0]},{p_front_b[1]} L {p_front_t[0]},{p_front_t[1]} L {p_right_t[0]},{p_right_t[1]} L {p_right_b[0]},{p_right_b[1]} Z"

        return {
            "top": top_path,
            "left": left_path,
            "right": right_path,
            "top_pts": [p_back_t, p_left_t, p_front_t, p_right_t],
            "front_pt": p_front_t
        }

    def get_reflection_paths(self, scale=0.45):
        """
        Calculates mirrored face paths extending in the negative z direction.
        Used to render translucent glass floor reflections.
        """
        ref_h = self.height_val * scale
        
        p_back_b = self.projector.project(self.c_min, self.r_min, 0)
        p_left_b = self.projector.project(self.c_min, self.r_max, 0)
        p_front_b = self.projector.project(self.c_max, self.r_max, 0)
        p_right_b = self.projector.project(self.c_max, self.r_min, 0)

        # Reflection bottoms (z = -ref_h)
        p_back_r = self.projector.project(self.c_min, self.r_min, -ref_h)
        p_left_r = self.projector.project(self.c_min, self.r_max, -ref_h)
        p_front_r = self.projector.project(self.c_max, self.r_max, -ref_h)
        p_right_r = self.projector.project(self.c_max, self.r_min, -ref_h)

        # Reflection faces (projecting down)
        left_ref = f"M {p_left_b[0]},{p_left_b[1]} L {p_left_r[0]},{p_left_r[1]} L {p_front_r[0]},{p_front_r[1]} L {p_front_b[0]},{p_front_b[1]} Z"
        right_ref = f"M {p_front_b[0]},{p_front_b[1]} L {p_front_r[0]},{p_front_r[1]} L {p_right_r[0]},{p_right_r[1]} L {p_right_b[0]},{p_right_b[1]} Z"
        top_ref = f"M {p_back_r[0]},{p_back_r[1]} L {p_left_r[0]},{p_left_r[1]} L {p_front_r[0]},{p_front_r[1]} L {p_right_r[0]},{p_right_r[1]} Z"

        return {
            "top": top_ref,
            "left": left_ref,
            "right": right_ref
        }

    def get_shadow_path(self, shadow_offset=3.0):
        """
        Calculates a flat floor polygon path, offset slightly,
        used for ambient drop-shadow underneath the building base.
        """
        p_back = self.projector.project(self.c_min, self.r_min, 0)
        p_left = self.projector.project(self.c_min, self.r_max, 0)
        p_front = self.projector.project(self.c_max, self.r_max, 0)
        p_right = self.projector.project(self.c_max, self.r_min, 0)

        # Shift shadow downwards slightly on screen
        s_back = (p_back[0], p_back[1] + shadow_offset)
        s_left = (p_left[0], p_left[1] + shadow_offset)
        s_front = (p_front[0], p_front[1] + shadow_offset)
        s_right = (p_right[0], p_right[1] + shadow_offset)

        return f"M {s_back[0]},{s_back[1]} L {s_left[0]},{s_left[1]} L {s_front[0]},{s_front[1]} L {s_right[0]},{s_right[1]} Z"
