document.addEventListener("DOMContentLoaded", () => {
  // UI Elements
  const selectYear = document.getElementById("year-select");
  const statsUsername = document.getElementById("stats-username");
  const statsTotal = document.getElementById("stats-total");
  const statsLongest = document.getElementById("stats-longest");
  const statsCurrent = document.getElementById("stats-current");
  const statsRepos = document.getElementById("stats-repos");
  const statsUpdated = document.getElementById("stats-updated");
  const svgRenderArea = document.getElementById("svg-render-area");
  const loadingSpinner = document.getElementById("viewport-spinner");
  
  // Interactive Viewport controls
  const canvasContainer = document.getElementById("viewport-canvas-container");
  const btnZoomIn = document.getElementById("btn-zoom-in");
  const btnZoomOut = document.getElementById("btn-zoom-out");
  const btnZoomReset = document.getElementById("btn-zoom-reset");
  const btnFullscreen = document.getElementById("btn-fullscreen");
  const btnDownloadSvg = document.getElementById("btn-download-svg");
  const btnDownloadPng = document.getElementById("btn-download-png");
  const exportCanvas = document.getElementById("export-canvas");

  // Zoom/Pan State
  let scale = 1.0;
  let translateX = 0;
  let translateY = 0;
  let isDragging = false;
  let startX = 0;
  let startY = 0;

  // Cache loaded stats
  let globalStatsData = null;

  // Initialize App
  init();

  async function init() {
    showLoading(true);
    try {
      // 1. Fetch Stats JSON
      const res = await fetch("data/stats.json");
      if (!res.ok) throw new Error("Stats database offline.");
      const data = await res.json();
      globalStatsData = data;
      
      // 2. Populate stats HUD
      populateHUD(data);
      
      // 3. Populate Year Dropdown
      populateYearOptions(data);
      
      // 4. Populate Theme Dropdown
      populateThemeOptions(data);

      // 5. Fetch and populate AI Insights
      try {
        const resAnalysis = await fetch("data/analysis.json");
        if (resAnalysis.ok) {
          const analysisData = await resAnalysis.json();
          populateAIInsights(analysisData);
        }
      } catch (errAnalysis) {
        console.warn("Failed to load analysis JSON:", errAnalysis);
      }

      // 6. Load initial SVG (default current year)
      await loadSkyline("current");

      // 7. Setup Viewport Event Listeners
      setupViewportControls();
      
    } catch (err) {
      console.error(err);
      svgRenderArea.innerHTML = `<div class="error-msg" style="padding:40px; color:#ec4899; text-align:center; font-family:monospace;">
        ERROR_CODE: DATABASE_RETRIEVAL_FAILURE<br>${err.message}
      </div>`;
    } finally {
      showLoading(false);
    }
  }

  function showLoading(active) {
    if (active) {
      loadingSpinner.classList.add("active");
    } else {
      loadingSpinner.classList.remove("active");
    }
  }

  function populateThemeOptions(data) {
    const selectTheme = document.getElementById("theme-select");
    if (!selectTheme) return;
    
    selectTheme.innerHTML = "";
    const themes = data.available_themes || ["cyberpunk"];
    themes.forEach(theme => {
      const opt = document.createElement("option");
      opt.value = theme;
      opt.textContent = theme;
      if (theme === "cyberpunk") {
        opt.selected = true;
      }
      selectTheme.appendChild(opt);
    });
    selectTheme.removeAttribute("disabled");
  }

  function populateAIInsights(analysisData) {
    const aiScore = document.getElementById("ai-score");
    const aiBestMonth = document.getElementById("ai-best-month");
    const aiBestWeekday = document.getElementById("ai-best-weekday");
    const aiBestMonthName = document.getElementById("ai-best-month-name");
    const aiYoYGrowth = document.getElementById("ai-yoy-growth");
    
    if (aiScore) aiScore.textContent = analysisData.productivity_score;
    if (aiBestMonth) aiBestMonth.textContent = analysisData.best_month || "N/A";
    if (aiBestWeekday) aiBestWeekday.textContent = analysisData.most_productive_weekday || "N/A";
    if (aiBestMonthName) aiBestMonthName.textContent = analysisData.most_productive_month || "N/A";
    
    if (aiYoYGrowth) {
      const growths = [];
      if (analysisData.yoy_growth) {
        Object.entries(analysisData.yoy_growth).forEach(([yr, val]) => {
          if (val === 0.0) {
            growths.push(`${yr}: Base`);
          } else {
            const prefix = val > 0 ? "+" : "";
            growths.push(`${yr}: ${prefix}${val}%`);
          }
        });
      }
      aiYoYGrowth.textContent = growths.length > 0 ? growths.join(", ") : "N/A";
    }
  }

  function populateHUD(data) {
    statsUsername.textContent = `@${data.username.toUpperCase()}`;
    statsTotal.textContent = data.total_contributions.toLocaleString();
    statsLongest.textContent = data.longest_streak;
    statsCurrent.textContent = data.current_streak;
    statsRepos.textContent = data.repository_count;
    
    // Format compilation date
    if (data.last_updated) {
      const date = new Date(data.last_updated);
      statsUpdated.textContent = date.toLocaleString();
    }
  }

  function populateYearOptions(data) {
    // Collect active years from summaries
    const years = Object.keys(data.yearly_summaries).sort((a, b) => b - a); // Descending
    
    // We already have hardcoded placeholder values for current, animated, all
    // Clear and build the dynamic options list
    selectYear.innerHTML = "";
    
    // Current Year Animated
    const optAnim = document.createElement("option");
    optAnim.value = "animated";
    optAnim.textContent = "Current Year (Animated)";
    selectYear.appendChild(optAnim);

    // Current Year Static
    const optCur = document.createElement("option");
    optCur.value = "current";
    optCur.textContent = "Current Year (Static)";
    selectYear.appendChild(optCur);

    // All Years
    const optAll = document.createElement("option");
    optAll.value = "all";
    optAll.textContent = "Cumulative (All Years)";
    selectYear.appendChild(optAll);

    // Add individual years
    years.forEach(year => {
      const opt = document.createElement("option");
      opt.value = year;
      opt.textContent = `Year: ${year}`;
      selectYear.appendChild(opt);
    });

    // Listen to changes
    selectYear.addEventListener("change", (e) => {
      loadSkyline(e.target.value);
    });
  }

  async function loadSkyline(key) {
    showLoading(true);
    resetTransform();

    let targetFile = "skyline-current.svg";
    if (key === "animated") targetFile = "skyline-animated.svg";
    else if (key === "all") targetFile = "skyline-all.svg";
    else if (key.match(/^\d{4}$/)) targetFile = `skyline-${key}.svg`;

    try {
      const res = await fetch(`../assets/${targetFile}`);
      if (!res.ok) throw new Error(`SVG file '${targetFile}' not found.`);
      const svgText = await res.text();
      
      // Inject raw SVG content into viewport to allow style and pan transformations
      svgRenderArea.innerHTML = svgText;
      
      // Remove hardcoded width and height attributes to allow fluid responsive scaling
      const svgEl = svgRenderArea.querySelector("svg");
      if (svgEl) {
        svgEl.removeAttribute("width");
        svgEl.removeAttribute("height");
        svgEl.style.width = "100%";
        svgEl.style.height = "100%";
      }
      
      // Update HUD values dynamically based on selected year if loading a specific year
      updateOverlayValues(key);
      
    } catch (err) {
      console.error(err);
      svgRenderArea.innerHTML = `<div class="error-msg" style="padding:40px; color:#ec4899; text-align:center; font-family:monospace;">
        ERROR_CODE: RENDERING_MATRIX_FAILURE<br>${err.message}
      </div>`;
    } finally {
      showLoading(false);
    }
  }

  function updateOverlayValues(key) {
    if (!globalStatsData) return;
    
    // If single year selection, we can show total contributions for that year
    if (key.match(/^\d{4}$/) && globalStatsData.yearly_summaries[key]) {
      const sum = globalStatsData.yearly_summaries[key];
      statsTotal.textContent = sum.total_contributions.toLocaleString();
    } else {
      // Revert to global all-time total
      statsTotal.textContent = globalStatsData.total_contributions.toLocaleString();
    }
  }

  // Transform Viewport Math (Zoom & Pan)
  function setupViewportControls() {
    // Mouse dragging/pan bindings
    canvasContainer.addEventListener("mousedown", (e) => {
      isDragging = true;
      startX = e.clientX - translateX;
      startY = e.clientY - translateY;
      canvasContainer.style.cursor = "grabbing";
    });

    window.addEventListener("mouseup", () => {
      isDragging = false;
      canvasContainer.style.cursor = "grab";
    });

    canvasContainer.addEventListener("mousemove", (e) => {
      if (!isDragging) return;
      translateX = e.clientX - startX;
      translateY = e.clientY - startY;
      applyTransform();
    });

    // Mouse scroll zoom bindings
    canvasContainer.addEventListener("wheel", (e) => {
      e.preventDefault();
      const zoomFactor = 0.08;
      if (e.deltaY < 0) {
        scale = Math.min(scale + zoomFactor, 4.0); // Limit zoom in
      } else {
        scale = Math.max(scale - zoomFactor, 0.4); // Limit zoom out
      }
      applyTransform();
    }, { passive: false });

    // Click actions buttons
    btnZoomIn.addEventListener("click", () => {
      scale = Math.min(scale + 0.25, 4.0);
      applyTransform();
    });

    btnZoomOut.addEventListener("click", () => {
      scale = Math.max(scale - 0.25, 0.4);
      applyTransform();
    });

    btnZoomReset.addEventListener("click", () => {
      resetTransform();
    });

    btnFullscreen.addEventListener("click", () => {
      toggleFullscreen();
    });

    // Download handlers
    btnDownloadSvg.addEventListener("click", downloadSVG);
    btnDownloadPng.addEventListener("click", downloadPNG);
  }

  function applyTransform() {
    svgRenderArea.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
  }

  function resetTransform() {
    scale = 1.0;
    translateX = 0;
    translateY = 0;
    applyTransform();
  }

  function toggleFullscreen() {
    const target = document.getElementById("fullscreen-target");
    if (!document.fullscreenElement) {
      target.requestFullscreen().catch(err => {
        console.error(`Fullscreen request rejected: ${err.message}`);
      });
    } else {
      document.exitFullscreen();
    }
  }

  // Export/Download Logic
  function getSerializedSVG() {
    const svgEl = svgRenderArea.querySelector("svg");
    if (!svgEl) return null;
    
    // Create clone to modify safely without changing active DOM
    const clone = svgEl.cloneNode(true);
    // Re-inject standard size definitions for static files compatibility
    clone.setAttribute("width", "1200");
    clone.setAttribute("height", "800");
    clone.style.width = "";
    clone.style.height = "";
    
    const serializer = new XMLSerializer();
    return serializer.serializeToString(clone);
  }

  function downloadSVG() {
    const svgString = getSerializedSVG();
    if (!svgString) return;

    const blob = new Blob([svgString], { type: "image/svg+xml;charset=utf-8" });
    const blobURL = URL.createObjectURL(blob);
    
    const a = document.createElement("a");
    a.href = blobURL;
    a.download = `github-skyline-${selectYear.value}.svg`;
    document.body.appendChild(a);
    a.click();
    
    // Cleanup
    document.body.removeChild(a);
    URL.revokeObjectURL(blobURL);
  }

  function downloadPNG() {
    const svgString = getSerializedSVG();
    if (!svgString) return;
    
    showLoading(true);

    // Build Image element with Blob URL
    const svgBlob = new Blob([svgString], { type: "image/svg+xml;charset=utf-8" });
    const blobURL = URL.createObjectURL(svgBlob);
    
    const img = new Image();
    
    img.onload = () => {
      // Set canvas size matching the high-resolution source
      exportCanvas.width = 1200;
      exportCanvas.height = 800;
      
      const ctx = exportCanvas.getContext("2d");
      ctx.clearRect(0, 0, 1200, 800);
      
      // Draw image onto canvas
      ctx.drawImage(img, 0, 0);
      
      try {
        const pngURL = exportCanvas.toDataURL("image/png");
        
        const a = document.createElement("a");
        a.href = pngURL;
        a.download = `github-skyline-${selectYear.value}.png`;
        document.body.appendChild(a);
        a.click();
        
        document.body.removeChild(a);
      } catch (err) {
        console.error("Canvas security block or rendering failure:", err);
      } finally {
        URL.revokeObjectURL(blobURL);
        showLoading(false);
      }
    };
    
    img.onerror = (err) => {
      console.error("Image loading failed:", err);
      URL.revokeObjectURL(blobURL);
      showLoading(false);
    };

    img.src = blobURL;
  }
});
