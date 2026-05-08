import React, { useState, useRef, useEffect } from 'react';
import ImageCard from '../components/ImageCard';
import { API_BASE } from '../api/client';
import '../styles/Chat.css';

const Chat = () => {
  const [messages, setMessages] = useState([
    { role: 'bot', text: 'Hi there! I am your AI assistant. You can ask me questions about Saif\'s CV and professional experience, search through his photography portfolio, or even upload an image and ask me to find similar ones!' }
  ]);
  const [knownImages, setKnownImages] = useState([]);
  const [input, setInput] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [threadId] = useState(() => {
    const stored = localStorage.getItem('chat_thread_id');
    if (stored) return stored;
    const newId = 'thread_' + Math.random().toString(36).substring(2, 15);
    localStorage.setItem('chat_thread_id', newId);
    return newId;
  });
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);
  const [lightboxData, setLightboxData] = useState(null);

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  };

  useEffect(() => { scrollToBottom(); }, [messages]);

  // --- Session Management & Exit Warning ---
  useEffect(() => {
    // Save state to sessionStorage for the Navbar to read
    sessionStorage.setItem('isChatActive', messages.length > 1 ? 'true' : 'false');
    
    // Prevent accidental reload or tab close
    const handleBeforeUnload = (e) => {
      if (messages.length > 1) {
        e.preventDefault();
        e.returnValue = ''; // Required for Chrome
      }
    };
    
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [messages.length]);

  useEffect(() => {
    // Cleanup when component fully unmounts
    return () => sessionStorage.removeItem('isChatActive');
  }, []);

  // --- Suggestions ---
  const suggestions = [
    "Where did you work?",
    "What experience do you have?",
    "Are you familiar with cloud services?",
    "Show me pictures of red sports cars",
    "What kind of camera gear do you use?"
  ];

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImageFile(file);
      const reader = new FileReader();
      reader.onloadend = () => setImagePreview(reader.result);
      reader.readAsDataURL(file);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    // Only set dragging to false if we leave the main container, not its children
    if (!e.currentTarget.contains(e.relatedTarget)) {
      setIsDragging(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (file.type.startsWith('image/')) {
        setImageFile(file);
        const reader = new FileReader();
        reader.onloadend = () => setImagePreview(reader.result);
        reader.readAsDataURL(file);
      }
    }
  };

  const handleRemoveImage = () => {
    setImageFile(null);
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
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
    const handleKeyDown = (e) => { if (e.key === 'Escape') closeLightbox(); };
    if (lightboxData) window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [lightboxData]);

  // --- Markdown → HTML renderer ---
  const renderMessageText = (text, images) => {
    let html = text;

    if (images && images.length > 0) {
      html = html.replace(/!\[[\s\S]*?\]\([\s\S]*?\)/g, '');
      html = html.replace(/\[([^\]]+)\]\([^)]+\)/g, '$1');
    } else {
      html = html.replace(/!\[([\s\S]*?)\]\(([\s\S]*?)\)/g, '<br/><img src="$2" alt="$1" class="chat-inline-image" /><br/>');
      html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    }

    // Hide partial markdown image tags that are actively streaming in (fixes raw text flashing)
    html = html.replace(/!\[[^\]]*\]\([^\s)]*$/, '');
    html = html.replace(/!\[[^\]]*$/, '');

    html = html.replace(/^### (.+)$/gm, '<h4 class="chat-md-heading">$1</h4>');
    html = html.replace(/^## (.+)$/gm, '<h3 class="chat-md-heading">$1</h3>');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/^\* (.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>[\s\S]*?<\/li>)/g, '<ul class="chat-md-list">$1</ul>');
    html = html.replace(/\n/g, '<br/>');
    html = html.replace(/(<\/h[34]>)<br\/>/g, '$1');

    return <div className="chat-text" dir="auto" dangerouslySetInnerHTML={{ __html: html }} />;
  };

  // --- Send message ---
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() && !imageFile) return;

    const userMessage = { role: 'user', text: input, imagePreview };
    const currentImageFile = imageFile;

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    handleRemoveImage();
    setIsLoading(true);

    try {
      const formData = new FormData();
      formData.append('message', userMessage.text);
      formData.append('thread_id', threadId);
      if (currentImageFile) formData.append('image', currentImageFile);

      setMessages(prev => [...prev, { role: 'bot', text: '', toolImages: [], isStreaming: true }]);

      const response = await fetch(`${API_BASE}/api/chat/stream`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) throw new Error("Network response was not ok");

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let botText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        for (const line of chunk.split('\n')) {
          if (!line.startsWith('data: ')) continue;
          const dataStr = line.slice(6).trim();
          if (!dataStr) continue;

          try {
            const data = JSON.parse(dataStr);

            if (data.type === 'content') {
              // Backend Pydantic guarantees `text` is always a plain string
              botText += data.text;
              setMessages(prev => {
                const nm = [...prev];
                nm[nm.length - 1] = { ...nm[nm.length - 1], text: botText };
                return nm;
              });

            } else if (data.type === 'tool_end' && data.name === 'search_portfolio') {
              if (data.images && data.images.length > 0) {
                // Update global known images so memory references always render as cards
                setKnownImages(prev => {
                  const updated = [...prev];
                  data.images.forEach(img => {
                    if (!updated.find(i => i.image_url === img.image_url)) {
                      updated.push(img);
                    }
                  });
                  return updated;
                });
                
                setMessages(prev => {
                  const nm = [...prev];
                  nm[nm.length - 1] = { ...nm[nm.length - 1], toolImages: data.images };
                  return nm;
                });
              }

            } else if (data.type === 'busy') {
              setMessages(prev => {
                const nm = [...prev];
                nm[nm.length - 1] = {
                  ...nm[nm.length - 1],
                  text: data.detail || "The assistant is currently busy. Please try again shortly.",
                  isStreaming: false
                };
                return nm;
              });
              setIsLoading(false);

            } else if (data.type === 'done' || data.type === 'error') {
              setMessages(prev => {
                const nm = [...prev];
                nm[nm.length - 1] = { ...nm[nm.length - 1], isStreaming: false };
                if (data.type === 'error') {
                  console.error("Backend stream error:", data.detail);
                  if (!nm[nm.length - 1].text) {
                    nm[nm.length - 1].text = "Sorry, I encountered a temporary error. Please try again.";
                  }
                }
                return nm;
              });
              setIsLoading(false);
            }
          } catch (e) {
            console.error("Error parsing SSE data", e);
          }
        }
      }

      // Always clear streaming state when reader finishes
      setIsLoading(false);
      setMessages(prev => {
        const nm = [...prev];
        if (nm.length > 0) nm[nm.length - 1] = { ...nm[nm.length - 1], isStreaming: false };
        return nm;
      });

    } catch (error) {
      console.error("Chat error:", error);
      setMessages(prev => {
        const nm = [...prev];
        nm[nm.length - 1] = {
          ...nm[nm.length - 1],
          text: "Sorry, an error occurred while connecting to the server.",
          isStreaming: false,
        };
        return nm;
      });
      setIsLoading(false);
    }
  };

  return (
    <div 
      className="chat-page animate-fade-in-up"
      onDragOver={handleDragOver}
      onDragEnter={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {isDragging && (
        <div className="chat-drag-overlay">
          <div className="chat-drag-content">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
              <circle cx="8.5" cy="8.5" r="1.5"></circle>
              <polyline points="21 15 16 10 5 21"></polyline>
            </svg>
            <p>Drop your image here</p>
          </div>
        </div>
      )}
      
      <div className="chat-header">
        <h2 className="section-title">AI Portfolio Assistant</h2>
        <p className="section-subtitle">Multimodal Search & Interaction</p>
      </div>

      <div className="chat-container">
        <div className="chat-messages">
          {messages.map((msg, index) => (
            <div key={index} className={`chat-message-wrapper ${msg.role}`}>
              <div className="chat-avatar">
                <span className="avatar-text">{msg.role === 'user' ? 'U' : 'AI'}</span>
              </div>
              <div className="chat-message-content">
                {msg.imagePreview && (
                  <img src={msg.imagePreview} alt="User Upload" className="chat-uploaded-image" />
                )}

                {msg.text && (() => {
                  let displayImages = [];
                  // Look up against ALL known images in the session
                  if (knownImages.length > 0) {
                    knownImages.forEach(img => {
                      if (msg.text.includes(img.image_url)) {
                        displayImages.push(img);
                      }
                    });
                  }

                  return (
                    <>
                      {renderMessageText(msg.text, displayImages)}

                      {msg.isStreaming && (
                        <span className="typing-indicator"><span>.</span><span>.</span><span>.</span></span>
                      )}

                      {displayImages.length > 0 && (
                        <div className="chat-carousel-wrapper">
                          <div className="chat-carousel">
                            {displayImages.map((img, i) => (
                              <div key={i} className="chat-carousel-item">
                                <ImageCard image={img} onExpand={openLightbox} />
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  );
                })()}

                {!msg.text && msg.isStreaming && (
                  <span className="typing-indicator"><span>.</span><span>.</span><span>.</span></span>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {messages.length === 1 && (
          <div className="chat-suggestions">
            {suggestions.map((suggestion, i) => (
              <button 
                key={i} 
                type="button"
                className="suggestion-bubble"
                onClick={() => setInput(suggestion)}
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}

        <form className="chat-input-area" onSubmit={handleSubmit}>
          {imagePreview && (
            <div className="chat-input-preview">
              <img src={imagePreview} alt="Preview" />
              <button type="button" className="remove-image-btn" onClick={handleRemoveImage}>&times;</button>
            </div>
          )}
          <div className="chat-input-controls">
            <div className="chat-upload-wrapper">
              <input type="file" id="chat-image-upload" accept="image/*" ref={fileInputRef}
                onChange={handleImageChange} style={{ display: 'none' }} />
              <label htmlFor="chat-image-upload" className="chat-btn-icon" aria-label="Upload Image">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
              </label>
            </div>

            <div className="voice-toggle-wrapper tooltip" data-tooltip="Voice mode coming soon">
              <button type="button" className="chat-btn-icon disabled" disabled>
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                  <line x1="12" y1="19" x2="12" y2="23" />
                  <line x1="8" y1="23" x2="16" y2="23" />
                </svg>
              </button>
            </div>

            <input type="text" className="chat-text-input"
              placeholder="Type your message or upload an image..."
              value={input} onChange={(e) => setInput(e.target.value)} disabled={isLoading} />

            <button type="submit" className="chat-submit-btn" disabled={isLoading || (!input.trim() && !imageFile)}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </form>
      </div>

      {/* Lightbox */}
      <div className={`lightbox ${lightboxData ? 'active' : ''}`} onClick={(e) => {
        if (e.target.classList.contains('lightbox')) closeLightbox();
      }}>
        <button className="lightbox-close" aria-label="Close lightbox" onClick={closeLightbox}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
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
    </div>
  );
};

export default Chat;
