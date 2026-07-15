import pytest
from scripts.renderer.projection import IsometricProjector
from scripts.renderer.cube import IsometricCube

def test_isometric_projection_scaling():
    projector = IsometricProjector(width=1000, height=800, grid_spacing=20, perspective_angle=30, height_scale=10.0)
    
    # Back corner (0, 0, 0)
    x0, y0 = projector.project(0, 0, 0)
    
    # Moving along columns (col=1, row=0, z=0) should move down-right
    x1, y1 = projector.project(1, 0, 0)
    assert x1 > x0
    assert y1 > y0
    
    # Moving along rows (col=0, row=1, z=0) should move down-left
    x2, y2 = projector.project(0, 1, 0)
    assert x2 < x0
    assert y2 > y0

    # Moving upwards (col=0, row=0, z=50) should move vertically straight up (y decreases)
    x3, y3 = projector.project(0, 0, 50)
    assert x3 == x0
    assert y3 < y0

def test_isometric_cube_paths():
    projector = IsometricProjector(width=1000, height=800, grid_spacing=20)
    cube = IsometricCube(col=5, row=3, count=4, height_val=40, projector=projector)
    
    paths = cube.get_face_paths()
    assert "top" in paths
    assert "left" in paths
    assert "right" in paths
    
    # Verifying they are closed SVG paths (start with M, contain L, end with Z)
    for face in ["top", "left", "right"]:
        path_str = paths[face]
        assert path_str.startswith("M")
        assert "L" in path_str
        assert path_str.endswith("Z")

def test_depth_sorting():
    # Verify back-to-front rendering sorting key: col + row
    blocks = [
        {"col": 10, "row": 5},
        {"col": 0, "row": 0},
        {"col": 5, "row": 3},
        {"col": 1, "row": 1}
    ]
    
    sorted_blocks = sorted(blocks, key=lambda b: (b["col"] + b["row"]))
    
    # Expect order: (0,0) -> (1,1) -> (5,3) -> (10,5)
    assert sorted_blocks[0] == {"col": 0, "row": 0}
    assert sorted_blocks[1] == {"col": 1, "row": 1}
    assert sorted_blocks[2] == {"col": 5, "row": 3}
    assert sorted_blocks[3] == {"col": 10, "row": 5}

def test_animation_manager():
    from scripts.renderer.animator import SVGAnimationManager
    from scripts.renderer.theme import Theme
    
    theme = Theme({
        "building": {"glow_color": "#00f0ff", "stroke": "#3366ff", "neon_glow": True},
        "text": {"accent_color": "#ff00ff"},
        "effects": {"scanline": True}
    })
    
    anim_settings = {"enabled": True, "duration_seconds": 3.0, "delay_increment_seconds": 0.05, "pulse_glow": True, "scanline": True}
    
    animator = SVGAnimationManager(anim_settings, theme)
    style = animator.get_style_section()
    
    assert "@keyframes rise-up" in style
    assert "@keyframes glow-pulse" in style
    assert "@keyframes laser-sweep" in style
    
    attrs = animator.get_column_style_attrs(col=5, row=5, base_x=120, base_y=240)
    assert 'class="building-group"' in attrs
    assert 'animation-delay: 0.5s' in attrs # (5+5) * 0.05 = 0.5

