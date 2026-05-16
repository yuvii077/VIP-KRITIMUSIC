<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NOBITA MUSIC - README</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --blue-deep: #0d0d2b;
    --blue-dark: #050518;
    --blue-mid: #0a1628;
    --blue-bright: #00b4ff;
    --blue-glow: #0099ff;
    --blue-accent: #00d4ff;
    --purple-accent: #7b2fff;
    --gold: #ffd700;
    --gold-dim: #b8860b;
    --white: #ffffff;
    --text-muted: rgba(180,210,255,0.7);
    --border-blue: rgba(0,180,255,0.3);
    --border-glow: rgba(0,180,255,0.6);
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    background: var(--blue-dark);
    color: var(--white);
    font-family: 'Rajdhani', sans-serif;
    min-height: 100vh;
    overflow-x: hidden;
  }

  /* Animated starfield background */
  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
      radial-gradient(1px 1px at 10% 20%, rgba(0,180,255,0.8) 0%, transparent 100%),
      radial-gradient(1px 1px at 30% 60%, rgba(255,255,255,0.6) 0%, transparent 100%),
      radial-gradient(1px 1px at 50% 10%, rgba(0,180,255,0.5) 0%, transparent 100%),
      radial-gradient(1px 1px at 70% 80%, rgba(255,255,255,0.4) 0%, transparent 100%),
      radial-gradient(1px 1px at 90% 40%, rgba(0,180,255,0.6) 0%, transparent 100%),
      radial-gradient(1px 1px at 20% 90%, rgba(255,255,255,0.5) 0%, transparent 100%),
      radial-gradient(1px 1px at 80% 15%, rgba(0,180,255,0.7) 0%, transparent 100%),
      radial-gradient(1px 1px at 60% 50%, rgba(255,255,255,0.3) 0%, transparent 100%),
      radial-gradient(1px 1px at 40% 70%, rgba(0,180,255,0.4) 0%, transparent 100%),
      radial-gradient(1px 1px at 15% 45%, rgba(255,255,255,0.6) 0%, transparent 100%);
    z-index: 0;
  }

  /* Grid lines background */
  body::after {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(rgba(0,180,255,0.04) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,180,255,0.04) 1px, transparent 1px);
    background-size: 40px 40px;
    z-index: 0;
  }

  .container {
    position: relative;
    z-index: 1;
    max-width: 900px;
    margin: 0 auto;
    padding: 2rem 1.5rem 4rem;
  }

  /* ─── ANIMATED DIVIDER ─── */
  .neon-divider {
    width: 100%;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--blue-bright), var(--blue-accent), var(--blue-bright), transparent);
    margin: 1.5rem 0;
    position: relative;
    animation: divider-pulse 3s ease-in-out infinite;
  }
  @keyframes divider-pulse {
    0%, 100% { opacity: 0.6; }
    50% { opacity: 1; box-shadow: 0 0 20px var(--blue-bright); }
  }

  /* ─── TOP HEADER ─── */
  .top-header {
    text-align: center;
    padding: 2.5rem 1rem 1.5rem;
  }
  .mahakal-text {
    font-family: 'Orbitron', monospace;
    font-size: 13px;
    color: var(--gold);
    letter-spacing: 4px;
    text-shadow: 0 0 10px var(--gold-dim);
    animation: glow-gold 2s ease-in-out infinite alternate;
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
  }
  @keyframes glow-gold {
    from { text-shadow: 0 0 8px var(--gold-dim); }
    to { text-shadow: 0 0 20px var(--gold), 0 0 40px var(--gold-dim); }
  }

  .main-title {
    font-family: 'Orbitron', monospace;
    font-size: clamp(28px, 6vw, 52px);
    font-weight: 900;
    letter-spacing: 6px;
    color: var(--white);
    text-shadow: 0 0 30px var(--blue-bright), 0 0 60px var(--blue-glow);
    animation: title-glow 3s ease-in-out infinite alternate;
    margin-bottom: 6px;
  }
  @keyframes title-glow {
    from { text-shadow: 0 0 20px var(--blue-bright), 0 0 40px var(--blue-glow); }
    to { text-shadow: 0 0 40px var(--blue-accent), 0 0 80px var(--blue-bright), 0 0 120px var(--blue-glow); }
  }

  .sub-title {
    font-family: 'Orbitron', monospace;
    font-size: 13px;
    color: var(--blue-accent);
    letter-spacing: 8px;
    margin-bottom: 1.5rem;
    opacity: 0.9;
  }

  /* ─── BADGE ROW ─── */
  .badge-row {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 10px;
    margin: 1rem 0;
  }
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 16px;
    border-radius: 4px;
    font-family: 'Rajdhani', sans-serif;
    font-size: 13px;
    font-weight: 600;
    text-decoration: none;
    letter-spacing: 1px;
    transition: all 0.3s;
    position: relative;
  }
  .badge-gh {
    background: rgba(0,0,0,0.4);
    color: #fff;
    border: 1px solid rgba(255,255,255,0.25);
  }
  .badge-gh:hover { border-color: var(--white); box-shadow: 0 0 12px rgba(255,255,255,0.3); }
  .badge-star {
    background: rgba(255,215,0,0.1);
    color: var(--gold);
    border: 1px solid rgba(255,215,0,0.3);
  }
  .badge-fork {
    background: rgba(0,180,255,0.1);
    color: var(--blue-accent);
    border: 1px solid var(--border-blue);
  }

  /* ─── STATS GRID ─── */
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin: 1.5rem 0;
  }
  .stat-card {
    background: rgba(0,100,200,0.1);
    border: 1px solid var(--border-blue);
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
    position: relative;
    overflow: hidden;
    transition: all 0.3s;
  }
  .stat-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--blue-bright), transparent);
  }
  .stat-card:hover {
    border-color: var(--border-glow);
    box-shadow: 0 0 20px rgba(0,180,255,0.2);
  }
  .stat-icon { font-size: 22px; margin-bottom: 4px; }
  .stat-num { font-family: 'Orbitron', monospace; font-size: 14px; color: var(--blue-accent); }
  .stat-label { font-size: 11px; color: var(--text-muted); letter-spacing: 1px; margin-top: 2px; }

  /* ─── VISITOR COUNTER ─── */
  .visitor-section {
    text-align: center;
    margin: 1rem 0;
  }
  .visitor-label {
    font-family: 'Orbitron', monospace;
    font-size: 11px;
    color: var(--text-muted);
    letter-spacing: 3px;
    margin-bottom: 8px;
    text-transform: uppercase;
  }
  .visitor-count {
    display: inline-block;
    background: rgba(0,100,200,0.2);
    border: 1px solid var(--border-blue);
    border-radius: 6px;
    padding: 8px 24px;
    font-family: 'Orbitron', monospace;
    font-size: 22px;
    color: var(--blue-bright);
    letter-spacing: 4px;
    animation: count-glow 2s ease-in-out infinite alternate;
  }
  @keyframes count-glow {
    from { box-shadow: 0 0 10px rgba(0,180,255,0.2); }
    to { box-shadow: 0 0 25px rgba(0,180,255,0.5); }
  }

  /* ─── SECTION CARD ─── */
  .section-card {
    background: linear-gradient(135deg, rgba(0,30,80,0.6), rgba(0,15,50,0.8));
    border: 1px solid var(--border-blue);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 16px;
    position: relative;
    overflow: hidden;
    transition: all 0.3s;
  }
  .section-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--blue-bright), var(--blue-accent), transparent);
  }
  .section-card:hover {
    border-color: var(--border-glow);
    box-shadow: 0 0 30px rgba(0,180,255,0.15);
  }
  .section-title {
    font-family: 'Orbitron', monospace;
    font-size: 14px;
    font-weight: 700;
    color: var(--blue-accent);
    letter-spacing: 3px;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .section-title::before {
    content: '';
    display: inline-block;
    width: 3px;
    height: 16px;
    background: var(--blue-bright);
    border-radius: 2px;
    box-shadow: 0 0 8px var(--blue-bright);
  }

  /* ─── TEST BOT CARD ─── */
  .bot-card {
    background: linear-gradient(135deg, rgba(0,60,30,0.5), rgba(0,30,15,0.7));
    border: 1px solid rgba(0,220,100,0.3);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 16px;
    position: relative;
    overflow: hidden;
  }
  .bot-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0,220,100,0.8), transparent);
  }
  .bot-name {
    font-family: 'Orbitron', monospace;
    font-size: 16px;
    font-weight: 700;
    color: #00ff88;
    text-shadow: 0 0 15px rgba(0,255,136,0.5);
    letter-spacing: 2px;
  }
  .bot-sub { font-size: 13px; color: rgba(0,255,136,0.6); margin-top: 3px; }
  .btn-start {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: linear-gradient(135deg, #00c853, #00e676);
    color: #003300;
    padding: 10px 22px;
    border-radius: 6px;
    font-family: 'Orbitron', monospace;
    font-size: 12px;
    font-weight: 700;
    text-decoration: none;
    letter-spacing: 1px;
    transition: all 0.3s;
    box-shadow: 0 0 15px rgba(0,200,83,0.4);
  }
  .btn-start:hover { box-shadow: 0 0 25px rgba(0,200,83,0.7); transform: translateY(-1px); }

  /* ─── DEPLOY GRID ─── */
  .deploy-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
  }
  .deploy-box {
    background: rgba(0,20,60,0.6);
    border: 1px solid var(--border-blue);
    border-radius: 10px;
    padding: 1.25rem;
  }
  .deploy-box-title {
    font-family: 'Orbitron', monospace;
    font-size: 12px;
    color: var(--blue-accent);
    letter-spacing: 2px;
    margin-bottom: 12px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .deploy-icon { font-size: 18px; }
  .btn-heroku {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: linear-gradient(135deg, #6762a6, #430098);
    color: #fff;
    padding: 9px 18px;
    border-radius: 6px;
    font-family: 'Orbitron', monospace;
    font-size: 11px;
    font-weight: 700;
    text-decoration: none;
    letter-spacing: 1px;
    margin-top: 6px;
    transition: all 0.3s;
    box-shadow: 0 0 12px rgba(107,98,166,0.4);
    width: 100%;
    justify-content: center;
  }
  .btn-heroku:hover { box-shadow: 0 0 22px rgba(107,98,166,0.7); }
  .btn-yt {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: linear-gradient(135deg, #c62828, #f44336);
    color: #fff;
    padding: 9px 18px;
    border-radius: 6px;
    font-family: 'Orbitron', monospace;
    font-size: 11px;
    font-weight: 700;
    text-decoration: none;
    letter-spacing: 1px;
    margin-top: 8px;
    transition: all 0.3s;
    box-shadow: 0 0 12px rgba(244,67,54,0.4);
    width: 100%;
    justify-content: center;
  }
  .btn-yt:hover { box-shadow: 0 0 22px rgba(244,67,54,0.7); }

  /* ─── STEPS ─── */
  .step { display: flex; align-items: flex-start; gap: 10px; margin-bottom: 10px; }
  .step-num {
    min-width: 22px; height: 22px;
    background: var(--blue-glow);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-family: 'Orbitron', monospace;
    font-size: 10px;
    font-weight: 700;
    color: #fff;
    flex-shrink: 0;
    margin-top: 2px;
    box-shadow: 0 0 8px var(--blue-glow);
  }
  .step-text { font-size: 13px; color: var(--text-muted); line-height: 1.5; }
  .step-text code {
    background: rgba(0,180,255,0.1);
    border: 1px solid rgba(0,180,255,0.2);
    padding: 1px 6px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 12px;
    color: var(--blue-accent);
  }

  /* ─── CODE BLOCK ─── */
  .code-block {
    background: rgba(0,0,0,0.5);
    border: 1px solid rgba(0,180,255,0.2);
    border-left: 3px solid var(--blue-bright);
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-top: 12px;
    font-family: 'Courier New', monospace;
    font-size: 12px;
    overflow-x: auto;
  }
  .code-line { display: flex; gap: 10px; margin-bottom: 5px; line-height: 1.6; }
  .code-line:last-child { margin-bottom: 0; }
  .prompt { color: var(--blue-glow); user-select: none; }
  .cmd-text { color: #a8d8ff; }
  .comment { color: rgba(100,160,200,0.6); font-style: italic; }

  /* ─── CONTACT ─── */
  .contact-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
  }
  .contact-btn {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 16px;
    border-radius: 8px;
    text-decoration: none;
    font-family: 'Rajdhani', sans-serif;
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 1px;
    transition: all 0.3s;
  }
  .contact-tg {
    background: rgba(41,182,246,0.1);
    border: 1px solid rgba(41,182,246,0.3);
    color: #29b6f6;
  }
  .contact-tg:hover { box-shadow: 0 0 18px rgba(41,182,246,0.3); background: rgba(41,182,246,0.15); }
  .contact-ig {
    background: rgba(240,98,146,0.1);
    border: 1px solid rgba(240,98,146,0.3);
    color: #f06292;
  }
  .contact-ig:hover { box-shadow: 0 0 18px rgba(240,98,146,0.3); background: rgba(240,98,146,0.15); }
  .contact-icon { font-size: 22px; }

  /* ─── WARNING BANNER ─── */
  .warn-banner {
    text-align: center;
    font-family: 'Orbitron', monospace;
    font-size: 11px;
    color: #ff6b00;
    letter-spacing: 2px;
    padding: 8px;
    border: 1px solid rgba(255,107,0,0.3);
    border-radius: 6px;
    background: rgba(255,107,0,0.05);
    margin: 12px 0;
    animation: warn-flash 2s ease-in-out infinite;
  }
  @keyframes warn-flash {
    0%, 100% { border-color: rgba(255,107,0,0.3); }
    50% { border-color: rgba(255,107,0,0.7); box-shadow: 0 0 15px rgba(255,107,0,0.2); }
  }

  /* ─── FOOTER ─── */
  .footer {
    text-align: center;
    margin-top: 2rem;
    padding-top: 1rem;
  }
  .footer-text {
    font-family: 'Orbitron', monospace;
    font-size: 11px;
    color: var(--text-muted);
    letter-spacing: 2px;
  }
  .footer-powered {
    font-size: 12px;
    color: rgba(0,180,255,0.5);
    margin-top: 6px;
    letter-spacing: 1px;
  }

  @media (max-width: 600px) {
    .deploy-grid, .contact-grid, .stats-grid { grid-template-columns: 1fr; }
    .main-title { font-size: 28px; letter-spacing: 3px; }
  }
</style>
</head>
<body>

<div class="container">

  <!-- TOP DIVIDER -->
  <div class="neon-divider"></div>

  <!-- HEADER -->
  <div class="top-header">
    <div class="mahakal-text">🔱 &nbsp; JAI SHREE MAHAKAL &nbsp; 🔱</div>

    <div class="badge-row">
      <a href="https://github.com/vishalpandeynkp1" class="badge badge-gh">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z"/></svg>
        GitHub — vishalpandeynkp1
      </a>
      <span class="badge badge-star">⭐ Stars</span>
      <span class="badge badge-fork">🍴 Forks</span>
    </div>

    <div class="main-title">NOBITA MUSIC</div>
    <div class="sub-title">★ HEROKU + VPS ★</div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon">🎵</div>
        <div class="stat-num">MUSIC BOT</div>
        <div class="stat-label">TELEGRAM</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">☁️</div>
        <div class="stat-num">HEROKU</div>
        <div class="stat-label">NO BAN ISSUE</div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">🖥️</div>
        <div class="stat-num">VPS READY</div>
        <div class="stat-label">ANY SERVER</div>
      </div>
    </div>

    <div class="visitor-section">
      <div class="visitor-label">👁 Visitors</div>
      <div class="visitor-count">NOBITA-BOT-MAKER</div>
    </div>
  </div>

  <div class="neon-divider"></div>

  <!-- TEST BOT SECTION -->
  <div class="section-card">
    <div class="section-title">TEST BOT</div>
    <div class="bot-card">
      <div>
        <div class="bot-name">🅰🅰🆁🆄 🅼🆄🆂🅸🅲</div>
        <div class="bot-sub">Enhanced Telegram Music Experience</div>
      </div>
      <a href="https://t.me/aaru_music_xbot" class="btn-start">▶ START HERE</a>
    </div>
  </div>

  <div class="warn-banner">⚠️ PEHLE FORK KAR LO — THEN DEPLOY ⚠️</div>

  <div class="neon-divider"></div>

  <!-- DEPLOY SECTION -->
  <div class="section-card">
    <div class="section-title">DEPLOY OPTIONS</div>
    <div class="deploy-grid">

      <!-- HEROKU -->
      <div class="deploy-box">
        <div class="deploy-box-title">
          <span class="deploy-icon">☁️</span> HEROKU DEPLOY
        </div>
        <div style="font-size:13px;color:var(--text-muted);line-height:1.6;margin-bottom:6px">
          One-click Heroku deploy.<br>No ban issues guaranteed.
        </div>
        <a href="https://dashboard.heroku.com/new?template=https://github.com/vishalpandeynkp/VIPNOBITAMUSIC_REPO" class="btn-heroku">
          🚀 DEPLOY ON HEROKU
        </a>
        <a href="https://youtu.be/U8T5W3J1FNo" class="btn-yt">
          ▶ YOUTUBE TUTORIAL
        </a>
      </div>

      <!-- VPS -->
      <div class="deploy-box">
        <div class="deploy-box-title">
          <span class="deploy-icon">🖥️</span> VPS / LOCAL
        </div>
        <div class="step">
          <div class="step-num">1</div>
          <div class="step-text">Clone the repository</div>
        </div>
        <div class="step">
          <div class="step-num">2</div>
          <div class="step-text">Run <code>bash setup</code></div>
        </div>
        <div class="step">
          <div class="step-num">3</div>
          <div class="step-text">Edit <code>nano .env</code> → save with <code>Ctrl+X</code></div>
        </div>
        <div class="step">
          <div class="step-num">4</div>
          <div class="step-text">Install tmux & run <code>bash start</code></div>
        </div>
        <div class="step">
          <div class="step-num">5</div>
          <div class="step-text">Detach: <code>Ctrl+B</code> then <code>D</code></div>
        </div>
      </div>
    </div>

    <!-- CODE BLOCK -->
    <div class="code-block">
      <div class="code-line"><span class="prompt">$</span><span class="cmd-text">git clone https://github.com/vishalpandeynkp1/VIPNOBITAMUSIC_REPO</span></div>
      <div class="code-line"><span class="prompt">$</span><span class="cmd-text">cd VIPNOBITAMUSIC_REPO && bash setup</span></div>
      <div class="code-line"><span class="prompt">$</span><span class="cmd-text">nano .env &nbsp;&nbsp;<span class="comment"># Fill variables → Ctrl+X → Y → Enter</span></span></div>
      <div class="code-line"><span class="prompt">$</span><span class="cmd-text">sudo apt install tmux && tmux</span></div>
      <div class="code-line"><span class="prompt">$</span><span class="cmd-text">bash start &nbsp;<span class="comment"># Detach: Ctrl+B then D</span></span></div>
    </div>
  </div>

  <div class="neon-divider"></div>

  <!-- CONTACT SECTION -->
  <div class="section-card">
    <div class="section-title">CONTACT & SUPPORT</div>
    <div style="font-size:13px;color:var(--text-muted);margin-bottom:14px">
      Koi problem ho toh neeche contact karein:
    </div>
    <div class="contact-grid">
      <a href="https://telegram.me/ll_NOBITA_BOT_DEVLOPER_ll" class="contact-btn contact-tg">
        <span class="contact-icon">✈️</span>
        <div>
          <div style="font-size:13px;font-weight:700">Telegram</div>
          <div style="font-size:11px;opacity:0.7">NOBITA BOT MAKER</div>
        </div>
      </a>
      <a href="https://instagram.com/NOBITA_BOT_MAKER" class="contact-btn contact-ig">
        <span class="contact-icon">📸</span>
        <div>
          <div style="font-size:13px;font-weight:700">Instagram</div>
          <div style="font-size:11px;opacity:0.7">@NOBITA_BOT_MAKER</div>
        </div>
      </a>
    </div>
  </div>

  <div class="neon-divider"></div>

  <!-- FOOTER -->
  <div class="footer">
    <div class="footer-text">🔱 JAI SHREE MAHAKAL 🔱</div>
    <div class="footer-powered">POWERED BY NOBITA BOT MAKER</div>
  </div>

</div>
</body>
</html>
