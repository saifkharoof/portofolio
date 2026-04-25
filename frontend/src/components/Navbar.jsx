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

  return (
    <nav className={`navbar ${scrolled ? 'scrolled' : ''}`} id="navbar">
      <div className="nav-container container">
        <Link to="/" className="nav-logo">
          <span className="logo-mark">S</span>
          <span className="logo-text">Saif</span>
        </Link>

        <div className={`nav-links ${menuOpen ? 'open' : ''}`} id="nav-links">
          <Link 
            to="/" 
            className={`nav-link ${currentPath === '/' ? 'active' : ''}`}
            onClick={() => setMenuOpen(false)}
          >
            Gallery
          </Link>
          <Link 
            to={isAuth ? '/admin' : '/login'} 
            className={`nav-link ${['/login', '/admin'].includes(currentPath) ? 'active' : ''}`}
            onClick={() => setMenuOpen(false)}
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
