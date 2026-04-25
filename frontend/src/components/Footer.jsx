import React from 'react';
import '../styles/global.css';

const Footer = () => {
  return (
    <footer className="footer-layout section" style={{ paddingBottom: '3rem', paddingTop: '3rem', borderTop: '1px solid var(--color-border)', marginTop: 'auto' }}>
      <div className="container">
        <div style={{ display: 'flex', flexDirection: 'row', justifyContent: 'space-between', flexWrap: 'wrap', gap: '2rem' }}>
          
          <div style={{ flex: '1', minWidth: '280px' }}>
            <h3 className="text-accent" style={{ marginBottom: '1rem', fontFamily: 'var(--font-display)', fontWeight: '600' }}>Saif Kharouf</h3>
            <p className="text-secondary" style={{ fontSize: '0.9rem', lineHeight: '1.6', maxWidth: '400px' }}>
              I am a professional photographer continuously pushing the boundaries of visual arts explicitly capturing premium automotive highlights seamlessly tracking beautiful nature boundaries globally.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '2rem' }}>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <h4 style={{ color: 'var(--color-text-primary)', marginBottom: '1rem' }}>Social Connections</h4>
              <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <a href="https://www.linkedin.com/in/saif-edeen-kharouf-181488209" target="_blank" rel="noopener noreferrer" className="text-muted" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', transition: 'var(--transition-fast)' }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"></path>
                    <rect x="2" y="9" width="4" height="12"></rect>
                    <circle cx="4" cy="4" r="2"></circle>
                  </svg>
                  LinkedIn
                </a>
                
                <a href="https://www.instagram.com/saifkharouf.cars/" target="_blank" rel="noopener noreferrer" className="text-muted" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', transition: 'var(--transition-fast)' }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <rect x="2" y="2" width="20" height="20" rx="5" ry="5"></rect>
                    <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"></path>
                    <line x1="17.5" y1="6.5" x2="17.51" y2="6.5"></line>
                  </svg>
                  Instagram
                </a>

                <a href="tel:+962793611134" className="text-muted" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', transition: 'var(--transition-fast)' }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>
                  </svg>
                  +962 79 361 1134
                </a>

                <a href="mailto:saifkharoouf@gmail.com" className="text-muted" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', transition: 'var(--transition-fast)' }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
                    <polyline points="22,6 12,13 2,6"></polyline>
                  </svg>
                  saifkharoouf@gmail.com
                </a>
              </nav>
            </div>
          </div>
        </div>
        
        <div style={{ marginTop: '3rem', paddingTop: '1.5rem', borderTop: '1px solid rgba(255,255,255,0.04)', textAlign: 'center' }}>
          <p className="text-muted" style={{ fontSize: '0.8rem' }}>© {new Date().getFullYear()} Saif Edeen Kharouf. All photographs inherently strictly reserved exclusively globally.</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
