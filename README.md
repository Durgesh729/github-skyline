# 🌌 GitHub Skyline Hub

[![Generate GitHub Skyline](https://github.com/Durgesh729/github-skyline/actions/workflows/skyline.yml/badge.svg)](https://github.com/Durgesh729/github-skyline/actions/workflows/skyline.yml)
[![GitHub license](https://img.shields.type/github/license/Durgesh729/github-skyline?color=cyan)](LICENSE)

A production-grade, highly automated, and visually stunning contribution graph visualizer. It generates retro-cybernetic, isometric 3D skyline vectors of your GitHub contributions, updates daily, integrates directly into your GitHub Profile README, and hosts a web dashboard with pan-and-zoom controls and image exports.

<div align="center">
  <img src="assets/skyline-animated.svg" alt="GitHub Skyline Animated Overview" width="800" style="max-width:100%;" />
  <p><i>Live cyberpunk-themed animated contribution skyline for the current year.</i></p>
</div>

---

## 🚀 Live Interactive Dashboard
Explore the contribution history, pan/zoom vectors, select target years, and export files directly on the web:
👉 **[Explore Interactive Skyline Hub](https://Durgesh729.github.io/github-skyline/)**

---

## 🛠️ System Architecture & Folder Layout

The project separates data queries, statistical compilation, mathematical projections, theme overrides, and CSS animations.

```text
github-skyline/
├── .github/workflows/
│   └── skyline.yml         # Daily & manual GHA schedules
├── assets/
│   ├── skyline-current.svg # Static current year skyline
│   ├── skyline-animated.svg# CSS-animated current year skyline
│   ├── skyline-all.svg     # Cumulative all-years compilation
│   └── skyline-2025.svg    # Yearly archived skyline vectors
├── docs/
│   ├── data/stats.json     # Chronological aggregates & streak calculations
│   ├── index.html          # Interactive Pages dashboard
│   ├── style.css           # Glassmorphism cyberpunk stylesheets
│   └── app.js              # Zoom, pan, and canvas export logic
├── scripts/
│   ├── renderer/
│   │   ├── animator.py     # Inline CSS animations compiler
│   │   ├── cube.py         # 3D isometric polygon face maths
│   │   ├── projection.py   # Maps (col, row, z) grid -> 2D screen coordinates
│   │   ├── styles.py       # Global grids, backgrounds, titles & legends
│   │   └── theme.py        # Gradients, glow filters, and adjust color helper
│   ├── client.py           # Rate-limit aware GitHub GraphQL Client
│   ├── config.py           # Global settings & themes validation
│   ├── logger.py           # Console + self-rotating logger with token scrubbing
│   ├── processor.py        # Year analytics, current and longest streak calculators
│   └── pipeline.py         # Main execution coordinator
├── themes/
│   ├── cyberpunk.json      # Default neon layout parameters
│   ├── github-dark.json    # Traditional GitHub mode
│   ├── matrix.json         # Green phosphors matrix look
│   └── light.json          # High-contrast light mode
├── config.json             # Global application parameters
├── requirements.txt        # PIP dependencies
├── skyline.py              # Root CLI wrapper
└── README.md               # Repository documentation
```

---

## ⚙️ Global Configuration (`config.json`)

All details are controlled via `config.json`. Update the `"username"` to fetch data for any GitHub user:

```json
{
  "username": "Durgesh729",
  "theme": "cyberpunk",
  "output_dir": "assets",
  "docs_dir": "docs",
  "github_pages_url": "https://Durgesh729.github.io/github-skyline/",
  "svg_settings": {
    "width": 1200,
    "height": 800,
    "height_scale": 15.0,
    "max_building_height": 180,
    "min_building_height": 5,
    "grid_spacing": 20,
    "perspective_angle": 30,
    "show_grid": true,
    "show_text": true
  },
  "animation_settings": {
    "enabled": true,
    "duration_seconds": 3.0,
    "delay_increment_seconds": 0.01,
    "pulse_glow": true,
    "scanline": true
  }
}
```

---

## 🎨 Theme Customization System
Themes are configured as structured JSON templates in the `themes/` directory.

### Available Themes:
1. `cyberpunk` (Default neon cyan/purple gradient with laser sweep grid scanlines)
2. `github-dark` (Clean dark mode displaying classic GitHub greens)
3. `matrix` (Glowing console terminal layout with monospaced text indicators)
4. `light` (Crisp modern high-contrast design for bright backgrounds)

Changing the theme is as simple as updating the `"theme"` value in `config.json` to the name of the target JSON file.

---

## 💻 Local Setup & CLI Usage

### Prerequisites
- Python 3.12 or newer.

### Installation
1. Clone the repository and install dependencies:
   ```bash
   git clone https://github.com/Durgesh729/github-skyline.git
   cd github-skyline
   pip install -r requirements.txt
   ```
2. Configure your credentials by creating a `.env` file in the root directory:
   ```env
   GITHUB_TOKEN=your_personal_access_token_here
   ```

### Running the CLI
Run the pipeline programmatically:

- **Generate Current Year Skyline**:
  ```bash
  python skyline.py --current
  ```
- **Generate All Available Years & Cumulative SVGs**:
  ```bash
  python skyline.py --all
  ```
- **Target a Specific Year**:
  ```bash
  python skyline.py --year 2025
  ```
- **Override Styling Theme**:
  ```bash
  python skyline.py --theme matrix --all
  ```
- **Force Offline Mock Mode (For local development/testing without tokens)**:
  ```bash
  python skyline.py --all --offline
  ```

---

## 🤖 Continuous GitHub Actions Integration

The workflow file `.github/workflows/skyline.yml` manages generation routines in the cloud.

### Workflow Features:
- **Triggers**: Scheduled daily at 00:00 UTC, weekly on Sundays at 12:00 UTC, or manually via the GitHub interface.
- **Testing**: Pre-runs the test suite to prevent publishing broken XML vectors.
- **Git Churn Prevention**: Computes SHA-256 hashes of generated SVGs and stats payloads. Files are written and pushed only if changes are detected, avoiding cluttering commit histories.
- **Fallback Authentication**: Automatically leverages repository secret `GH_TOKEN` or falls back to the default repo `GITHUB_TOKEN`.

---

## 🧪 Quality Assurance & Test Suites

The project features a suite of unit and integration tests checking configurations, token scrubbers, GraphQL error responses, analytics metrics, projection calculations, and compilation bounds.

Run the test suite locally:
```bash
python -m pytest tests/
```
All tests run cleanly with zero warnings.

---

## Data Integrity Verification

The GitHub Skyline Generator Hub enforces absolute mathematical data precision. For every run, a complete date-by-date verification audit is executed to ensure the generated skyline vectors exactly match GitHub's official metrics.

- ✔ Verified directly against GitHub GraphQL
- ✔ 1096 calendar days compared
- ✔ 1096 matched
- ✔ 0 mismatches
- ✔ Renderer = Processor = GraphQL
- ✔ Manual verification completed (GitHub UI confirmed 33 contributions on 2026-07-14)

### Audit Reports & Logs:
- [Data Integrity Audit Report](docs/audit/audit-report.md)
- [Yearly Comparison Table - 2024](docs/audit/comparison-2024.csv)
- [Yearly Comparison Table - 2025](docs/audit/comparison-2025.csv)
- [Yearly Comparison Table - 2026](docs/audit/comparison-2026.csv)

Anyone can clone this repository and independently verify that every rendered contribution block aligns 100% to official GitHub GraphQL calendar responses.

---

## 📜 License
Licensed under the MIT License. See [LICENSE](LICENSE) for details.
