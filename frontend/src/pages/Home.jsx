import React, { useState, useEffect } from 'react';
import { fetchAPI } from '../api/client';
import ImageCard from '../components/ImageCard';
import '../styles/Home.css';

const Home = () => {
  const [images, setImages] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const [currentTag, setCurrentTag] = useState('all');
  const [allTags, setAllTags] = useState([]);
  
  const [skip, setSkip] = useState(0);
  const limit = 20;
  
  const [lightboxData, setLightboxData] = useState(null);

  const [currentCategory, setCurrentCategory] = useState('all');

  useEffect(() => {
    loadImages(0, 'all', 'all', false);
  }, []); // Initial load

  const loadImages = async (newSkip, tag, category, append, isCategoryChange = false) => {
    try {
      if (!append) setLoading(true);
      
      const tagParam = tag !== 'all' ? `&tag=${tag}` : '';
      const catParam = category !== 'all' ? `&category=${category}` : '';
      const data = await fetchAPI(`/api/images/?skip=${newSkip}&limit=${limit}${tagParam}${catParam}`);
      
      const newImages = append ? [...images, ...data.images] : data.images;
      setImages(newImages);
      setTotal(data.total);
      
      // Only recompute global tags and reset active tag when the category changes
      if (isCategoryChange || (newSkip === 0 && tag === 'all' && category === 'all' && !append)) {
        const uniqueTags = new Set(newImages.flatMap(img => img.tags || []));
        setAllTags(Array.from(uniqueTags).sort());
        if (isCategoryChange) {
          setCurrentTag('all');
        }
      }
      
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTagClick = (tag) => {
    setCurrentTag(tag);
    setSkip(0);
    loadImages(0, tag, currentCategory, false, false);
  };

  const handleCategoryClick = (cat) => {
    setCurrentCategory(cat);
    setSkip(0);
    setCurrentTag('all');
    loadImages(0, 'all', cat, false, true);
  };

  const loadMore = () => {
    const nextSkip = skip + limit;
    setSkip(nextSkip);
    loadImages(nextSkip, currentTag, currentCategory, true);
  };

  const openLightbox = (image) => {
    setLightboxData(image);
    document.body.style.overflow = 'hidden';
  };

  const closeLightbox = () => {
    setLightboxData(null);
    document.body.style.overflow = '';
  };

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') closeLightbox();
    };
    if (lightboxData) window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [lightboxData]);

  return (
    <>
      {/* Hero Section */}
      <section className="hero" id="hero">
        <div className="hero-bg-glow"></div>
        <div className="hero-content container">
          <div className="hero-badge animate-fade-in-up">
            <span className="badge-dot"></span>
            Photography & API Development
          </div>
          <h1 className="hero-title animate-fade-in-up stagger-1">
            Capturing moments,<br />
            <span className="text-accent">crafting APIs.</span>
          </h1>
          <p className="hero-subtitle animate-fade-in-up stagger-2">
            I'm Saif — a developer who sees the world through two lenses: the camera and the code editor.
            Explore my photography portfolio and the technology behind it.
          </p>
          <div className="hero-actions animate-fade-in-up stagger-3">
            <a href="#gallery" className="btn btn-primary btn-lg">View Gallery</a>
          </div>
          <div className="hero-stats animate-fade-in-up stagger-4">
            <div className="stat">
              <span className="stat-value" id="stat-photos">{total}</span>
              <span className="stat-label">Photos</span>
            </div>
            <div className="stat-divider"></div>
            <div className="stat">
              <span className="stat-value">FastAPI</span>
              <span className="stat-label">Backend</span>
            </div>
            <div className="stat-divider"></div>
            <div className="stat">
              <span className="stat-value">MongoDB</span>
              <span className="stat-label">Database</span>
            </div>
          </div>
        </div>
      </section>

      {/* Gallery Section */}
      <section className="gallery-section section" id="gallery">
        <div className="container">
          <div className="section-header animate-fade-in-up">
            <span className="section-tag">Portfolio</span>
            <h2 className="section-title">Selected Works</h2>
            <p className="section-subtitle">A collection of my photography — moments frozen in time.</p>
          </div>

          {/* General Filters */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '2.5rem' }}>
            <div className="filter-bar animate-fade-in-up stagger-1" style={{ justifyContent: 'center' }}>
              <button className={`filter-chip ${currentCategory === 'all' ? 'active' : ''}`} onClick={() => handleCategoryClick('all')}>All Categories</button>
              <button className={`filter-chip ${currentCategory === 'nature' ? 'active' : ''}`} onClick={() => handleCategoryClick('nature')}>Nature</button>
              <button className={`filter-chip ${currentCategory === 'cars' ? 'active' : ''}`} onClick={() => handleCategoryClick('cars')}>Cars</button>
            </div>

            {/* Tag filters */}
            {allTags.length > 0 && (
              <div className="filter-bar animate-fade-in-up stagger-1">
                <button 
                  className={`filter-chip ${currentTag === 'all' ? 'active' : ''}`} 
                  onClick={() => handleTagClick('all')}
                >
                  All Tags
                </button>
                {allTags.map(tag => (
                  <button 
                    key={tag}
                    className={`filter-chip ${currentTag === tag ? 'active' : ''}`} 
                    onClick={() => handleTagClick(tag)}
                  >
                    {tag}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Error state */}
          {error && (
            <div className="empty-state">
              <p className="text-error">{error}</p>
            </div>
          )}

          {/* Loading Skeletons */}
          {loading && images.length === 0 && (
            <div className="gallery-grid" id="gallery-grid">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="skeleton-card"><div className="skeleton-img"></div><div className="skeleton-text"></div><div className="skeleton-text short"></div></div>
              ))}
            </div>
          )}

          {/* Image Grid */}
          {!loading && images.length > 0 && (
            <div className="gallery-grid">
              {images.map(img => (
                <ImageCard key={img.id} image={img} onExpand={openLightbox} />
              ))}
            </div>
          )}

          {/* Empty state */}
          {!loading && images.length === 0 && !error && (
            <div className="empty-state">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" className="text-muted">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                <polyline points="21 15 16 10 5 21"></polyline>
              </svg>
              <h3>No photos yet</h3>
              <p className="text-secondary">Check back soon — new work is always in progress.</p>
            </div>
          )}

          {/* Load more */}
          {images.length < total && (
            <div className="load-more">
              <button className="btn btn-outline" onClick={loadMore}>
                {loading ? 'Loading...' : 'Load More'}
              </button>
            </div>
          )}
        </div>
      </section>

      {/* Lightbox Modal */}
      <div className={`lightbox ${lightboxData ? 'active' : ''}`} onClick={(e) => {
        if(e.target.classList.contains('lightbox')) closeLightbox();
      }}>
        <button className="lightbox-close" aria-label="Close lightbox" onClick={closeLightbox}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
        {lightboxData && (
          <div className="lightbox-content">
            <img src={lightboxData.image_url} alt={lightboxData.title} />
            <div className="lightbox-info">
              <h3>{lightboxData.title}</h3>
              {lightboxData.description && <p className="text-secondary">{lightboxData.description}</p>}
            </div>
          </div>
       )}
      </div>
    </>
  );
};

export default Home;
