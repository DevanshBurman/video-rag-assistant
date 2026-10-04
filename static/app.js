/* ═══════════════════════════════════════════════════════════════════════════
   AI Video Assistant — Video Intelligence Studio (Client Controller)
   ═══════════════════════════════════════════════════════════════════════════ */

(() => {
    "use strict";

    /* ── Helper utilities ────────────────────────────────────────────────── */
    const $ = (id) => document.getElementById(id);
    const $$ = (sel) => document.querySelectorAll(sel);

    function escapeHtml(str) {
        if (!str) return "";
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function formatTime(date) {
        const d = date || new Date();
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    /* ── Application State ───────────────────────────────────────────────── */
    const state = {
        mode: "url",           // "url" | "file"
        selectedFile: null,
        taskId: null,
        pollTimer: null,
        pollIntervalMs: 1400,
        resultData: null,
        transcriptRaw: "",
        currentView: "idle",   // "idle" | "processing" | "results"
        elapsedSeconds: 0,
        elapsedTimer: null,
        recentSources: [],
        checkedActions: new Set(),
        transcriptMatches: [],
        currentMatchIndex: -1,
        exploreStepIndex: 0,
        threeRenderer: null,
        threeScene: null,
        threeCamera: null,
        threeOrb: null,
        threeAnimId: null,
    };

    /* ── DOM References ──────────────────────────────────────────────────── */
    const dom = {
        html: document.documentElement,
        metaTheme: $("meta-theme-color"),
        
        // Navigation Rails & Header
        sideRail: $("side-rail"),
        railBrandBtn: $("rail-brand-btn"),
        railBtnStudio: $("rail-btn-studio"),
        railBtnAnalysis: $("rail-btn-analysis"),
        railBtnResults: $("rail-btn-results"),
        railBtnHistory: $("rail-btn-history"),
        railBtnExplore: $("rail-btn-explore"),
        railThemeToggle: $("rail-theme-toggle"),
        topThemeToggle: $("top-theme-toggle"),
        topHowItWorksBtn: $("top-how-it-works-btn"),
        navResetBtn: $("nav-reset-btn"),
        navStepIngest: $("nav-step-ingest"),
        navStepAnalysis: $("nav-step-analysis"),
        navStepResults: $("nav-step-results"),
        
        // Views
        viewIdle: $("view-idle"),
        viewProcessing: $("progress-section"),
        viewResults: $("results-section"),
        heroSection: $("hero-section"),
        inputSection: $("input-section"),
        featuresSection: $("features-section"),
        
        // Input Controls
        segmentedControl: $("segmented-control"),
        tabUrlBtn: $("tab-url-btn"),
        tabFileBtn: $("tab-file-btn"),
        tabTextBtn: $("tab-text-btn"),
        panelUrl: $("panel-url"),
        panelFile: $("panel-file"),
        panelText: $("panel-text"),
        youtubeInput: $("youtube-url-input"),
        clearUrlBtn: $("clear-url-btn"),
        transcriptPasteInput: $("transcript-paste-input"),
        pasteCharCounter: $("paste-char-counter"),
        fallbackHelpBanner: $("fallback-help-banner"),
        fallbackBannerTitle: $("fallback-banner-title"),
        fallbackBannerDesc: $("fallback-banner-desc"),
        fallbackSwitchUploadBtn: $("fallback-switch-upload-btn"),
        fallbackSwitchPasteBtn: $("fallback-switch-paste-btn"),
        dropZone: $("drop-zone"),
        emptyStateBrowseBtn: $("empty-state-browse-btn"),
        fileInput: $("file-input"),
        selectedFilePill: $("selected-file-pill"),
        selectedFileName: $("selected-file-name"),
        selectedFileSize: $("selected-file-size"),
        removeFileBtn: $("remove-file-btn"),
        languageSelect: $("language-select"),
        startBtn: $("start-analysis-btn"),
        recentSourcesTray: $("recent-sources-tray"),
        recentSourcesList: $("recent-sources-list"),
        workflowCards: $$(".workflow-card"),
        
        // Processing View
        threeContainer: $("three-canvas-container"),
        fallbackOrb: $("fallback-orb"),
        liveStepLabel: $("live-step-label"),
        liveProgressPct: $("live-progress-pct"),
        progressBarFill: $("progress-bar-fill"),
        mainProgressBar: $("main-progress-bar"),
        elapsedTimeCounter: $("elapsed-time-counter"),
        cancelAnalysisBtn: $("cancel-analysis-btn"),
        pipelineStages: $$("#pipeline-stages .pipeline-step-card"),
        
        // Results View
        videoTitle: $("result-video-title"),
        statWordCount: $("stat-word-count"),
        statCharCount: $("stat-char-count"),
        statReadingTime: $("stat-reading-time"),
        tabStrip: $("tab-strip"),
        tabActivePill: $("tab-active-pill"),
        tabButtons: $$("#tab-strip .tab-btn"),
        tabPanes: $$(".tab-viewport .tab-pane"),
        
        // Tab Content Areas & Copy Buttons
        summaryContent: $("summary-content"),
        actionsContent: $("actions-content"),
        decisionsContent: $("decisions-content"),
        questionsContent: $("questions-content"),
        transcriptContent: $("transcript-content"),
        btnCopySummary: $("btn-copy-summary"),
        btnCopyActions: $("btn-copy-actions"),
        btnCopyDecisions: $("btn-copy-decisions"),
        btnCopyQuestions: $("btn-copy-questions"),
        
        // Transcript Tools
        transcriptSearch: $("transcript-search"),
        transcriptSearchCount: $("transcript-search-count"),
        searchNavControls: $("search-nav-controls"),
        transcriptPrevMatch: $("transcript-prev-match"),
        transcriptNextMatch: $("transcript-next-match"),
        copyTranscriptAction: $("copy-transcript-action"),
        
        // Export Deck
        btnExportPdf: $("btn-export-pdf"),
        btnExportTxt: $("btn-export-txt"),
        btnCopyAllTranscript: $("btn-copy-all-transcript"),
        
        // RAG Chat
        chatCard: $("chat-section-card"),
        chatForm: $("chat-form"),
        chatInput: $("chat-user-input"),
        chatSubmitBtn: $("chat-submit-btn"),
        chatMessagesArea: $("chat-messages-area"),
        clearChatBtn: $("clear-chat-btn"),
        suggestionChips: $$(".suggestion-chip"),
        
        // Modals & Tour
        topHowItWorksBtn: $("top-how-it-works-btn"),
        exploreModal: $("explore-modal"),
        exploreCloseBtn: $("explore-close-btn"),
        exploreStepCurrent: $("explore-step-current"),
        exploreStageEyebrow: $("explore-stage-eyebrow"),
        exploreStageTitle: $("explore-stage-title"),
        exploreStageBody: $("explore-stage-body"),
        exploreQuoteBox: $("explore-quote-box"),
        exploreQuoteText: $("explore-quote-text"),
        exploreStageImgLight: $("explore-stage-img-light"),
        exploreStageImgDark: $("explore-stage-img-dark"),
        exploreProgressFill: $("explore-progress-fill"),
        exploreStepButtons: $$(".explore-step-btn"),
        explorePrevBtn: $("explore-prev-btn"),
        exploreNextBtn: $("explore-next-btn"),
        splashModal: $("splash-modal"),
        splashSkipBtn: $("splash-skip-btn"),
        
        // Toast
        toastNotify: $("toast-notify"),
        toastIcon: $("toast-icon"),
        toastMsg: $("toast-msg"),
    };

    /* ═══════════════════════════════════════════════════════════════════════
       1. THEME SWITCHER (Light / Dark with View Transitions)
       ═══════════════════════════════════════════════════════════════════════ */
    function getStoredTheme() {
        try {
            const saved = localStorage.getItem("ai_video_theme");
            if (saved === "dark" || saved === "light") return saved;
        } catch (e) {}
        return "light";
    }

    function setTheme(newTheme, animate = true) {
        const apply = () => {
            dom.html.setAttribute("data-theme", newTheme);
            if (dom.metaTheme) {
                dom.metaTheme.setAttribute("content", newTheme === "dark" ? "#0A1822" : "#F5F8FA");
            }
            if (dom.railThemeToggle) {
                dom.railThemeToggle.setAttribute("aria-pressed", newTheme === "dark" ? "true" : "false");
            }
            try {
                localStorage.setItem("ai_video_theme", newTheme);
            } catch (e) {}

            // Update Three.js materials if initialized
            updateThreeColors(newTheme);
        };

        if (animate && document.startViewTransition && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            document.startViewTransition(() => apply());
        } else {
            apply();
        }
    }

    function toggleTheme() {
        const current = dom.html.getAttribute("data-theme") || "light";
        const next = current === "dark" ? "light" : "dark";
        setTheme(next, true);
        showToast(`Theme switched to ${next === "dark" ? "Dark Navy" : "Light Mist"}`);
    }

    /* ═══════════════════════════════════════════════════════════════════════
       2. RECENT SOURCES (Session Persistence)
       ═══════════════════════════════════════════════════════════════════════ */
    function loadRecentSources() {
        try {
            const raw = localStorage.getItem("ai_video_recent_sources");
            if (raw) {
                state.recentSources = JSON.parse(raw);
                renderRecentSources();
            }
        } catch (e) {}
    }

    function saveRecentSource(sourceName, type = "url") {
        if (!sourceName) return;
        state.recentSources = state.recentSources.filter(s => s.name !== sourceName);
        state.recentSources.unshift({ name: sourceName, type, time: Date.now() });
        if (state.recentSources.length > 5) state.recentSources.pop();
        try {
            localStorage.setItem("ai_video_recent_sources", JSON.stringify(state.recentSources));
        } catch (e) {}
        renderRecentSources();
    }

    function renderRecentSources() {
        if (!dom.recentSourcesList || !dom.recentSourcesTray) return;
        if (state.recentSources.length === 0) {
            dom.recentSourcesTray.classList.add("hidden");
            return;
        }

        dom.recentSourcesTray.classList.remove("hidden");
        dom.recentSourcesList.innerHTML = "";

        state.recentSources.forEach(item => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "recent-tag-btn";
            btn.textContent = item.name.length > 34 ? item.name.slice(0, 32) + "..." : item.name;
            btn.title = `Reload ${item.name}`;
            btn.addEventListener("click", () => {
                if (item.type === "url") {
                    setInputMode("url");
                    dom.youtubeInput.value = item.name;
                    validateInputState();
                } else {
                    showToast("Please re-select local file: " + item.name);
                    setInputMode("file");
                }
            });
            dom.recentSourcesList.appendChild(btn);
        });
    }

    /* ═══════════════════════════════════════════════════════════════════════
       3. SAFE MARKDOWN PARSER (XSS Safe & Proper Lists)
       ═══════════════════════════════════════════════════════════════════════ */
    function renderSafeMarkdown(rawText) {
        if (!rawText) return "";
        
        // 1. First escape all raw HTML characters to prevent XSS
        const escaped = escapeHtml(rawText);
        
        // 2. Parse lines
        const lines = escaped.split("\n");
        let html = "";
        let inList = false;

        for (let i = 0; i < lines.length; i++) {
            let line = lines[i].trim();

            if (!line) {
                if (inList) {
                    html += "</ul>";
                    inList = false;
                }
                continue;
            }

            // Headers
            if (line.startsWith("### ")) {
                if (inList) { html += "</ul>"; inList = false; }
                html += `<h4>${line.slice(4)}</h4>`;
                continue;
            }
            if (line.startsWith("## ")) {
                if (inList) { html += "</ul>"; inList = false; }
                html += `<h3>${line.slice(3)}</h3>`;
                continue;
            }
            if (line.startsWith("# ")) {
                if (inList) { html += "</ul>"; inList = false; }
                html += `<h3>${line.slice(2)}</h3>`;
                continue;
            }

            // Unordered list items: * or -
            const listMatch = line.match(/^[\*\-]\s+(.*)$/);
            if (listMatch) {
                if (!inList) {
                    html += "<ul>";
                    inList = true;
                }
                let body = formatInlineMarkdown(listMatch[1]);
                html += `<li>${body}</li>`;
                continue;
            }

            // Numbered list items: 1.
            const numMatch = line.match(/^(\d+)\.\s+(.*)$/);
            if (numMatch) {
                if (!inList) {
                    html += "<ol>";
                    inList = true;
                }
                let body = formatInlineMarkdown(numMatch[2]);
                html += `<li>${body}</li>`;
                continue;
            }

            if (inList) {
                html += "</ul>";
                inList = false;
            }

            // Regular paragraph
            html += `<p>${formatInlineMarkdown(line)}</p>`;
        }

        if (inList) {
            html += "</ul>";
        }

        return html;
    }

    function formatInlineMarkdown(text) {
        return text
            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.*?)\*/g, "<em>$1</em>")
            .replace(/`([^`]+)`/g, "<code>$1</code>");
    }

    /* ═══════════════════════════════════════════════════════════════════════
       4. INTERACTIVE 3D THREE.JS CENTERPIECE
       ═══════════════════════════════════════════════════════════════════════ */
    function initThreeJS() {
        if (!window.THREE || !dom.threeContainer) return;
        if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            return;
        }

        try {
            const width = dom.threeContainer.clientWidth || 380;
            const height = dom.threeContainer.clientHeight || 420;

            const scene = new THREE.Scene();
            const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
            camera.position.z = 7;

            const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
            renderer.setSize(width, height);
            renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

            dom.threeContainer.innerHTML = "";
            dom.threeContainer.appendChild(renderer.domElement);
            if (dom.fallbackOrb) dom.fallbackOrb.style.display = "none";

            // Translucent glass orb + orbiting rings
            const isDark = dom.html.getAttribute("data-theme") === "dark";
            const tealColor = new THREE.Color(isDark ? 0x36D5D0 : 0x168F95);
            const blueColor = new THREE.Color(isDark ? 0x3D8BFF : 0x0966ED);

            const orbGroup = new THREE.Group();

            // Inner core sphere
            const sphereGeo = new THREE.IcosahedronGeometry(1.6, 3);
            const sphereMat = new THREE.MeshPhongMaterial({
                color: tealColor,
                wireframe: true,
                transparent: true,
                opacity: 0.45,
            });
            const coreMesh = new THREE.Mesh(sphereGeo, sphereMat);
            orbGroup.add(coreMesh);

            // Orbiting particle ring
            const particleCount = 200;
            const partGeo = new THREE.BufferGeometry();
            const positions = new Float32Array(particleCount * 3);
            for (let i = 0; i < particleCount; i++) {
                const angle = (i / particleCount) * Math.PI * 2;
                const radius = 2.4 + (Math.random() - 0.5) * 0.4;
                positions[i * 3] = Math.cos(angle) * radius;
                positions[i * 3 + 1] = (Math.random() - 0.5) * 0.6;
                positions[i * 3 + 2] = Math.sin(angle) * radius;
            }
            partGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
            const partMat = new THREE.PointsMaterial({
                color: blueColor,
                size: 0.08,
                transparent: true,
                opacity: 0.8,
            });
            const particles = new THREE.Points(partGeo, partMat);
            orbGroup.add(particles);

            // Outer ring
            const ringGeo = new THREE.TorusGeometry(2.6, 0.02, 16, 100);
            const ringMat = new THREE.MeshBasicMaterial({
                color: tealColor,
                transparent: true,
                opacity: 0.6,
            });
            const ringMesh = new THREE.Mesh(ringGeo, ringMat);
            ringMesh.rotation.x = Math.PI / 3;
            orbGroup.add(ringMesh);

            scene.add(orbGroup);

            // Ambient & Point light
            const ambLight = new THREE.AmbientLight(0xffffff, 0.8);
            scene.add(ambLight);
            const pointLight = new THREE.PointLight(0x36D5D0, 2, 20);
            pointLight.position.set(5, 5, 5);
            scene.add(pointLight);

            state.threeRenderer = renderer;
            state.threeScene = scene;
            state.threeCamera = camera;
            state.threeOrb = orbGroup;

            // Mouse parallax response
            let targetRotX = 0;
            let targetRotY = 0;
            dom.threeContainer.addEventListener("mousemove", (e) => {
                const rect = dom.threeContainer.getBoundingClientRect();
                const x = (e.clientX - rect.left) / rect.width - 0.5;
                const y = (e.clientY - rect.top) / rect.height - 0.5;
                targetRotY = x * 0.8;
                targetRotX = y * 0.8;
            });

            // Animation Loop
            function animate() {
                state.threeAnimId = requestAnimationFrame(animate);

                orbGroup.rotation.y += 0.008;
                orbGroup.rotation.x += (targetRotX - orbGroup.rotation.x) * 0.05;
                orbGroup.rotation.z += 0.003;
                particles.rotation.y -= 0.012;

                renderer.render(scene, camera);
            }
            animate();

            // Resize handler
            window.addEventListener("resize", () => {
                if (!dom.threeContainer) return;
                const w = dom.threeContainer.clientWidth;
                const h = dom.threeContainer.clientHeight;
                if (w && h) {
                    camera.aspect = w / h;
                    camera.updateProjectionMatrix();
                    renderer.setSize(w, h);
                }
            });

        } catch (e) {
            console.warn("Three.js setup fallback:", e);
            if (dom.fallbackOrb) dom.fallbackOrb.style.display = "grid";
        }
    }

    function updateThreeColors(theme) {
        if (!state.threeOrb || !window.THREE) return;
        const isDark = theme === "dark";
        const teal = new THREE.Color(isDark ? 0x36D5D0 : 0x168F95);
        const blue = new THREE.Color(isDark ? 0x3D8BFF : 0x0966ED);

        state.threeOrb.children.forEach(child => {
            if (child.material && child.material.color) {
                if (child instanceof THREE.Points) {
                    child.material.color = blue;
                } else {
                    child.material.color = teal;
                }
            }
        });
    }

    /* ═══════════════════════════════════════════════════════════════════════
       5. 3D TILT EFFECT & PARALLAX GRID
       ═══════════════════════════════════════════════════════════════════════ */
    function init3DTilt() {
        const isTouch = ('ontouchstart' in window) || (navigator.maxTouchPoints > 0);
        if (isTouch || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

        const cards = $$(".card-3d");
        const grid = $("perspective-grid");

        if (grid) {
            window.addEventListener("mousemove", (e) => {
                const xRatio = (e.clientX / window.innerWidth) - 0.5;
                const yRatio = (e.clientY / window.innerHeight) - 0.5;
                grid.style.transform = `perspective(700px) rotateX(${48 + yRatio * -4}deg) rotateY(${xRatio * 4}deg)`;
            });
        }

        cards.forEach((card) => {
            card.addEventListener("mousemove", (e) => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                const centerX = rect.width / 2;
                const centerY = rect.height / 2;
                const rotateX = ((y - centerY) / centerY) * -3.5;
                const rotateY = ((x - centerX) / centerX) * 3.5;

                card.style.transform = `perspective(900px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateY(-2px)`;
            });

            card.addEventListener("mouseleave", () => {
                card.style.transform = "";
            });
        });
    }

    /* ═══════════════════════════════════════════════════════════════════════
       6. TOAST NOTIFICATIONS
       ═══════════════════════════════════════════════════════════════════════ */
    let toastTimeout = null;
    function showToast(msg, isError = false) {
        if (!dom.toastNotify) return;
        clearTimeout(toastTimeout);

        dom.toastMsg.textContent = msg;
        if (isError) {
            dom.toastNotify.classList.add("error");
            dom.toastIcon.textContent = "✕";
        } else {
            dom.toastNotify.classList.remove("error");
            dom.toastIcon.textContent = "✓";
        }

        dom.toastNotify.classList.remove("hidden");
        toastTimeout = setTimeout(() => {
            dom.toastNotify.classList.add("hidden");
        }, 3600);
    }

    /* ═══════════════════════════════════════════════════════════════════════
       7. VIEW NAVIGATION CONTROLLER
       ═══════════════════════════════════════════════════════════════════════ */
    function switchView(viewName) {
        state.currentView = viewName;

        // Toggle Views
        dom.viewIdle.classList.toggle("hidden", viewName !== "idle");
        dom.viewProcessing.classList.toggle("hidden", viewName !== "processing");
        dom.viewResults.classList.toggle("hidden", viewName !== "results");
        dom.navResetBtn.classList.toggle("hidden", viewName !== "results");

        // Sync Top 3-Step Bar
        dom.navStepIngest.classList.toggle("active", viewName === "idle");
        dom.navStepAnalysis.classList.toggle("active", viewName === "processing");
        dom.navStepResults.classList.toggle("active", viewName === "results");

        // Sync Left Rail
        dom.railBtnStudio.classList.toggle("active", viewName === "idle");
        dom.railBtnAnalysis.classList.toggle("active", viewName === "processing");
        dom.railBtnResults.classList.toggle("active", viewName === "results");

        window.scrollTo({ top: 0, behavior: "smooth" });

        if (viewName === "results") {
            updateTabIndicator();
        }
    }

    /* ═══════════════════════════════════════════════════════════════════════
       8. INPUT MODE & VALIDATION
       ═══════════════════════════════════════════════════════════════════════ */
    function setInputMode(newMode) {
        state.mode = newMode;

        if (dom.segmentedControl) {
            dom.segmentedControl.classList.remove("file-active", "mode-url", "mode-file", "mode-text");
            dom.segmentedControl.classList.add(`mode-${newMode}`);
            if (newMode === "file") dom.segmentedControl.classList.add("file-active");
        }

        const tabs = [
            { mode: "url", btn: dom.tabUrlBtn, panel: dom.panelUrl },
            { mode: "file", btn: dom.tabFileBtn, panel: dom.panelFile },
            { mode: "text", btn: dom.tabTextBtn, panel: dom.panelText },
        ];

        tabs.forEach(t => {
            const isActive = t.mode === newMode;
            if (t.btn) {
                t.btn.classList.toggle("active", isActive);
                t.btn.setAttribute("aria-selected", isActive ? "true" : "false");
            }
            if (t.panel) {
                t.panel.classList.toggle("hidden", !isActive);
                t.panel.classList.toggle("active", isActive);
            }
        });

        // Hide fallback alert when user switches modes
        if (dom.fallbackHelpBanner) dom.fallbackHelpBanner.classList.add("hidden");

        validateInputState();
    }

    function validateInputState() {
        let isValid = false;
        if (state.mode === "url") {
            const urlVal = dom.youtubeInput.value.trim();
            dom.clearUrlBtn.classList.toggle("hidden", urlVal.length === 0);
            isValid = urlVal.length > 5 && (
                urlVal.includes("youtube.com") ||
                urlVal.includes("youtu.be") ||
                urlVal.startsWith("http://") ||
                urlVal.startsWith("https://")
            );
        } else if (state.mode === "file") {
            isValid = state.selectedFile !== null;
        } else if (state.mode === "text") {
            const textVal = dom.transcriptPasteInput ? dom.transcriptPasteInput.value.trim() : "";
            const charCount = textVal.length;
            if (dom.pasteCharCounter) {
                dom.pasteCharCounter.textContent = `${charCount} characters`;
            }
            isValid = charCount > 15;
        }

        dom.startBtn.disabled = !isValid;
    }

    function formatBytes(bytes) {
        if (!bytes || bytes === 0) return "0 Bytes";
        const k = 1024;
        const sizes = ["Bytes", "KB", "MB", "GB"];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
    }

    function handleFileSelection(file) {
        if (!file) return;
        state.selectedFile = file;

        dom.selectedFileName.textContent = file.name;
        dom.selectedFileSize.textContent = formatBytes(file.size);
        dom.selectedFilePill.classList.remove("hidden");
        dom.dropZone.classList.add("hidden");

        validateInputState();
        showToast(`Selected file: ${file.name}`);
    }

    function removeSelectedFile() {
        state.selectedFile = null;
        dom.fileInput.value = "";
        dom.selectedFilePill.classList.add("hidden");
        dom.dropZone.classList.remove("hidden");
        validateInputState();
    }

    /* ═══════════════════════════════════════════════════════════════════════
       9. PIPELINE STAGES & LOOKUP TABLE
       ═══════════════════════════════════════════════════════════════════════ */
    const PIPELINE_LOOKUP = [
        { minPct: 0, stageIndex: 0, label: "Downloading & processing audio..." },
        { minPct: 18, stageIndex: 1, label: "Transcribing audio with Whisper AI..." },
        { minPct: 38, stageIndex: 2, label: "Generating title with Mistral 7B..." },
        { minPct: 48, stageIndex: 3, label: "Creating executive summary..." },
        { minPct: 60, stageIndex: 4, label: "Extracting action items & commitments..." },
        { minPct: 72, stageIndex: 5, label: "Extracting key decisions & questions..." },
        { minPct: 86, stageIndex: 6, label: "Building ChromaDB vector RAG engine..." },
    ];

    function getPipelineStepInfo(pct) {
        let current = PIPELINE_LOOKUP[0];
        for (let i = 0; i < PIPELINE_LOOKUP.length; i++) {
            if (pct >= PIPELINE_LOOKUP[i].minPct) {
                current = PIPELINE_LOOKUP[i];
            }
        }
        return current;
    }

    function startTimer() {
        state.elapsedSeconds = 0;
        clearInterval(state.elapsedTimer);
        state.elapsedTimer = setInterval(() => {
            state.elapsedSeconds++;
            const mins = String(Math.floor(state.elapsedSeconds / 60)).padStart(2, "0");
            const secs = String(state.elapsedSeconds % 60).padStart(2, "0");
            if (dom.elapsedTimeCounter) {
                dom.elapsedTimeCounter.textContent = `${mins}:${secs}`;
            }
        }, 1000);
    }

    function stopTimer() {
        clearInterval(state.elapsedTimer);
    }

    function updateProgress(percent, label) {
        const rounded = Math.round(percent);
        dom.liveProgressPct.textContent = rounded;
        dom.progressBarFill.style.width = `${percent}%`;
        dom.mainProgressBar.setAttribute("aria-valuenow", rounded);
        dom.liveStepLabel.textContent = label;

        const info = getPipelineStepInfo(rounded);

        dom.pipelineStages.forEach((stepCard, idx) => {
            const chip = stepCard.querySelector(".step-status-chip");
            const indicator = stepCard.querySelector(".step-indicator");

            if (idx < info.stageIndex) {
                stepCard.className = "pipeline-step-card completed";
                indicator.innerHTML = "✓";
                if (chip) chip.textContent = "Done";
            } else if (idx === info.stageIndex) {
                stepCard.className = "pipeline-step-card active";
                indicator.innerHTML = idx + 1;
                if (chip) chip.textContent = "Active";
            } else {
                stepCard.className = "pipeline-step-card";
                indicator.innerHTML = idx + 1;
                if (chip) chip.textContent = "Queued";
            }
        });
    }

    /* ═══════════════════════════════════════════════════════════════════════
       10. PIPELINE EXECUTION & STATUS POLLING
       ═══════════════════════════════════════════════════════════════════════ */
    async function startAnalysis() {
        dom.startBtn.disabled = true;

        const formData = new FormData();
        const lang = dom.languageSelect.value;
        formData.append("language", lang);

        let sourceLabel = "";
        if (state.mode === "url") {
            const url = dom.youtubeInput.value.trim();
            formData.append("source", url);
            sourceLabel = url;
            saveRecentSource(url, "url");
        } else if (state.mode === "file" && state.selectedFile) {
            formData.append("file", state.selectedFile);
            sourceLabel = state.selectedFile.name;
            saveRecentSource(state.selectedFile.name, "file");
        } else if (state.mode === "text") {
            const pastedText = dom.transcriptPasteInput.value.trim();
            formData.append("transcript_text", pastedText);
            sourceLabel = "Pasted Transcript";
            saveRecentSource("Pasted Transcript", "text");
        }

        try {
            switchView("processing");
            startTimer();
            updateProgress(5, "Contacting processing engine...");

            const res = await fetch("/process", {
                method: "POST",
                body: formData,
            }).catch(() => fetch("/api/analyze", { method: "POST", body: formData }));

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || "Failed to start analysis");
            }

            const data = await res.json();
            state.taskId = data.job_id || data.task_id;

            startStatusPolling(state.taskId);
        } catch (err) {
            console.error("Analysis initiation error:", err);
            stopTimer();
            showToast(err.message || "Failed to connect to server", true);
            switchView("idle");
            validateInputState();
        }
    }

    function cancelAnalysis() {
        clearInterval(state.pollTimer);
        stopTimer();
        state.taskId = null;
        switchView("idle");
        validateInputState();
        showToast("Analysis cancelled by user");
    }

    function startStatusPolling(taskId) {
        clearInterval(state.pollTimer);

        let pollCount = 0;
        state.pollTimer = setInterval(async () => {
            pollCount++;
            try {
                const res = await fetch(`/api/status/${taskId}`);
                if (res.status === 404) {
                    clearInterval(state.pollTimer);
                    stopTimer();
                    showToast("Analysis task expired or not found. Please restart.", true);
                    switchView("idle");
                    return;
                }
                if (!res.ok) throw new Error("Status check failed");

                const data = await res.json();

                if (data.status === "processing") {
                    const pct = data.progress || 10;
                    const stepText = data.step || "Processing...";
                    updateProgress(pct, stepText);
                } else if (data.status === "complete") {
                    clearInterval(state.pollTimer);
                    stopTimer();
                    updateProgress(100, "Analysis complete! Preparing presentation...");
                    setTimeout(() => {
                        presentResults(data.result);
                    }, 600);
                } else if (data.status === "error") {
                    clearInterval(state.pollTimer);
                    stopTimer();
                    const errMsg = data.step || "Pipeline encountered an error";
                    showToast(errMsg, true);
                    
                    // Show friendly user-facing fallback card on ingest screen
                    if (dom.fallbackHelpBanner) {
                        dom.fallbackHelpBanner.classList.remove("hidden");
                        if (dom.fallbackBannerDesc) {
                            dom.fallbackBannerDesc.textContent = errMsg;
                        }
                    }
                    setTimeout(() => switchView("idle"), 2000);
                }
            } catch (err) {
                console.error("Polling error:", err);
            }
        }, state.pollIntervalMs);
    }

    /* ═══════════════════════════════════════════════════════════════════════
       11. PRESENT RESULTS & TABS
       ═══════════════════════════════════════════════════════════════════════ */
    function renderCheckableActions(rawText, container) {
        if (!rawText || !rawText.trim()) {
            container.innerHTML = `<div class="item-card-3d"><span class="item-text" style="color:var(--text-muted)">No action items extracted.</span></div>`;
            return;
        }

        const lines = rawText.split("\n").filter(l => l.trim().length > 0);
        container.innerHTML = "";

        lines.forEach((line, index) => {
            const clean = line.replace(/^[\*\-\d\.\s]+/, "").trim();
            if (!clean) return;

            const card = document.createElement("div");
            card.className = "item-card-3d";

            const checkbox = document.createElement("div");
            checkbox.className = "item-action-checkbox";
            checkbox.setAttribute("role", "checkbox");
            checkbox.setAttribute("aria-checked", "false");
            checkbox.setAttribute("tabindex", "0");

            const textSpan = document.createElement("span");
            textSpan.className = "item-text";
            textSpan.textContent = clean;

            const toggle = () => {
                const isChecked = checkbox.classList.toggle("checked");
                checkbox.setAttribute("aria-checked", isChecked ? "true" : "false");
                checkbox.innerHTML = isChecked ? "✓" : "";
                textSpan.classList.toggle("completed", isChecked);
            };

            checkbox.addEventListener("click", toggle);
            checkbox.addEventListener("keydown", (e) => {
                if (e.key === " " || e.key === "Enter") {
                    e.preventDefault();
                    toggle();
                }
            });

            card.appendChild(checkbox);
            card.appendChild(textSpan);
            container.appendChild(card);
        });
    }

    function renderItemList(rawText, container, iconSvg) {
        if (!rawText || !rawText.trim()) {
            container.innerHTML = `<div class="item-card-3d"><span class="item-text" style="color:var(--text-muted)">No items extracted.</span></div>`;
            return;
        }

        const lines = rawText.split("\n").filter(l => l.trim().length > 0);
        let html = "";

        lines.forEach(line => {
            const clean = line.replace(/^[\*\-\d\.\s]+/, "").trim();
            if (clean) {
                html += `
                    <div class="item-card-3d">
                        <div class="item-check-icon">${iconSvg}</div>
                        <div class="item-text">${escapeHtml(clean)}</div>
                    </div>
                `;
            }
        });

        container.innerHTML = html || `<div class="item-card-3d"><span class="item-text">${escapeHtml(rawText)}</span></div>`;
    }

    function presentResults(result) {
        state.resultData = result;
        state.transcriptRaw = result.transcript || "";

        // Header Title & Animated Stats
        dom.videoTitle.textContent = result.title || "Video Analysis Report";
        animateNumber(dom.statWordCount, result.word_count || 0);
        animateNumber(dom.statCharCount, result.char_count || 0);

        // Calculate reading/listening time estimate (~150 words/min)
        const words = result.word_count || 0;
        const estMins = Math.max(1, Math.round(words / 150));
        dom.statReadingTime.textContent = `~${estMins} min`;

        // 1. Executive Summary
        dom.summaryContent.innerHTML = renderSafeMarkdown(result.summary);

        // 2. Action Items (Checkable)
        renderCheckableActions(result.action_items, dom.actionsContent);

        // 3. Key Decisions
        const decisionIcon = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>`;
        renderItemList(result.key_decisions, dom.decisionsContent, decisionIcon);

        // 4. Open Questions
        const questionIcon = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`;
        renderItemList(result.open_questions, dom.questionsContent, questionIcon);

        // 5. Full Transcript
        dom.transcriptContent.textContent = result.transcript || "No transcript available.";

        // Export links
        dom.btnExportPdf.href = `/api/export/${state.taskId}/pdf`;
        dom.btnExportTxt.href = `/api/export/${state.taskId}/txt`;

        switchView("results");
        showToast("Intelligence report generated successfully!");
    }

    function animateNumber(element, finalValue) {
        if (!element) return;
        const duration = 600;
        const startTime = performance.now();
        const startVal = 0;

        function step(now) {
            const elapsed = now - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const current = Math.floor(startVal + (finalValue - startVal) * progress);
            element.textContent = current.toLocaleString();
            if (progress < 1) {
                requestAnimationFrame(step);
            } else {
                element.textContent = finalValue.toLocaleString();
            }
        }
        requestAnimationFrame(step);
    }

    /* ═══════════════════════════════════════════════════════════════════════
       12. TAB STRIP NAVIGATION
       ═══════════════════════════════════════════════════════════════════════ */
    function updateTabIndicator() {
        const activeBtn = $("#tab-strip .tab-btn.active");
        if (!activeBtn || !dom.tabActivePill) return;

        dom.tabActivePill.style.width = `${activeBtn.offsetWidth}px`;
        dom.tabActivePill.style.left = `${activeBtn.offsetLeft}px`;
    }

    function switchTab(tabKey) {
        dom.tabButtons.forEach(btn => {
            const isMatch = btn.dataset.tab === tabKey;
            btn.classList.toggle("active", isMatch);
            btn.setAttribute("aria-selected", isMatch ? "true" : "false");
        });

        dom.tabPanes.forEach(pane => {
            pane.classList.toggle("hidden", pane.id !== `tab-pane-${tabKey}`);
        });

        updateTabIndicator();
    }

    /* ═══════════════════════════════════════════════════════════════════════
       13. SAFE TRANSCRIPT SEARCH WITH HIGHLIGHT & JUMP
       ═══════════════════════════════════════════════════════════════════════ */
    function searchTranscript() {
        const query = dom.transcriptSearch.value.trim().toLowerCase();
        if (!query) {
            dom.transcriptContent.textContent = state.transcriptRaw;
            dom.transcriptSearchCount.classList.add("hidden");
            dom.searchNavControls.classList.add("hidden");
            state.transcriptMatches = [];
            state.currentMatchIndex = -1;
            return;
        }

        const raw = state.transcriptRaw;
        // Escape query for regex
        const safeQuery = query.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const regex = new RegExp(`(${safeQuery})`, "gi");

        const matches = raw.match(regex);
        const matchCount = matches ? matches.length : 0;

        dom.transcriptSearchCount.textContent = `${matchCount} match${matchCount === 1 ? "" : "es"}`;
        dom.transcriptSearchCount.classList.remove("hidden");
        dom.searchNavControls.classList.toggle("hidden", matchCount === 0);

        // Escape raw text first, then wrap matching portions in <mark>
        const escaped = escapeHtml(raw);
        const escapedQuery = escapeHtml(query).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const highlightRegex = new RegExp(`(${escapedQuery})`, "gi");
        const highlighted = escaped.replace(highlightRegex, `<mark class="search-match">$1</mark>`);

        dom.transcriptContent.innerHTML = highlighted;

        // Collect all <mark> nodes for navigation
        state.transcriptMatches = Array.from(dom.transcriptContent.querySelectorAll("mark.search-match"));
        state.currentMatchIndex = state.transcriptMatches.length > 0 ? 0 : -1;
        scrollToCurrentMatch();
    }

    function scrollToCurrentMatch() {
        if (state.currentMatchIndex < 0 || state.currentMatchIndex >= state.transcriptMatches.length) return;
        state.transcriptMatches.forEach((m, idx) => {
            m.style.outline = idx === state.currentMatchIndex ? "2px solid #0966ED" : "none";
        });
        const currentEl = state.transcriptMatches[state.currentMatchIndex];
        if (currentEl) {
            currentEl.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    }

    function jumpPrevMatch() {
        if (state.transcriptMatches.length === 0) return;
        state.currentMatchIndex = (state.currentMatchIndex - 1 + state.transcriptMatches.length) % state.transcriptMatches.length;
        scrollToCurrentMatch();
    }

    function jumpNextMatch() {
        if (state.transcriptMatches.length === 0) return;
        state.currentMatchIndex = (state.currentMatchIndex + 1) % state.transcriptMatches.length;
        scrollToCurrentMatch();
    }

    function copyToClipboard(text, successMsg) {
        if (!text) {
            showToast("Nothing to copy", true);
            return;
        }
        navigator.clipboard.writeText(text).then(
            () => showToast(successMsg || "Copied to clipboard!"),
            () => showToast("Clipboard access denied", true)
        );
    }

    /* ═══════════════════════════════════════════════════════════════════════
       14. RAG CHAT CONVERSATION
       ═══════════════════════════════════════════════════════════════════════ */
    async function sendChatMessage(question) {
        if (!question || !question.trim()) return;
        const q = question.trim();

        appendChatMessage("user", q);
        dom.chatInput.value = "";
        dom.chatSubmitBtn.disabled = true;

        const typingEl = appendTypingIndicator();

        try {
            const formData = new FormData();
            formData.append("task_id", state.taskId);
            formData.append("question", q);

            const res = await fetch("/api/chat", {
                method: "POST",
                body: formData,
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || "RAG engine query failed");
            }

            const data = await res.json();
            typingEl.remove();
            appendChatMessage("ai", data.answer || "No response received.");
        } catch (err) {
            console.error("Chat error:", err);
            typingEl.remove();
            appendChatMessage("ai", `Error: ${err.message || "Failed to process query."}`);
        } finally {
            dom.chatSubmitBtn.disabled = false;
        }
    }

    function appendChatMessage(sender, text) {
        const msgDiv = document.createElement("div");
        msgDiv.className = `chat-msg ${sender}-msg`;

        const avatar = sender === "user" ? "You" : "AI";
        const formatted = sender === "ai" ? renderSafeMarkdown(text) : `<p>${escapeHtml(text)}</p>`;

        msgDiv.innerHTML = `
            <div class="msg-avatar">${avatar}</div>
            <div class="msg-body">
                <div class="msg-content">${formatted}</div>
                <span class="msg-time">${formatTime()}</span>
            </div>
        `;

        dom.chatMessagesArea.appendChild(msgDiv);
        dom.chatMessagesArea.scrollTop = dom.chatMessagesArea.scrollHeight;
    }

    function appendTypingIndicator() {
        const msgDiv = document.createElement("div");
        msgDiv.className = "chat-msg ai-msg";
        msgDiv.innerHTML = `
            <div class="msg-avatar">AI</div>
            <div class="msg-body">
                <div class="msg-content">
                    <div class="typing-dots">
                        <span class="typing-dot"></span>
                        <span class="typing-dot"></span>
                        <span class="typing-dot"></span>
                    </div>
                </div>
            </div>
        `;
        dom.chatMessagesArea.appendChild(msgDiv);
        dom.chatMessagesArea.scrollTop = dom.chatMessagesArea.scrollHeight;
        return msgDiv;
    }

    function clearChat() {
        dom.chatMessagesArea.innerHTML = `
            <div class="chat-msg ai-msg">
                <div class="msg-avatar">AI</div>
                <div class="msg-body">
                    <div class="msg-content">
                        <p>Conversation history cleared. Ask anything regarding the video.</p>
                    </div>
                    <span class="msg-time">Just now</span>
                </div>
            </div>
        `;
        showToast("Conversation cleared");
    }

    /* ═══════════════════════════════════════════════════════════════════════
       15. "HOW IT WORKS" EXPLORE MODAL
       ═══════════════════════════════════════════════════════════════════════ */
    const EXPLORE_STAGES = [
        {
            num: "01",
            eyebrow: "STEP 01 — MULTIMODAL INGESTION",
            title: "Acoustic Splitting & Audio Processing",
            body: "Media is acquired from YouTube streams or direct local container uploads (MP4, WAV, MP3). Pydub normalizes the stream to 16kHz mono audio and partitions it into 10-minute parallelizable acoustic chunks.",
            quote: "Whisper acoustic modeling extracts phonemes seamlessly across mixed English and Hinglish vernacular.",
            progress: "25%",
            imgLight: "/static/assets/snapshots/stage_01_light.png",
            imgDark: "/static/assets/snapshots/stage_01_dark.png",
            alt: "Acoustic Splitting & Audio Processing Pipeline"
        },
        {
            num: "02",
            eyebrow: "STEP 02 — WHISPER SPEECH RECOGNITION",
            title: "High-Fidelity Phoneme Transcription",
            body: "OpenAI Whisper AI processes each 10-minute slice through deep transformer encoders. It accurately transcribes speech with natural punctuation, recognizing technical jargon and multi-speaker exchanges.",
            quote: "Punctuation-restored transcription preserves semantic clarity for downstream vector indexing.",
            progress: "50%",
            imgLight: "/static/assets/snapshots/stage_02_light.png",
            imgDark: "/static/assets/snapshots/stage_02_dark.png",
            alt: "OpenAI Whisper Speech-To-Text Transcription"
        },
        {
            num: "03",
            eyebrow: "STEP 03 — MISTRAL 7B SYNTHESIS",
            title: "Structured Executive Intelligence",
            body: "Mistral 7B synthesizes the full transcript into four discrete artifacts: an executive summary, clear action item deliverables, agreed key decisions, and unanswered questions for team follow-up.",
            quote: "Zero fluff: each commitment is isolated with assigned context for immediate operational execution.",
            progress: "75%",
            imgLight: "/static/assets/snapshots/stage_03_light.png",
            imgDark: "/static/assets/snapshots/stage_03_dark.png",
            alt: "Mistral 7B Structured Executive Intelligence"
        },
        {
            num: "04",
            eyebrow: "STEP 04 — CHROMADB VECTOR RAG",
            title: "Interactive Grounded Dialogue",
            body: "LangChain partitions the transcript into dense embeddings stored in ChromaDB vector collections. When you ask questions, cosine similarity retrieves exact timestamped segments to formulate truthful answers.",
            quote: "Evidence-first: answers are directly grounded in the video's actual spoken dialogue.",
            progress: "100%",
            imgLight: "/static/assets/snapshots/stage_04_light.png",
            imgDark: "/static/assets/snapshots/stage_04_dark.png",
            alt: "ChromaDB Grounded Conversational AI"
        }
    ];

    function openExploreModal(stepIndex = 0) {
        state.exploreStepIndex = stepIndex;
        updateExploreSlide();
        if (dom.exploreModal) {
            dom.exploreModal.classList.remove("hidden");
            if (dom.exploreCloseBtn) dom.exploreCloseBtn.focus();
        }
    }

    function closeExploreModal() {
        if (dom.exploreModal) {
            dom.exploreModal.classList.add("hidden");
        }
    }

    function updateExploreSlide() {
        const stage = EXPLORE_STAGES[state.exploreStepIndex];
        if (!stage) return;

        if (dom.exploreStepCurrent) dom.exploreStepCurrent.textContent = stage.num;
        if (dom.exploreStageEyebrow) dom.exploreStageEyebrow.textContent = stage.eyebrow;
        if (dom.exploreStageTitle) dom.exploreStageTitle.textContent = stage.title;
        if (dom.exploreStageBody) dom.exploreStageBody.textContent = stage.body;
        if (dom.exploreQuoteText) dom.exploreQuoteText.textContent = `"${stage.quote}"`;
        if (dom.exploreProgressFill) dom.exploreProgressFill.style.width = stage.progress;

        if (dom.exploreStageImgLight) {
            dom.exploreStageImgLight.src = stage.imgLight;
            dom.exploreStageImgLight.alt = stage.alt;
        }
        if (dom.exploreStageImgDark) {
            dom.exploreStageImgDark.src = stage.imgDark;
            dom.exploreStageImgDark.alt = stage.alt;
        }

        if (dom.exploreStepButtons) {
            dom.exploreStepButtons.forEach((btn, idx) => {
                btn.classList.toggle("active", idx === state.exploreStepIndex);
            });
        }

        if (dom.explorePrevBtn) dom.explorePrevBtn.disabled = state.exploreStepIndex === 0;
        if (dom.exploreNextBtn) dom.exploreNextBtn.textContent = state.exploreStepIndex === EXPLORE_STAGES.length - 1 ? "Finish Tour" : "Next Step →";
    }

    function nextExploreStep() {
        if (state.exploreStepIndex < EXPLORE_STAGES.length - 1) {
            state.exploreStepIndex++;
            updateExploreSlide();
        } else {
            closeExploreModal();
        }
    }

    function prevExploreStep() {
        if (state.exploreStepIndex > 0) {
            state.exploreStepIndex--;
            updateExploreSlide();
        }
    }

    /* ═══════════════════════════════════════════════════════════════════════
       16. SPLASH / LOADER MODAL (800ms)
       ═══════════════════════════════════════════════════════════════════════ */
    function initSplashLoader() {
        if (!dom.splashModal) return;

        function dismissSplash() {
            dom.splashModal.classList.add("fade-out");
            setTimeout(() => {
                dom.splashModal.classList.add("hidden");
            }, 400);
        }

        // Auto dismiss after 800ms
        const timer = setTimeout(dismissSplash, 800);

        dom.splashSkipBtn.addEventListener("click", () => {
            clearTimeout(timer);
            dismissSplash();
        });

        window.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && !dom.splashModal.classList.contains("hidden")) {
                clearTimeout(timer);
                dismissSplash();
            }
        });
    }

    /* ═══════════════════════════════════════════════════════════════════════
       17. EVENT LISTENERS SETUP
       ═══════════════════════════════════════════════════════════════════════ */
    function initEventListeners() {
        // Theme switchers
        if (dom.topThemeToggle) dom.topThemeToggle.addEventListener("click", toggleTheme);
        if (dom.railThemeToggle) dom.railThemeToggle.addEventListener("click", toggleTheme);

        // Rail views navigation
        if (dom.railBtnStudio) dom.railBtnStudio.addEventListener("click", () => switchView("idle"));
        if (dom.railBtnAnalysis) dom.railBtnAnalysis.addEventListener("click", () => {
            if (state.taskId) switchView("processing");
            else showToast("No active analysis in progress");
        });
        if (dom.railBtnResults) dom.railBtnResults.addEventListener("click", () => {
            if (state.resultData) switchView("results");
            else showToast("No results generated yet");
        });
        if (dom.railBtnHistory) dom.railBtnHistory.addEventListener("click", () => {
            renderRecentSources();
            showToast("Viewing session source history");
        });
        if (dom.railBtnExplore) dom.railBtnExplore.addEventListener("click", () => openExploreModal(0));
        if (dom.topHowItWorksBtn) dom.topHowItWorksBtn.addEventListener("click", () => openExploreModal(0));

        // Top 3-Step Navigation links
        if (dom.navStepIngest) dom.navStepIngest.addEventListener("click", () => switchView("idle"));
        if (dom.navStepAnalysis) dom.navStepAnalysis.addEventListener("click", () => {
            if (state.taskId) switchView("processing");
            else showToast("Start an analysis to view pipeline progress");
        });
        if (dom.navStepResults) dom.navStepResults.addEventListener("click", () => {
            if (state.resultData) switchView("results");
            else showToast("Complete an analysis first to view results");
        });

        // New Ingestion / Reset button
        if (dom.navResetBtn) dom.navResetBtn.addEventListener("click", () => {
            switchView("idle");
            validateInputState();
        });

        // Segmented Control (URL vs File vs Paste Transcript)
        if (dom.tabUrlBtn) dom.tabUrlBtn.addEventListener("click", () => setInputMode("url"));
        if (dom.tabFileBtn) dom.tabFileBtn.addEventListener("click", () => setInputMode("file"));
        if (dom.tabTextBtn) dom.tabTextBtn.addEventListener("click", () => setInputMode("text"));

        // Fallback banner actions
        if (dom.fallbackSwitchUploadBtn) dom.fallbackSwitchUploadBtn.addEventListener("click", () => setInputMode("file"));
        if (dom.fallbackSwitchPasteBtn) dom.fallbackSwitchPasteBtn.addEventListener("click", () => setInputMode("text"));

        // Textarea Input
        if (dom.transcriptPasteInput) {
            dom.transcriptPasteInput.addEventListener("input", validateInputState);
        }

        // URL Input
        if (dom.youtubeInput) {
            dom.youtubeInput.addEventListener("input", validateInputState);
            dom.youtubeInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter" && !dom.startBtn.disabled) {
                    startAnalysis();
                }
            });
        }
        if (dom.clearUrlBtn) {
            dom.clearUrlBtn.addEventListener("click", () => {
                dom.youtubeInput.value = "";
                validateInputState();
                dom.youtubeInput.focus();
            });
        }

        // File drop zone & browse
        if (dom.dropZone) {
            dom.dropZone.addEventListener("click", () => dom.fileInput.click());
            dom.dropZone.addEventListener("keydown", (e) => {
                if (e.key === " " || e.key === "Enter") {
                    e.preventDefault();
                    dom.fileInput.click();
                }
            });
        }
        if (dom.emptyStateBrowseBtn) {
            dom.emptyStateBrowseBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                dom.fileInput.click();
            });
        }
        if (dom.fileInput) {
            dom.fileInput.addEventListener("change", (e) => {
                if (e.target.files && e.target.files.length > 0) {
                    handleFileSelection(e.target.files[0]);
                }
            });
        }
        if (dom.removeFileBtn) dom.removeFileBtn.addEventListener("click", removeSelectedFile);

        // Page-wide Drag & Drop
        window.addEventListener("dragover", (e) => e.preventDefault());
        window.addEventListener("drop", (e) => e.preventDefault());

        if (dom.dropZone) {
            ["dragenter", "dragover"].forEach(evt => {
                dom.dropZone.addEventListener(evt, (e) => {
                    e.preventDefault();
                    dom.dropZone.classList.add("dragover");
                });
            });
            ["dragleave", "drop"].forEach(evt => {
                dom.dropZone.addEventListener(evt, (e) => {
                    e.preventDefault();
                    dom.dropZone.classList.remove("dragover");
                });
            });
            dom.dropZone.addEventListener("drop", (e) => {
                if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    handleFileSelection(e.dataTransfer.files[0]);
                }
            });
        }

        // Workflow Card Suggestions on Studio Page
        dom.workflowCards.forEach(card => {
            card.addEventListener("click", () => {
                const question = card.dataset.suggest;
                showToast(`Question prompt queued: "${question.slice(0, 36)}..."`);
                if (state.resultData) {
                    switchView("results");
                    dom.chatInput.value = question;
                    sendChatMessage(question);
                }
            });
        });

        // Start Analysis
        if (dom.startBtn) dom.startBtn.addEventListener("click", startAnalysis);
        if (dom.cancelAnalysisBtn) dom.cancelAnalysisBtn.addEventListener("click", cancelAnalysis);

        // Results Tab Strip
        dom.tabButtons.forEach(btn => {
            btn.addEventListener("click", () => switchTab(btn.dataset.tab));
        });
        window.addEventListener("resize", updateTabIndicator);

        // Section Copy Buttons
        if (dom.btnCopySummary) dom.btnCopySummary.addEventListener("click", () => copyToClipboard(state.resultData ? state.resultData.summary : "", "Executive summary copied!"));
        if (dom.btnCopyActions) dom.btnCopyActions.addEventListener("click", () => copyToClipboard(state.resultData ? state.resultData.action_items : "", "Action items copied!"));
        if (dom.btnCopyDecisions) dom.btnCopyDecisions.addEventListener("click", () => copyToClipboard(state.resultData ? state.resultData.key_decisions : "", "Key decisions copied!"));
        if (dom.btnCopyQuestions) dom.btnCopyQuestions.addEventListener("click", () => copyToClipboard(state.resultData ? state.resultData.open_questions : "", "Open questions copied!"));
        if (dom.copyTranscriptAction) dom.copyTranscriptAction.addEventListener("click", () => copyToClipboard(state.transcriptRaw, "Full transcript copied!"));
        if (dom.btnCopyAllTranscript) dom.btnCopyAllTranscript.addEventListener("click", () => copyToClipboard(state.transcriptRaw, "Full transcript copied!"));

        // Transcript Search & Navigation
        if (dom.transcriptSearch) dom.transcriptSearch.addEventListener("input", searchTranscript);
        if (dom.transcriptPrevMatch) dom.transcriptPrevMatch.addEventListener("click", jumpPrevMatch);
        if (dom.transcriptNextMatch) dom.transcriptNextMatch.addEventListener("click", jumpNextMatch);

        // Chat Form & Quick Suggestion Chips
        if (dom.chatForm) {
            dom.chatForm.addEventListener("submit", (e) => {
                e.preventDefault();
                sendChatMessage(dom.chatInput.value);
            });
        }
        if (dom.chatInput) {
            dom.chatInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    sendChatMessage(dom.chatInput.value);
                }
            });
        }
        if (dom.clearChatBtn) dom.clearChatBtn.addEventListener("click", clearChat);

        dom.suggestionChips.forEach(chip => {
            chip.addEventListener("click", () => {
                const question = chip.dataset.q;
                if (question) {
                    dom.chatInput.value = question;
                    sendChatMessage(question);
                }
            });
        });

        // Explore Modal controls
        if (dom.topHowItWorksBtn) dom.topHowItWorksBtn.addEventListener("click", () => openExploreModal(0));
        if (dom.exploreCloseBtn) dom.exploreCloseBtn.addEventListener("click", closeExploreModal);
        if (dom.explorePrevBtn) dom.explorePrevBtn.addEventListener("click", prevExploreStep);
        if (dom.exploreNextBtn) dom.exploreNextBtn.addEventListener("click", nextExploreStep);

        dom.exploreStepButtons.forEach((btn, idx) => {
            btn.addEventListener("click", () => {
                state.exploreStepIndex = idx;
                updateExploreSlide();
            });
        });

        // Keyboard navigation for Explore Modal
        window.addEventListener("keydown", (e) => {
            if (dom.exploreModal && !dom.exploreModal.classList.contains("hidden")) {
                if (e.key === "Escape") closeExploreModal();
                else if (e.key === "ArrowRight") nextExploreStep();
                else if (e.key === "ArrowLeft") prevExploreStep();
            }
        });
    }

    /* ═══════════════════════════════════════════════════════════════════════
       18. INITIALIZATION
       ═══════════════════════════════════════════════════════════════════════ */
    document.addEventListener("DOMContentLoaded", () => {
        // Initialize Theme from localStorage / prefers-color-scheme
        const initialTheme = getStoredTheme();
        setTheme(initialTheme, false);

        initSplashLoader();
        initThreeJS();
        init3DTilt();
        initEventListeners();
        loadRecentSources();
        validateInputState();
        updateTabIndicator();
    });

})();
