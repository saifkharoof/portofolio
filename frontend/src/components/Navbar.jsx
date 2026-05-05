import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import '../styles/global.css';

const Navbar = () => {
  const location = useLocation();
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [isAuth, setIsAuth] = useState(!!localStorage.getItem('auth_token'));

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Re-check auth state whenever the route changes (covers login/logout navigation)
  useEffect(() => {
    setIsAuth(!!localStorage.getItem('auth_token'));
  }, [location.pathname]);

  const currentPath = location.pathname;

  const handleNavClick = (e, targetPath) => {
    if (currentPath === '/chat' && targetPath !== '/chat' && sessionStorage.getItem('isChatActive') === 'true') {
      const confirmLeave = window.confirm("Are you sure you want to leave? This will delete your current chat.");
      if (!confirmLeave) {
        e.preventDefault();
        return;
      }
    }
    setMenuOpen(false);
  };

  return (
    <nav className={`navbar ${scrolled ? 'scrolled' : ''}`} id="navbar">
      <div className="nav-container container">
        <Link to="/" className="nav-logo" onClick={(e) => handleNavClick(e, '/')}>
          <span className="logo-mark">S</span>
          <span className="logo-text">Saif</span>
        </Link>

        <div className={`nav-links ${menuOpen ? 'open' : ''}`} id="nav-links">
          <Link 
            to="/" 
            className={`nav-link ${currentPath === '/' ? 'active' : ''}`}
            onClick={(e) => handleNavClick(e, '/')}
          >
            Gallery
          </Link>
          <Link 
            to="/chat" 
            className={`nav-link ${currentPath === '/chat' ? 'active' : ''}`}
            onClick={(e) => handleNavClick(e, '/chat')}
          >
            Chat
          </Link>
          <Link 
            to={isAuth ? '/admin' : '/login'} 
            className={`nav-link ${['/login', '/admin'].includes(currentPath) ? 'active' : ''}`}
            onClick={(e) => handleNavClick(e, isAuth ? '/admin' : '/login')}
          >
            {isAuth ? 'Dashboard' : 'Admin'}
          </Link>
        </div>

        <button 
          className="nav-toggle" 
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Toggle navigation"
        >
          <span></span>
          <span></span>
          <span></span>
        </button>
      </div>
    </nav>
  );
};

export default Navbar;
