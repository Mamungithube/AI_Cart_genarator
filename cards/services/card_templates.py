"""
Default ultra-luxury, executive professional card templates for instant generation and fallback
Supports multiple diverse industries (Executive Gold, Cyber Tech Cyan, Swiss Minimalist White, Emerald Corporate)
"""

TEMPLATES = [
    {
        "id": "luxury_dark_gold",
        "name": "Executive Obsidian & Gold",
        "primary_color": "#090d16",
        "accent_color": "#d4af37",
        "text_color": "#f8fafc",
        "css": """
.business-card {
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  font-family: 'Plus Jakarta Sans', 'Outfit', 'Inter', system-ui, -apple-system, sans-serif;
  position: relative;
  overflow: hidden;
  border-radius: 12px;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08), 0 25px 50px -12px rgba(0, 0, 0, 0.65);
}

/* Front Side */
.business-card.front {
  background: radial-gradient(circle at 85% 15%, rgba(212, 175, 55, 0.15), transparent 45%),
              linear-gradient(135deg, #070a11 0%, #111726 50%, #0a0f1d 100%);
  color: #f8fafc;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 32px 38px;
}

.business-card.front::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 3px;
  background: linear-gradient(90deg, #d4af37, #f6e05e, #aa771c);
}

.card-top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
  z-index: 10;
}

.card-logo-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.card-logo-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: linear-gradient(135deg, #d4af37, #aa771c);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #070a11;
  font-weight: 800;
  font-size: 18px;
  box-shadow: 0 6px 16px rgba(212, 175, 55, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.card-company-name {
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: #ffffff;
}

.card-company-tagline {
  font-size: 8.5px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #94a3b8;
  margin-top: 2px;
}

.card-badge {
  padding: 4px 12px;
  border-radius: 20px;
  background: rgba(212, 175, 55, 0.1);
  border: 1px solid rgba(212, 175, 55, 0.3);
  font-size: 9px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: #d4af37;
  font-weight: 700;
}

.card-main-info {
  margin-top: auto;
  margin-bottom: 16px;
  position: relative;
  z-index: 10;
}

.card-name {
  font-size: 23px;
  font-weight: 800;
  letter-spacing: -0.4px;
  color: #ffffff;
  line-height: 1.15;
  margin: 0;
}

.card-title {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #d4af37;
  margin-top: 4px;
}

.card-accent-bar {
  width: 28px;
  height: 2px;
  background: #d4af37;
  border-radius: 2px;
  margin-top: 8px;
}

.card-contact-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 24px;
  padding-top: 14px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  position: relative;
  z-index: 10;
}

.contact-item {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 9.5px;
  color: #cbd5e1;
  font-weight: 500;
  letter-spacing: 0.2px;
}

.contact-chip {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: rgba(212, 175, 55, 0.12);
  border: 1px solid rgba(212, 175, 55, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #d4af37;
}

.contact-chip svg {
  width: 11px;
  height: 11px;
}

/* Back Side */
.business-card.back {
  background: radial-gradient(circle at 50% 40%, rgba(212, 175, 55, 0.12), transparent 60%),
              linear-gradient(145deg, #070a11 0%, #111827 50%, #0a0f1d 100%);
  color: #f8fafc;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  text-align: center;
  position: relative;
}

.back-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  z-index: 2;
  width: 100%;
}

.back-logo-big {
  width: 54px;
  height: 54px;
  border-radius: 14px;
  background: linear-gradient(135deg, #d4af37, #aa771c);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #070a11;
  font-weight: 900;
  font-size: 26px;
  box-shadow: 0 10px 25px rgba(212, 175, 55, 0.35);
  border: 1px solid rgba(255, 255, 255, 0.25);
  margin-bottom: 10px;
}

.back-brand-title {
  font-size: 17px;
  font-weight: 800;
  letter-spacing: 3.5px;
  text-transform: uppercase;
  color: #ffffff;
  margin: 0;
}

.back-brand-subtitle {
  font-size: 8.5px;
  letter-spacing: 2.5px;
  text-transform: uppercase;
  color: #d4af37;
  margin-top: 3px;
  margin-bottom: 12px;
}

.back-qr-box {
  padding: 7px;
  background: #ffffff;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 20px rgba(0,0,0,0.4);
  border: 1px solid rgba(212, 175, 55, 0.4);
  margin-bottom: 6px;
}

.back-qr-box svg {
  width: 48px;
  height: 48px;
}

.back-qr-label {
  font-size: 7px;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: #d4af37;
  margin-bottom: 10px;
}

.back-website-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 14px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  font-size: 9px;
  letter-spacing: 1.2px;
  color: #cbd5e1;
  text-transform: lowercase;
}
""",
        "front_html": """
<div class="business-card front">
  <div class="card-top-row">
    <div class="card-logo-area">
      <div class="card-logo-icon">{initial}</div>
      <div>
        <div class="card-company-name">{company}</div>
        <div class="card-company-tagline">{tagline}</div>
      </div>
    </div>
    <div class="card-badge">VERIFIED</div>
  </div>
  
  <div class="card-main-info">
    <h2 class="card-name">{name}</h2>
    <div class="card-title">{title}</div>
    <div class="card-accent-bar"></div>
  </div>
  
  <div class="card-contact-grid">
    <div class="contact-item">
      <span class="contact-chip">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>
      </span>
      <span>{phone}</span>
    </div>
    <div class="contact-item">
      <span class="contact-chip">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>
      </span>
      <span>{email}</span>
    </div>
    <div class="contact-item">
      <span class="contact-chip">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
      </span>
      <span>{website}</span>
    </div>
    <div class="contact-item">
      <span class="contact-chip">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
      </span>
      <span>{address}</span>
    </div>
  </div>
</div>
""",
        "back_html": """
<div class="business-card back">
  <div class="back-content">
    <div class="back-logo-big">{initial}</div>
    <h1 class="back-brand-title">{company}</h1>
    <div class="back-brand-subtitle">{tagline}</div>
    
    <div class="back-qr-box">
      <svg viewBox="0 0 100 100" fill="#070a11">
        <rect x="5" y="5" width="25" height="25" fill="#070a11" />
        <rect x="10" y="10" width="15" height="15" fill="#ffffff" />
        <rect x="14" y="14" width="7" height="7" fill="#070a11" />
        <rect x="70" y="5" width="25" height="25" fill="#070a11" />
        <rect x="75" y="10" width="15" height="15" fill="#ffffff" />
        <rect x="79" y="14" width="7" height="7" fill="#070a11" />
        <rect x="5" y="70" width="25" height="25" fill="#070a11" />
        <rect x="10" y="75" width="15" height="15" fill="#ffffff" />
        <rect x="14" y="79" width="7" height="7" fill="#070a11" />
        <rect x="36" y="8" width="6" height="6" fill="#070a11"/>
        <rect x="46" y="14" width="8" height="8" fill="#070a11"/>
        <rect x="36" y="24" width="10" height="6" fill="#070a11"/>
        <rect x="40" y="40" width="20" height="20" fill="#070a11"/>
        <rect x="68" y="44" width="8" height="12" fill="#070a11"/>
        <rect x="70" y="72" width="18" height="18" fill="#070a11"/>
      </svg>
    </div>
    <div class="back-qr-label">SCAN TO CONNECT</div>
    
    <div class="back-website-pill">{website}</div>
  </div>
</div>
"""
    },
    {
        "id": "cyber_navy_cyan",
        "name": "Cyber Tech Midnight Navy & Cyan",
        "primary_color": "#0a1128",
        "accent_color": "#00d2ff",
        "text_color": "#ffffff",
        "css": """
.business-card {
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  position: relative;
  overflow: hidden;
  border-radius: 12px;
  -webkit-font-smoothing: antialiased;
  box-shadow: inset 0 0 0 1px rgba(0, 210, 255, 0.15), 0 25px 50px -12px rgba(0, 0, 0, 0.7);
}

.business-card.front {
  background: radial-gradient(circle at 15% 15%, rgba(0, 210, 255, 0.12), transparent 40%),
              radial-gradient(circle at 90% 85%, rgba(0, 114, 255, 0.1), transparent 45%),
              linear-gradient(135deg, #060b19 0%, #0a1329 50%, #080e22 100%);
  color: #ffffff;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 32px 38px;
}

.business-card.front::before {
  content: '';
  position: absolute;
  top: 0; right: 0; width: 140px; height: 140px;
  background: radial-gradient(circle, rgba(0, 210, 255, 0.18) 0%, transparent 70%);
  pointer-events: none;
}

.cyber-top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: relative;
  z-index: 10;
}

.cyber-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.cyber-logo-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: linear-gradient(135deg, #00d2ff, #0072ff);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #060b19;
  font-weight: 900;
  font-size: 18px;
  box-shadow: 0 0 18px rgba(0, 210, 255, 0.4);
}

.cyber-company-name {
  font-size: 14px;
  font-weight: 800;
  letter-spacing: 1.8px;
  text-transform: uppercase;
  color: #ffffff;
}

.cyber-tagline {
  font-size: 8.5px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #38bdf8;
  margin-top: 2px;
}

.cyber-tech-badge {
  padding: 4px 12px;
  border-radius: 6px;
  background: rgba(0, 210, 255, 0.1);
  border: 1px solid rgba(0, 210, 255, 0.3);
  font-size: 8.5px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: #00d2ff;
  font-weight: 700;
}

.cyber-main-info {
  margin-top: auto;
  margin-bottom: 16px;
  position: relative;
  z-index: 10;
}

.cyber-name {
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.4px;
  color: #ffffff;
  line-height: 1.15;
  margin: 0;
}

.cyber-title {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 2.2px;
  text-transform: uppercase;
  color: #00d2ff;
  margin-top: 5px;
}

.cyber-accent-bar {
  width: 32px;
  height: 2px;
  background: linear-gradient(90deg, #00d2ff, #0072ff);
  border-radius: 2px;
  margin-top: 8px;
}

.cyber-contact-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 24px;
  padding-top: 14px;
  border-top: 1px solid rgba(0, 210, 255, 0.12);
  position: relative;
  z-index: 10;
}

.cyber-contact-item {
  display: flex;
  align-items: center;
  gap: 9px;
  font-size: 9.5px;
  color: #cbd5e1;
  font-weight: 500;
}

.cyber-chip {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: rgba(0, 210, 255, 0.1);
  border: 1px solid rgba(0, 210, 255, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #00d2ff;
}

.cyber-chip svg {
  width: 11px;
  height: 11px;
}

/* Back Side */
.business-card.back {
  background: radial-gradient(circle at 50% 50%, rgba(0, 210, 255, 0.12), transparent 60%),
              linear-gradient(135deg, #060b19 0%, #0a1329 100%);
  color: #ffffff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  text-align: center;
  position: relative;
}

.cyber-back-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  z-index: 2;
  width: 100%;
}

.cyber-back-logo {
  width: 54px;
  height: 54px;
  border-radius: 14px;
  background: linear-gradient(135deg, #00d2ff, #0072ff);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #060b19;
  font-weight: 900;
  font-size: 26px;
  box-shadow: 0 0 25px rgba(0, 210, 255, 0.5);
  margin-bottom: 10px;
}

.cyber-back-title {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: 3.5px;
  text-transform: uppercase;
  color: #ffffff;
  margin: 0;
}

.cyber-back-subtitle {
  font-size: 8.5px;
  letter-spacing: 2.5px;
  text-transform: uppercase;
  color: #00d2ff;
  margin-top: 3px;
  margin-bottom: 12px;
}

.cyber-back-qr {
  padding: 7px;
  background: #ffffff;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 20px rgba(0,0,0,0.5);
  border: 1px solid rgba(0, 210, 255, 0.4);
  margin-bottom: 6px;
}

.cyber-back-qr svg {
  width: 48px;
  height: 48px;
}

.cyber-back-tag {
  font-size: 7px;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: #00d2ff;
  margin-bottom: 10px;
}

.cyber-website-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 14px;
  border-radius: 20px;
  background: rgba(0, 210, 255, 0.08);
  border: 1px solid rgba(0, 210, 255, 0.25);
  font-size: 9px;
  letter-spacing: 1.2px;
  color: #38bdf8;
  text-transform: lowercase;
}
""",
        "front_html": """
<div class="business-card front">
  <div class="cyber-top-row">
    <div class="cyber-brand">
      <div class="cyber-logo-icon">{initial}</div>
      <div>
        <div class="cyber-company-name">{company}</div>
        <div class="cyber-tagline">{tagline}</div>
      </div>
    </div>
    <div class="cyber-tech-badge">TECH NODE</div>
  </div>
  
  <div class="cyber-main-info">
    <h2 class="cyber-name">{name}</h2>
    <div class="cyber-title">{title}</div>
    <div class="cyber-accent-bar"></div>
  </div>
  
  <div class="cyber-contact-grid">
    <div class="cyber-contact-item">
      <span class="cyber-chip">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>
      </span>
      <span>{phone}</span>
    </div>
    <div class="cyber-contact-item">
      <span class="cyber-chip">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>
      </span>
      <span>{email}</span>
    </div>
    <div class="cyber-contact-item">
      <span class="cyber-chip">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
      </span>
      <span>{website}</span>
    </div>
    <div class="cyber-contact-item">
      <span class="cyber-chip">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
      </span>
      <span>{address}</span>
    </div>
  </div>
</div>
""",
        "back_html": """
<div class="business-card back">
  <div class="cyber-back-content">
    <div class="cyber-back-logo">{initial}</div>
    <h1 class="cyber-back-title">{company}</h1>
    <div class="cyber-back-subtitle">{tagline}</div>
    
    <div class="cyber-back-qr">
      <svg viewBox="0 0 100 100" fill="#060b19">
        <rect x="5" y="5" width="25" height="25" fill="#060b19" />
        <rect x="10" y="10" width="15" height="15" fill="#ffffff" />
        <rect x="14" y="14" width="7" height="7" fill="#060b19" />
        <rect x="70" y="5" width="25" height="25" fill="#060b19" />
        <rect x="75" y="10" width="15" height="15" fill="#ffffff" />
        <rect x="79" y="14" width="7" height="7" fill="#060b19" />
        <rect x="5" y="70" width="25" height="25" fill="#060b19" />
        <rect x="10" y="75" width="15" height="15" fill="#ffffff" />
        <rect x="14" y="79" width="7" height="7" fill="#060b19" />
        <rect x="36" y="8" width="6" height="6" fill="#060b19"/>
        <rect x="46" y="14" width="8" height="8" fill="#060b19"/>
        <rect x="36" y="24" width="10" height="6" fill="#060b19"/>
        <rect x="40" y="40" width="20" height="20" fill="#060b19"/>
        <rect x="68" y="44" width="8" height="12" fill="#060b19"/>
        <rect x="70" y="72" width="18" height="18" fill="#060b19"/>
      </svg>
    </div>
    <div class="cyber-back-tag">SCAN TO CONNECT</div>
    
    <div class="cyber-website-pill">{website}</div>
  </div>
</div>
"""
    },
    {
        "id": "swiss_minimalist_slate",
        "name": "Swiss Architectural Minimalist White",
        "primary_color": "#ffffff",
        "accent_color": "#0f172a",
        "text_color": "#0f172a",
        "css": """
.business-card {
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  font-family: 'Plus Jakarta Sans', 'Inter', system-ui, sans-serif;
  position: relative;
  overflow: hidden;
  border-radius: 12px;
  -webkit-font-smoothing: antialiased;
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.08), 0 20px 45px -10px rgba(0, 0, 0, 0.35);
}

.business-card.front {
  background: #ffffff;
  color: #0f172a;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 34px 40px;
}

.swiss-top-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.swiss-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.swiss-logo-icon {
  width: 34px;
  height: 34px;
  border-radius: 6px;
  background: #0f172a;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-weight: 800;
  font-size: 16px;
}

.swiss-company-name {
  font-size: 13.5px;
  font-weight: 800;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: #0f172a;
}

.swiss-tagline {
  font-size: 8px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #64748b;
  margin-top: 1px;
}

.swiss-badge {
  padding: 4px 10px;
  border-radius: 4px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  font-size: 8.5px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: #334155;
  font-weight: 700;
}

.swiss-main-info {
  margin-top: auto;
  margin-bottom: 16px;
}

.swiss-name {
  font-size: 24px;
  font-weight: 800;
  letter-spacing: -0.5px;
  color: #0f172a;
  line-height: 1.1;
  margin: 0;
}

.swiss-title {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #2563eb;
  margin-top: 5px;
}

.swiss-accent-bar {
  width: 26px;
  height: 2px;
  background: #2563eb;
  margin-top: 8px;
  border-radius: 2px;
}

.swiss-contact-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 24px;
  padding-top: 14px;
  border-top: 1px solid #e2e8f0;
}

.swiss-contact-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 9.5px;
  color: #334155;
  font-weight: 500;
}

.swiss-chip {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #2563eb;
}

.swiss-chip svg {
  width: 10px;
  height: 10px;
}

/* Back Side */
.business-card.back {
  background: #0f172a;
  color: #ffffff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  text-align: center;
  position: relative;
}

.swiss-back-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
}

.swiss-back-logo {
  width: 52px;
  height: 52px;
  border-radius: 12px;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #0f172a;
  font-weight: 900;
  font-size: 24px;
  margin-bottom: 10px;
}

.swiss-back-title {
  font-size: 17px;
  font-weight: 800;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: #ffffff;
  margin: 0;
}

.swiss-back-subtitle {
  font-size: 8.5px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #94a3b8;
  margin-top: 3px;
  margin-bottom: 12px;
}

.swiss-back-qr {
  padding: 7px;
  background: #ffffff;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  margin-bottom: 6px;
}

.swiss-back-qr svg {
  width: 46px;
  height: 46px;
}

.swiss-back-tag {
  font-size: 7px;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: #94a3b8;
  margin-bottom: 10px;
}

.swiss-website-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 14px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  font-size: 9px;
  letter-spacing: 1px;
  color: #cbd5e1;
  text-transform: lowercase;
}
""",
        "front_html": """
<div class="business-card front">
  <div class="swiss-top-row">
    <div class="swiss-brand">
      <div class="swiss-logo-icon">{initial}</div>
      <div>
        <div class="swiss-company-name">{company}</div>
        <div class="swiss-tagline">{tagline}</div>
      </div>
    </div>
    <div class="swiss-badge">STUDIO</div>
  </div>
  
  <div class="swiss-main-info">
    <h2 class="swiss-name">{name}</h2>
    <div class="swiss-title">{title}</div>
    <div class="swiss-accent-bar"></div>
  </div>
  
  <div class="swiss-contact-grid">
    <div class="swiss-contact-item">
      <span class="swiss-chip">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>
      </span>
      <span>{phone}</span>
    </div>
    <div class="swiss-contact-item">
      <span class="swiss-chip">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>
      </span>
      <span>{email}</span>
    </div>
    <div class="swiss-contact-item">
      <span class="swiss-chip">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="2" y1="12" x2="22" y2="12"></line><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path></svg>
      </span>
      <span>{website}</span>
    </div>
    <div class="swiss-contact-item">
      <span class="swiss-chip">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path><circle cx="12" cy="10" r="3"></circle></svg>
      </span>
      <span>{address}</span>
    </div>
  </div>
</div>
""",
        "back_html": """
<div class="business-card back">
  <div class="swiss-back-content">
    <div class="swiss-back-logo">{initial}</div>
    <h1 class="swiss-back-title">{company}</h1>
    <div class="swiss-back-subtitle">{tagline}</div>
    
    <div class="swiss-back-qr">
      <svg viewBox="0 0 100 100" fill="#0f172a">
        <rect x="5" y="5" width="25" height="25" fill="#0f172a" />
        <rect x="10" y="10" width="15" height="15" fill="#ffffff" />
        <rect x="14" y="14" width="7" height="7" fill="#0f172a" />
        <rect x="70" y="5" width="25" height="25" fill="#0f172a" />
        <rect x="75" y="10" width="15" height="15" fill="#ffffff" />
        <rect x="79" y="14" width="7" height="7" fill="#0f172a" />
        <rect x="5" y="70" width="25" height="25" fill="#0f172a" />
        <rect x="10" y="75" width="15" height="15" fill="#ffffff" />
        <rect x="14" y="79" width="7" height="7" fill="#0f172a" />
        <rect x="36" y="8" width="6" height="6" fill="#0f172a"/>
        <rect x="46" y="14" width="8" height="8" fill="#0f172a"/>
        <rect x="36" y="24" width="10" height="6" fill="#0f172a"/>
        <rect x="40" y="40" width="20" height="20" fill="#0f172a"/>
        <rect x="68" y="44" width="8" height="12" fill="#0f172a"/>
        <rect x="70" y="72" width="18" height="18" fill="#0f172a"/>
      </svg>
    </div>
    <div class="swiss-back-tag">SCAN TO CONNECT</div>
    
    <div class="swiss-website-pill">{website}</div>
  </div>
</div>
"""
    }
]

def select_template_for_data(data):
    """
    Intelligently selects a template based on company, title, or name keywords
    """
    import re
    text = (f"{data.get('title', '')} {data.get('company', '')} {data.get('name', '')}").lower()
    
    # 1. Tech / Software / AI -> Cyber Tech Midnight Navy & Cyan
    if re.search(r'\b(software|developer|engineer|tech|ai|cyber|data|cloud|system|devops|fullstack)\b', text):
        return TEMPLATES[1]
        
    # 2. Minimalist / Design / Architecture / Studio -> Swiss Minimalist White
    if re.search(r'\b(architect|design|designer|studio|creative|art|artist|minimal|white|swiss)\b', text):
        return TEMPLATES[2]
        
    # 3. Default to Executive Obsidian & Gold for C-Level / Directors / Legal / Finance
    return TEMPLATES[0]


def render_fallback_card(data):
    """Fills the most appropriate template with extracted values"""
    tpl = select_template_for_data(data)
    name = data.get('name') or "Executive Member"
    title = data.get('title') or "Professional"
    company = data.get('company') or "Enterprise"
    tagline = data.get('tagline') or "ENGINEERING EXCELLENCE"
    phone = data.get('phone') or ""
    email = data.get('email') or ""
    website = data.get('website') or ""
    address = data.get('address') or ""
    initial = (company[:1] if company else (name[:1] if name else "C")).upper()

    front = tpl["front_html"].format(
        initial=initial,
        company=company,
        tagline=tagline,
        name=name,
        title=title,
        phone=phone,
        email=email,
        website=website,
        address=address
    )

    back = tpl["back_html"].format(
        initial=initial,
        company=company,
        tagline=tagline,
        website=website
    )

    return {
        "title": f"{name} - {company}",
        "card_data": {
            "name": name,
            "title": title,
            "company": company,
            "tagline": tagline,
            "phone": phone,
            "email": email,
            "website": website,
            "address": address,
            "primary_color": tpl["primary_color"],
            "accent_color": tpl["accent_color"]
        },
        "front_html": front.strip(),
        "back_html": back.strip(),
        "css": tpl["css"].strip(),
        "bot_reply": f"Crafted an executive {tpl['name']} business card design with front and back sides."
    }
