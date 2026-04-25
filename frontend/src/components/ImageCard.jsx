import React, { useState } from 'react';

const ImageCard = ({ image, onExpand }) => {
  const [isLoaded, setIsLoaded] = useState(false);

  return (
    <div className="image-card card animate-fade-in-up">
      <div className="card-image-wrapper">
        {!isLoaded && <div className="image-skeleton"></div>}
        <img 
          src={`https://wsrv.nl/?url=${encodeURIComponent(image.image_url)}&w=800&output=webp&maxage=30d`} 
          alt={image.title} 
          loading="lazy" 
          decoding="async"
          className={isLoaded ? 'img-loaded' : 'img-hidden'}
          onLoad={() => setIsLoaded(true)}
        />
        <div className="card-overlay">
          <button 
            className="card-expand-btn" 
            aria-label="View full image" 
            onClick={() => onExpand(image)}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 3 21 3 21 9"></polyline>
              <polyline points="9 21 3 21 3 15"></polyline>
              <line x1="21" y1="3" x2="14" y2="10"></line>
              <line x1="3" y1="21" x2="10" y2="14"></line>
            </svg>
          </button>
        </div>
      </div>
      <div className="card-body">
        <h3 className="card-title">{image.title}</h3>
        {image.description && <p className="card-description">{image.description}</p>}
        {image.tags && image.tags.length > 0 && (
          <div className="card-tags">
            {image.tags.map(tag => (
              <span key={tag} className="tag">{tag}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ImageCard;
