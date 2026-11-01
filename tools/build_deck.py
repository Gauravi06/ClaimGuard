"""tools/build_deck.py

Builds the 10-slide ClaimGuard presentation deck using python-pptx.
Outputs ClaimGuard.pptx at the repository root.
"""
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "ClaimGuard.pptx"
FIGURES_DIR = REPO_ROOT / "docs" / "figures"

# Professional Color Palette
NAVY = RGBColor(15, 23, 42)        # Slate 900
DARK_BLUE = RGBColor(30, 41, 59)   # Slate 800
BLUE_ACCENT = RGBColor(37, 99, 235)# Blue 600
TEXT_MUTED = RGBColor(100, 116, 139)# Slate 500
CARD_BG = RGBColor(248, 250, 252)  # Slate 50
CARD_BORDER = RGBColor(226, 232, 240) # Slate 200
WHITE = RGBColor(255, 255, 255)
GREEN = RGBColor(22, 163, 74)      # Emerald 600
RED = RGBColor(220, 38, 38)        # Rose 600


def create_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    def add_header(slide, title_text, category_text="CLAIMGUARD • MLOPS PLATFORM"):
        # Category tracker
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.4))
        tf_cat = cat_box.text_frame
        tf_cat.word_wrap = True
        tf_cat.margin_left = tf_cat.margin_right = tf_cat.margin_top = tf_cat.margin_bottom = 0
        p_cat = tf_cat.paragraphs[0]
        p_cat.text = category_text.upper()
        p_cat.font.size = Pt(13)
        p_cat.font.bold = True
        p_cat.font.color.rgb = BLUE_ACCENT

        # Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11.7), Inches(0.8))
        tf = title_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.text = title_text
        p.font.size = Pt(36)
        p.font.bold = True
        p.font.color.rgb = NAVY

    # ==========================================
    # SLIDE 1: TITLE
    # ==========================================
    s1 = prs.slides.add_slide(blank_layout)
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = NAVY
    bg1.line.fill.background()

    t_box1 = s1.shapes.add_textbox(Inches(1.2), Inches(1.8), Inches(11.0), Inches(2.2))
    tf1 = t_box1.text_frame
    tf1.word_wrap = True
    p1 = tf1.paragraphs[0]
    p1.text = "ClaimGuard"
    p1.font.size = Pt(56)
    p1.font.bold = True
    p1.font.color.rgb = WHITE

    p1_sub = tf1.add_paragraph()
    p1_sub.text = "Insurance Fraud Detection Under Delayed Feedback"
    p1_sub.font.size = Pt(32)
    p1_sub.font.bold = True
    p1_sub.font.color.rgb = RGBColor(147, 197, 253)

    p1_desc = tf1.add_paragraph()
    p1_desc.text = "Real-Time XGBoost Scoring, Delayed-Label Simulation & Promotion Guardrails"
    p1_desc.font.size = Pt(22)
    p1_desc.font.color.rgb = RGBColor(203, 213, 225)

    meta_box = s1.shapes.add_textbox(Inches(1.2), Inches(5.2), Inches(11.0), Inches(1.2))
    tf_meta = meta_box.text_frame
    p_meta = tf_meta.paragraphs[0]
    p_meta.text = "Team ClaimGuard: Gauravi, Rashi, Om • Production MLOps Capstone"
    p_meta.font.size = Pt(20)
    p_meta.font.color.rgb = RGBColor(148, 163, 184)

    # ==========================================
    # SLIDE 2: THE PROBLEM (DELAYED LABELS)
    # ==========================================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "The Real-World Problem: Delayed Ground Truth")

    cards2 = [
        ("1. Investigation Latency (10–30 Days)",
         "Fraud is never known at submission. Adjusters, police reports, and legal inquiries take 10 to 30+ days to verify ground truth.",
         BLUE_ACCENT),
        ("2. Catastrophic Naive Retraining (0.0000 Recall)",
         "Assuming unobserved pending claims are legitimate causes 0.0000 recall across early cycles, missing 100% of positive fraud.",
         RED),
        ("3. Model Staleness & Drift Vulnerability",
         "Waiting months for complete settlement leaves models undefended against fast-drifting organized fraud syndicates.",
         DARK_BLUE),
    ]
    for i, (head, body, color) in enumerate(cards2):
        top = Inches(1.8 + i * 1.7)
        shape = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), top, Inches(11.733), Inches(1.4))
        shape.fill.solid()
        shape.fill.fore_color.rgb = CARD_BG
        shape.line.color.rgb = CARD_BORDER
        shape.line.width = Pt(1.5)

        tb = s2.shapes.add_textbox(Inches(1.1), top + Inches(0.15), Inches(11.1), Inches(1.1))
        tf = tb.text_frame
        tf.word_wrap = True
        p_h = tf.paragraphs[0]
        p_h.text = head
        p_h.font.size = Pt(22)
        p_h.font.bold = True
        p_h.font.color.rgb = color

        p_b = tf.add_paragraph()
        p_b.text = body
        p_b.font.size = Pt(20)
        p_b.font.color.rgb = DARK_BLUE

    # ==========================================
    # SLIDE 3: IDEA AND APPROACH
    # ==========================================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "The Approach: Decoupled Scoring & Chronological Replay")

    col_w = Inches(5.65)
    # Left Card
    sh_l = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), col_w, Inches(4.8))
    sh_l.fill.solid()
    sh_l.fill.fore_color.rgb = CARD_BG
    sh_l.line.color.rgb = BLUE_ACCENT
    sh_l.line.width = Pt(2)

    tb_l = s3.shapes.add_textbox(Inches(1.1), Inches(2.0), col_w - Inches(0.6), Inches(4.3))
    tf_l = tb_l.text_frame
    tf_l.word_wrap = True
    p = tf_l.paragraphs[0]
    p.text = "Subsystem A: Production Scoring"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = BLUE_ACCENT

    bullets_l = [
        "Real-Time Inference: <10ms scoring via pre-trained XGBoost champion.",
        "Local Attribution: Tree SHAP explains exact risk drivers per claim.",
        "Audit Log: Immutable scores and frozen initial predictions stored in DB."
    ]
    for b in bullets_l:
        pb = tf_l.add_paragraph()
        pb.text = "• " + b
        pb.font.size = Pt(20)
        pb.font.color.rgb = DARK_BLUE

    # Right Card
    sh_r = s3.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.85), Inches(1.8), col_w, Inches(4.8))
    sh_r.fill.solid()
    sh_r.fill.fore_color.rgb = CARD_BG
    sh_r.line.color.rgb = GREEN
    sh_r.line.width = Pt(2)

    tb_r = s3.shapes.add_textbox(Inches(7.15), Inches(2.0), col_w - Inches(0.6), Inches(4.3))
    tf_r = tb_r.text_frame
    tf_r.word_wrap = True
    p = tf_r.paragraphs[0]
    p.text = "Subsystem B: Simulation Pipeline"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = GREEN

    bullets_r = [
        "Discrete Time Engine: Simulated clock advances 7 days per step.",
        "Zero Target Leakage: Pending claims strictly hide true fraud labels.",
        "Settlement-Aware Retraining: Retrains on >=25 settled claims.",
        "Champion Promotion Gate: Deploys candidate only if holdout PR-AUC wins."
    ]
    for b in bullets_r:
        pb = tf_r.add_paragraph()
        pb.text = "• " + b
        pb.font.size = Pt(20)
        pb.font.color.rgb = DARK_BLUE

    # ==========================================
    # SLIDE 4: ARCHITECTURE (SHAPES DIAGRAM)
    # ==========================================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "System Architecture: Production & MLOps Pipeline")

    # Draw built vs planned components
    components = [
        # Col 1: Production
        ("React Dashboard\n(/claims, /submit, /simulation)", Inches(0.8), Inches(1.8), Inches(3.6), Inches(1.3), True),
        ("XGBoost Champion + SHAP\n(/api/claims, <10ms latency)", Inches(0.8), Inches(3.3), Inches(3.6), Inches(1.3), True),
        ("Persistent Store\n(PostgreSQL / SQLite claims DB)", Inches(0.8), Inches(4.8), Inches(3.6), Inches(1.3), True),
        # Col 2: Simulation
        ("Clock & Queue Engine\n(7-day steps, zero-leakage split)", Inches(4.8), Inches(1.8), Inches(3.6), Inches(1.3), True),
        ("3-Candidate Retraining\n(RF, LR, XGBoost every >=25 settled)", Inches(4.8), Inches(3.3), Inches(3.6), Inches(1.3), True),
        ("Promotion Gate & MLflow\n(Strict holdout PR-AUC comparison)", Inches(4.8), Inches(4.8), Inches(3.6), Inches(1.3), True),
        # Col 3: Monitoring & Future
        ("Telemetry & Monitoring\n(Prometheus /metrics + Grafana)", Inches(8.8), Inches(1.8), Inches(3.6), Inches(1.3), True),
        ("PSI Drift Detection\n(GET /api/sim/drift, ok/alert)", Inches(8.8), Inches(3.3), Inches(3.6), Inches(1.3), True),
        ("TODO: Airflow & DVC\n(dags/, .dvc - Designed Only)", Inches(8.8), Inches(4.8), Inches(3.6), Inches(1.3), False),
    ]

    for label, x, y, w, h, is_built in components:
        box = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
        box.fill.solid()
        box.fill.fore_color.rgb = CARD_BG if is_built else RGBColor(254, 242, 242)
        box.line.color.rgb = BLUE_ACCENT if is_built else RED
        box.line.width = Pt(2.0 if is_built else 1.5)

        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = label
        p.font.size = Pt(20)
        p.font.bold = True
        p.font.color.rgb = NAVY if is_built else RED
        p.alignment = PP_ALIGN.CENTER

    legend = s4.shapes.add_textbox(Inches(0.8), Inches(6.4), Inches(11.7), Inches(0.5))
    p_leg = legend.text_frame.paragraphs[0]
    p_leg.text = "Solid blue border = Built & Live on main  |  Dashed red border = Designed only (TODO)"
    p_leg.font.size = Pt(20)
    p_leg.font.bold = True
    p_leg.font.color.rgb = TEXT_MUTED

    # ==========================================
    # SLIDE 5: DATA (EMPIRICAL DATASETS)
    # ==========================================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "Dual Datasets: Real Ingestion & Synthetic Simulation")

    # Left Dataset
    sh_d1 = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(5.65), Inches(5.0))
    sh_d1.fill.solid()
    sh_d1.fill.fore_color.rgb = CARD_BG
    sh_d1.line.color.rgb = CARD_BORDER

    tb_d1 = s5.shapes.add_textbox(Inches(1.1), Inches(2.0), Inches(5.0), Inches(4.5))
    tf_d1 = tb_d1.text_frame
    tf_d1.word_wrap = True
    p = tf_d1.paragraphs[0]
    p.text = "Real Automobile Dataset"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = BLUE_ACCENT

    d1_items = [
        "Source: data/processed/carclaims_processed.csv",
        "Records: 15,419 verified claims (14 features).",
        "Fraud Rate: 5.99% (923 positive fraud cases).",
        "Champion Model: XGBoost achieves 0.1872 PR-AUC (3.1x random) and 90.27% recall at threshold 0.40.",
        "Role: Immediate intake inference and SHAP local attribution (<10ms latency)."
    ]
    for it in d1_items:
        pb = tf_d1.add_paragraph()
        pb.text = "• " + it
        pb.font.size = Pt(20)
        pb.font.color.rgb = DARK_BLUE

    # Right Dataset
    sh_d2 = s5.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.85), Inches(1.8), Inches(5.65), Inches(5.0))
    sh_d2.fill.solid()
    sh_d2.fill.fore_color.rgb = CARD_BG
    sh_d2.line.color.rgb = CARD_BORDER

    tb_d2 = s5.shapes.add_textbox(Inches(7.15), Inches(2.0), Inches(5.0), Inches(4.5))
    tf_d2 = tb_d2.text_frame
    tf_d2.word_wrap = True
    p = tf_d2.paragraphs[0]
    p.text = "Delayed-Label Simulation"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = GREEN

    d2_items = [
        "Source: backend/data/claims_sim.csv",
        "Records: 1,000 synthetic claims (13 features).",
        "Fraud Rate: 24.7% (247 positive fraud cases).",
        "Delay: 10–30 days uniform window (mean 19.63 days, seed 42) per claim.",
        "Timeline: 2015-01-01 to 2015-03-01.",
        "Role: Temporal replay, backlog simulation, and retraining trigger evaluation."
    ]
    for it in d2_items:
        pb = tf_d2.add_paragraph()
        pb.text = "• " + it
        pb.font.size = Pt(20)
        pb.font.color.rgb = DARK_BLUE

    # ==========================================
    # SLIDE 6: SIMULATION LOOP AND LEAKAGE GUARD
    # ==========================================
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "Simulation Loop & Strict Zero-Leakage Contract")

    cards6 = [
        ("Simulated Clock Engine",
         "Clock starts on 2015-01-01 and advances in 7-day increments (/api/sim/advance). Evaluates pending backlog vs settled cohorts dynamically at each step.",
         BLUE_ACCENT),
        ("Strict Target Leakage Guard",
         "Pending claims (/api/sim/pending) strictly hide is_fraud, investigation_days, and label_available_at. Zero target leakage guaranteed by contract.",
         GREEN),
        ("Retrain Threshold (>= 25 Settled)",
         "Retraining is locked until at least 25 claims settle. Prevents fitting degenerate estimators on unstable, single-class cohorts.",
         DARK_BLUE),
    ]
    for i, (head, body, color) in enumerate(cards6):
        top = Inches(1.8 + i * 1.7)
        shape = s6.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), top, Inches(11.733), Inches(1.4))
        shape.fill.solid()
        shape.fill.fore_color.rgb = CARD_BG
        shape.line.color.rgb = CARD_BORDER
        shape.line.width = Pt(1.5)

        tb = s6.shapes.add_textbox(Inches(1.1), top + Inches(0.15), Inches(11.1), Inches(1.1))
        tf = tb.text_frame
        tf.word_wrap = True
        p_h = tf.paragraphs[0]
        p_h.text = head
        p_h.font.size = Pt(22)
        p_h.font.bold = True
        p_h.font.color.rgb = color

        p_b = tf.add_paragraph()
        p_b.text = body
        p_b.font.size = Pt(20)
        p_b.font.color.rgb = DARK_BLUE

    # ==========================================
    # SLIDE 7: MODEL COMPARISON & PROMOTION RULE
    # ==========================================
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "Model Comparison & Candidate Promotion Gate")

    # Table on Left
    tb_table = s7.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(6.8), Inches(5.0))
    tf_t = tb_table.text_frame
    tf_t.word_wrap = True
    p = tf_t.paragraphs[0]
    p.text = "Dry-Run Retraining & Promotion Sequence"
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = NAVY

    t_lines = [
        "• Jan 08 & 15: Settled < 25 -> No retrain (v0)",
        "• Jan 22: 61 settled -> v1 promoted (PR-AUC 0.5769)",
        "• Jan 29: 167 settled -> v2 promoted (0.6451 > 0.2095)",
        "• Feb 05: 274 settled -> Rejected (0.5518 < 0.6164), stays v2",
        "• Feb 12: 384 settled -> v3 promoted (0.5458 > 0.4442)",
        "• Feb 19 & 26: Candidates lose to champion -> Retain v3!",
        "Rule: 6 retrains executed, exactly 3 promotions approved."
    ]
    for tl in t_lines:
        pb = tf_t.add_paragraph()
        pb.text = tl
        pb.font.size = Pt(20)
        pb.font.color.rgb = DARK_BLUE

    # Right side: Chart from docs/figures/ if available
    img_path = FIGURES_DIR / "settlement_pr_auc_over_time.png"
    if img_path.exists():
        s7.shapes.add_picture(str(img_path), Inches(7.8), Inches(2.0), width=Inches(4.8))
    else:
        # Fallback text box
        fb = s7.shapes.add_textbox(Inches(7.8), Inches(2.0), Inches(4.8), Inches(4.0))
        tf_fb = fb.text_frame
        p_fb = tf_fb.paragraphs[0]
        p_fb.text = "Settlement-Aware vs Naive:\n\n• Naive gets 0.0000 recall in cycles 1-4.\n• Settlement-aware achieves up to 8x recall advantage."
        p_fb.font.size = Pt(22)

    # ==========================================
    # SLIDE 8: MONITORING & OBSERVABILITY
    # ==========================================
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "Observability: MLflow, Prometheus & Drift Monitor")

    cards8 = [
        ("MLflow Experiment Tracking (Port 5000)",
         "Logs every retrain run: parameters (n_train, n_pending), candidate PR-AUC, champion PR-AUC, and binary promotion outcomes.",
         BLUE_ACCENT),
        ("Prometheus Telemetry (/metrics) & Grafana (Port 3001)",
         "Real-time gauges: claimguard_model_version, claimguard_settled_claims, claimguard_pending_backlog. Pre-provisioned Grafana dashboard on main.",
         GREEN),
        ("Feature Drift Monitoring (GET /api/sim/drift)",
         "Calculates Population Stability Index (PSI) across 13 contract features comparing training baseline to recent claims (status: ok | alert).",
         DARK_BLUE),
        ("TODO: Alerts & Automated Rollback (Designed Only)",
         "TODO: Automated PagerDuty/Slack webhooks on drift alert and automatic shadow-mode canary deployment.",
         RED),
    ]
    for i, (head, body, color) in enumerate(cards8):
        top = Inches(1.8 + i * 1.3)
        shape = s8.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), top, Inches(11.733), Inches(1.1))
        shape.fill.solid()
        shape.fill.fore_color.rgb = CARD_BG
        shape.line.color.rgb = CARD_BORDER
        shape.line.width = Pt(1.5)

        tb = s8.shapes.add_textbox(Inches(1.1), top + Inches(0.1), Inches(11.1), Inches(0.9))
        tf = tb.text_frame
        tf.word_wrap = True
        p_h = tf.paragraphs[0]
        p_h.text = head
        p_h.font.size = Pt(21)
        p_h.font.bold = True
        p_h.font.color.rgb = color

        p_b = tf.add_paragraph()
        p_b.text = body
        p_b.font.size = Pt(20)
        p_b.font.color.rgb = DARK_BLUE

    # ==========================================
    # SLIDE 9: LIVE DEMO PLAN
    # ==========================================
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, "Live 5-Minute Demonstration Plan & Browser Flow")

    demo_steps = [
        ("Tab 1: Simulation Dashboard", ":5173/simulation", "Start at Day 0: 19 pending, 0 settled, model_version = 0 (no model yet)."),
        ("Tab 2: Metrics Exposition", ":8000/metrics", "Advance clock 3 times -> 2015-01-22: 61 settled triggers v1 retrain (PR-AUC 0.5769)."),
        ("Tab 3: MLflow Tracking UI", ":5000", "Inspect retrain runs, holdout candidate comparisons, and promotion rejections."),
        ("Tab 4: Claim Scoring & SHAP", ":5173/claims/:id", "Show intake adjudication and interactive Tree SHAP red/green contribution bars."),
        ("Tab 5: Interactive API Docs", ":8000/docs", "Inspect REST contract, /api/sim/drift status, and settlement endpoints."),
    ]
    for i, (tab, port, desc) in enumerate(demo_steps):
        top = Inches(1.8 + i * 1.05)
        shape = s9.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), top, Inches(11.733), Inches(0.95))
        shape.fill.solid()
        shape.fill.fore_color.rgb = CARD_BG
        shape.line.color.rgb = BLUE_ACCENT if i == 0 else CARD_BORDER
        shape.line.width = Pt(1.5)

        tb = s9.shapes.add_textbox(Inches(1.0), top + Inches(0.08), Inches(11.3), Inches(0.8))
        tf = tb.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = f"{tab} ({port}): {desc}"
        p.font.size = Pt(20)
        p.font.bold = (i in (0, 1, 3))
        p.font.color.rgb = NAVY

    # ==========================================
    # SLIDE 10: STATUS, AUDIT & ROADMAP
    # ==========================================
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, "Engineering Audit: Completed vs. Future Roadmap")

    # Left: Done
    sh_dn = s10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8), Inches(5.65), Inches(5.0))
    sh_dn.fill.solid()
    sh_dn.fill.fore_color.rgb = CARD_BG
    sh_dn.line.color.rgb = GREEN
    sh_dn.line.width = Pt(2)

    tb_dn = s10.shapes.add_textbox(Inches(1.1), Inches(2.0), Inches(5.0), Inches(4.5))
    tf_dn = tb_dn.text_frame
    tf_dn.word_wrap = True
    p = tf_dn.paragraphs[0]
    p.text = "Completed & Live on Main"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = GREEN

    done_items = [
        "14-feature real-data XGBoost scoring (<10ms).",
        "Tree SHAP local attribution & frontend UI bars.",
        "Delayed-label clock engine with zero leakage.",
        "3-candidate retrain pipeline + promotion gate.",
        "Population Stability Index (PSI) drift monitoring.",
        "MLflow tracking, Prometheus /metrics & Grafana.",
        "135 automated unit & integration tests passing."
    ]
    for it in done_items:
        pb = tf_dn.add_paragraph()
        pb.text = "✓ " + it
        pb.font.size = Pt(20)
        pb.font.color.rgb = DARK_BLUE

    # Right: Future Work
    sh_fw = s10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.85), Inches(1.8), Inches(5.65), Inches(5.0))
    sh_fw.fill.solid()
    sh_fw.fill.fore_color.rgb = CARD_BG
    sh_fw.line.color.rgb = RED
    sh_fw.line.width = Pt(2)

    tb_fw = s10.shapes.add_textbox(Inches(7.15), Inches(2.0), Inches(5.0), Inches(4.5))
    tf_fw = tb_fw.text_frame
    tf_fw.word_wrap = True
    p = tf_fw.paragraphs[0]
    p.text = "Designed Only / Future Work (TODO)"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = RED

    todo_items = [
        "TODO: docs/DOCKER.md container user guide.",
        "TODO: Apache Airflow DAG integration (dags/).",
        "TODO: Data Version Control for raw data (.dvc).",
        "TODO: Production JWT / OAuth2 authentication.",
        "TODO: Real-time alerting webhooks on drift alerts.",
        "TODO: Automated shadow-mode canary deployment."
    ]
    for it in todo_items:
        pb = tf_fw.add_paragraph()
        pb.text = "• " + it
        pb.font.size = Pt(20)
        pb.font.color.rgb = DARK_BLUE

    # Save presentation
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUTPUT_PATH))
    print(f"Presentation successfully saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    create_deck()
