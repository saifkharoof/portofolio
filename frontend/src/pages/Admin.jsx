import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchAPI } from '../api/client';
import '../styles/Admin.css';

const Admin = () => {
  const [images, setImages] = useState([]);
  const [totalImages, setTotalImages] = useState(0);
  const [totalTags, setTotalTags] = useState(0);

  // Batch states
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [batchItems, setBatchItems] = useState([]);
  const [isDragging, setIsDragging] = useState(false);

  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [deletingId, setDeletingId] = useState(null);
  
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [editingImageId, setEditingImageId] = useState(null);
  const [editingData, setEditingData] = useState({});
  
  const navigate = useNavigate();

  useEffect(() => {
    if (!localStorage.getItem('auth_token')) {
      navigate('/login');
    } else {
      loadImages();
    }
  }, [navigate]);

  const loadImages = async () => {
    try {
      const data = await fetchAPI('/api/images/?limit=100');
      const imgs = data.images || [];
      
      setImages(imgs);
      setTotalImages(data.total || 0);

      const uniqueTags = new Set(imgs.flatMap(img => img.tags || []));
      setTotalTags(uniqueTags.size);
    } catch (err) {
      console.error('Failed to load images:', err);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    navigate('/login');
  };

  const processFiles = (incomingFiles) => {
    const uniqueIncoming = incomingFiles.filter(newFile => {
      return !selectedFiles.some(existingFile => existingFile.name === newFile.name && existingFile.size === newFile.size);
    });

    if (uniqueIncoming.length === 0) return;

    if (selectedFiles.length + uniqueIncoming.length > 20) {
      setErrorMsg("Cannot select more than 20 images in a single batch layout natively.");
      return;
    }
    setErrorMsg('');
    setSelectedFiles(prev => [...prev, ...uniqueIncoming]);

    const newBatch = uniqueIncoming.map(f => ({
      title: f.name.replace(/\.[^/.]+$/, ""),
      description: '',
      category: 'nature',
      tags: '',
      rating: 0,
      preview: URL.createObjectURL(f)
    }));
    setBatchItems(prev => [...prev, ...newBatch]);

    if (uniqueIncoming.length > 0) {
      setSuccessMsg(`Poof! Successfully appended ${uniqueIncoming.length} photo(s) to your staging queue.`);
      setTimeout(() => setSuccessMsg(''), 3000);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files) {
      processFiles(Array.from(e.target.files));
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFiles(Array.from(e.dataTransfer.files));
    }
  };

  const [generatingIndex, setGeneratingIndex] = useState(null);

  const removeBatchItem = (index) => {
    URL.revokeObjectURL(batchItems[index].preview);
    const newFiles = [...selectedFiles];
    newFiles.splice(index, 1);
    setSelectedFiles(newFiles);
    
    const newBatchItems = [...batchItems];
    newBatchItems.splice(index, 1);
    setBatchItems(newBatchItems);
  };

  const updateBatchItem = (index, field, value) => {
    const newItems = [...batchItems];
    newItems[index][field] = value;
    setBatchItems(newItems);
  };

  const handleAutoGenerate = async (idx) => {
    try {
      setGeneratingIndex(idx);
      setErrorMsg('');
      const file = selectedFiles[idx];
      const formData = new FormData();
      formData.append('file', file);

      const aiData = await fetchAPI('/api/ai/analyze', {
        method: 'POST',
        body: formData
      });

      const newItems = [...batchItems];
      newItems[idx].title = aiData.title || newItems[idx].title;
      newItems[idx].description = aiData.description || newItems[idx].description;
      newItems[idx].category = aiData.category || newItems[idx].category;
      newItems[idx].tags = aiData.tags ? aiData.tags.join(', ') : newItems[idx].tags;
      newItems[idx].rating = aiData.rating || newItems[idx].rating;
      
      setBatchItems(newItems);
      setSuccessMsg(`AI successfully curated metadata for: ${file.name}`);
      setTimeout(() => setSuccessMsg(''), 3000);
    } catch (err) {
      setErrorMsg(`AI Vision Error: ${err.message || 'Failed connecting securely to structured endpoint.'}`);
    } finally {
      setGeneratingIndex(null);
    }
  };

  const handleBatchUpload = async (e) => {
    e.preventDefault();
    setSuccessMsg('');
    setErrorMsg('');

    if (selectedFiles.length === 0) {
      setErrorMsg('Please select at least one image file to upload.');
      return;
    }

    try {
      const formData = new FormData();
      selectedFiles.forEach((file) => {
        formData.append('files', file);
      });
      formData.append('metadata', JSON.stringify(batchItems));

      await fetchAPI('/api/images/batch', {
        method: 'POST',
        body: formData
      });

      setSelectedFiles([]);
      setBatchItems([]);
      document.getElementById('img-file').value = '';

      setSuccessMsg('Batch uploaded successfully!');
      setTimeout(() => setSuccessMsg(''), 3000);
      loadImages();
    } catch (err) {
      setErrorMsg(err.message || 'Something went wrong during batch execution.');
    }
  };

  const handleDelete = async (id) => {
    try {
      await fetchAPI(`/api/images/${id}`, { method: 'DELETE' });
      setDeletingId(null);
      loadImages();
    } catch (err) {
      console.error('Delete error:', err);
    }
  };

  const handleEditClick = (img) => {
    setEditingImageId(img.id);
    setEditingData({
      title: img.title,
      description: img.description || '',
      category: img.category || 'nature',
      tags: (img.tags || []).join(', '),
      rating: img.rating || 0
    });
  };

  const handleUpdate = async (id) => {
    try {
      const payload = {
        title: editingData.title,
        description: editingData.description,
        category: editingData.category,
        tags: editingData.tags.split(',').map(t => t.trim()).filter(Boolean),
        rating: editingData.rating
      };
      await fetchAPI(`/api/images/${id}`, {
        method: 'PUT',
        body: JSON.stringify(payload)
      });
      setEditingImageId(null);
      loadImages();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <section className="admin-section container">
      <div className="admin-header">
        <div>
          <h1>Dashboard</h1>
          <p className="text-secondary">Manage your portfolio dynamically mapping Batch executions.</p>
        </div>
        <button className="btn btn-outline" onClick={handleLogout}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
            <polyline points="16 17 21 12 16 7"></polyline>
            <line x1="21" y1="12" x2="9" y2="12"></line>
          </svg>
          Logout
        </button>
      </div>

      <div className="stats-row">
        <div className="stat-card">
          <span className="stat-card-value">{totalImages}</span>
          <span className="stat-card-label">Total Images</span>
        </div>
        <div className="stat-card">
          <span className="stat-card-value">{totalTags}</span>
          <span className="stat-card-label">Tags Used</span>
        </div>
      </div>

      <div className="admin-panel">
        <div className="panel-header">
          <h2>Batch Upload Images</h2>
          <p className="text-secondary">Select up to 20 images explicitly mapping structural metadata seamlessly.</p>
        </div>

        <form className="add-image-form" onSubmit={handleBatchUpload}>
          <div className="form-row" style={{ display: 'flex', justifyContent: 'center' }}>
            <div className="input-group" style={{ width: '60%', minWidth: '300px' }}>
              <div 
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                style={{
                  width: '100%',
                  position: 'relative'
                }}
              >
                <label
                  htmlFor="img-file"
                  style={{
                    cursor: 'pointer',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '3rem 2rem',
                    border: `2px dashed ${isDragging ? 'var(--color-primary)' : 'var(--color-border)'}`,
                    borderRadius: 'var(--radius-lg)',
                    backgroundColor: isDragging ? 'rgba(78, 204, 163, 0.05)' : 'var(--color-bg-secondary)',
                    transition: 'var(--transition-fast)',
                    textAlign: 'center'
                  }}
                onMouseOver={e => e.currentTarget.style.borderColor = 'var(--color-primary)'}
                onMouseOut={e => e.currentTarget.style.borderColor = 'var(--color-border)'}
              >
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ marginBottom: '1rem', transform: isDragging ? 'scale(1.2)' : 'none', transition: 'transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275)' }}>
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="17 8 12 3 7 8"></polyline>
                  <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
                {isDragging ? (
                  <div style={{ fontWeight: '700', fontSize: '1.3rem', color: 'var(--color-primary)' }}>Drop your photos right here!</div>
                ) : (
                  <>
                    <div style={{ fontWeight: '600', marginBottom: '0.5rem', color: 'var(--color-text-primary)' }}>Click here or Drag and drop images to upload</div>
                    <div style={{ fontSize: '0.9rem', color: 'var(--color-text-secondary)' }}>Supported formats: JPEG, PNG, WEBP. Max 20 files & 15MB each.</div>
                  </>
                )}
              </label>
              <input 
                type="file" 
                id="img-file" 
                style={{ display: 'none' }}
                multiple
                accept="image/jpeg, image/png, image/webp"
                onChange={handleFileSelect}
              />
              </div>
            </div>
          </div>

          <div style={{ marginTop: '2rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {selectedFiles.map((file, idx) => (
              <div key={idx} className="batch-item-card" style={{ padding: '1.5rem', border: `1px solid ${generatingIndex === idx ? 'var(--color-primary)' : 'var(--color-border)'}`, borderRadius: 'var(--radius-lg)', display: 'flex', gap: '1.5rem', alignItems: 'flex-start', position: 'relative', overflow: 'hidden', transition: 'var(--transition-fast)' }}>
                {generatingIndex === idx && (
                  <>
                    <div className="scan-overlay"></div>
                    <div className="analyzing-text">✨ GENERATING...</div>
                  </>
                )}

                <div style={{ flex: '0 0 160px', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <div style={{ width: '100%', aspectRatio: '4/3', borderRadius: 'var(--radius-md)', overflow: 'hidden', border: '1px solid var(--color-border)', backgroundColor: 'var(--color-bg-secondary)', position: 'relative' }}>
                    {batchItems[idx].preview && (
                      <img src={batchItems[idx].preview} alt="preview" style={{ width: '100%', height: '100%', objectFit: 'cover', filter: generatingIndex === idx ? 'brightness(0.6)' : 'none', transition: 'var(--transition-fast)' }} />
                    )}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    <button type="button" className="btn btn-outline btn-sm" onClick={() => removeBatchItem(idx)} style={{ width: '100%' }}>
                      Remove
                    </button>
                    <button 
                      type="button" 
                      onClick={() => handleAutoGenerate(idx)} 
                      disabled={generatingIndex === idx} 
                      style={{ 
                        width: '100%', 
                        padding: '0.5rem', 
                        borderRadius: 'var(--radius-md)', 
                        border: 'none', 
                        background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', 
                        color: 'white', 
                        fontWeight: '600', 
                        cursor: generatingIndex === idx ? 'not-allowed' : 'pointer',
                        opacity: generatingIndex === idx ? 0.7 : 1,
                        transition: 'var(--transition-fast)'
                      }}
                    >
                      {generatingIndex === idx ? '⚡ Analyzing...' : '✨ Auto Details'}
                    </button>
                  </div>
                </div>
                
                <div style={{ flex: '1', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <div style={{ fontWeight: '600', color: 'var(--color-text-primary)', wordBreak: 'break-all' }}>{file.name}</div>
                  <div className="form-row">
                    <div className="input-group">
                      <label>Title</label>
                      <input type="text" className="input" value={batchItems[idx].title} onChange={(e) => updateBatchItem(idx, 'title', e.target.value)} required />
                    </div>
                    <div className="input-group">
                      <label>Category</label>
                      <select className="input" value={batchItems[idx].category} onChange={(e) => updateBatchItem(idx, 'category', e.target.value)}>
                        <option value="nature">Nature</option>
                        <option value="cars">Cars</option>
                      </select>
                    </div>
                    <div className="input-group">
                      <label>Rating (0-5)</label>
                      <input type="number" min="0" max="5" className="input" value={batchItems[idx].rating} onChange={(e) => updateBatchItem(idx, 'rating', parseInt(e.target.value) || 0)} />
                    </div>
                  </div>
                  <div className="form-row">
                    <div className="input-group">
                      <label>Tags (comma-separated)</label>
                      <input type="text" className="input" value={batchItems[idx].tags} onChange={(e) => updateBatchItem(idx, 'tags', e.target.value)} />
                    </div>
                    <div className="input-group">
                      <label>Description</label>
                      <input type="text" className="input" value={batchItems[idx].description} onChange={(e) => updateBatchItem(idx, 'description', e.target.value)} />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {selectedFiles.length > 0 && (
            <div className="form-actions" style={{ marginTop: '2rem' }}>
              <button type="submit" className="btn btn-primary" disabled={selectedFiles.length === 0}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="12" y1="5" x2="12" y2="19"></line>
                  <line x1="5" y1="12" x2="19" y2="12"></line>
                </svg>
                <span>Upload {selectedFiles.length > 0 ? selectedFiles.length : ''} Images</span>
              </button>
            </div>
          )}

          {successMsg && (
            <div className="success-message animate-slide-down">
              <span>{successMsg}</span>
            </div>
          )}

          {errorMsg && (
            <div className="error-message animate-slide-down">
              <span>{errorMsg}</span>
            </div>
          )}
        </form>
      </div>

      <div className="admin-panel">
        <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2>Your Images</h2>
          <select className="input" style={{ width: 'auto' }} value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}>
            <option value="all">All Categories</option>
            <option value="nature">Nature</option>
            <option value="cars">Cars</option>
          </select>
        </div>
        
        {images.length > 0 ? (
          <div className="image-list">
            {(categoryFilter === 'all' ? images : images.filter(img => img.category === categoryFilter)).map((img) => (
              <div key={img.id} className="image-list-item">
                <img className="list-thumb" src={`https://wsrv.nl/?url=${encodeURIComponent(img.image_url)}&w=300&output=webp`} alt={img.title} loading="lazy" decoding="async" />
                
                {editingImageId === img.id ? (
                  <div style={{ flex: '1', display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
                    <div style={{ display: 'flex', gap: '1rem' }}>
                      <input className="input" style={{ flex: '1' }} value={editingData.title} onChange={e => setEditingData({...editingData, title: e.target.value})} placeholder="Title" />
                      <select className="input" style={{ flex: '1' }} value={editingData.category} onChange={e => setEditingData({...editingData, category: e.target.value})}>
                        <option value="nature">Nature</option>
                        <option value="cars">Cars</option>
                      </select>
                    </div>
                    <div style={{ display: 'flex', gap: '1rem' }}>
                      <input className="input" style={{ flex: '1' }} value={editingData.tags} onChange={e => setEditingData({...editingData, tags: e.target.value})} placeholder="Tags (comma-separated)" />
                      <input type="number" min="0" max="5" className="input" style={{ width: '100px' }} value={editingData.rating} onChange={e => setEditingData({...editingData, rating: parseInt(e.target.value) || 0})} placeholder="Rating" />
                    </div>
                    <input className="input" value={editingData.description} onChange={e => setEditingData({...editingData, description: e.target.value})} placeholder="Description" />
                  </div>
                ) : (
                  <div className="list-info">
                    <div className="list-title" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      {img.title}
                      {img.rating > 0 && <span style={{ color: 'var(--color-primary)', fontSize: '0.9rem' }}>{'★'.repeat(img.rating)}</span>}
                    </div>
                    <div className="list-meta">
                      <span style={{ textTransform: 'capitalize', color: 'var(--color-primary)' }}>{img.category}</span> · {img.tags?.join(', ') || 'No tags'} · {new Date(img.created_at).toLocaleDateString()}
                    </div>
                  </div>
                )}

                <div className="list-actions">
                  {editingImageId === img.id ? (
                     <div style={{ display: 'flex', gap: '8px' }}>
                       <button className="btn btn-primary btn-sm" onClick={() => handleUpdate(img.id)}>Save</button>
                       <button className="btn btn-outline btn-sm" onClick={() => setEditingImageId(null)}>Cancel</button>
                     </div>
                  ) : deletingId === img.id ? (
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button className="btn btn-danger btn-sm" onClick={() => handleDelete(img.id)}>Confirm</button>
                      <button className="btn btn-outline btn-sm" onClick={() => setDeletingId(null)}>Cancel</button>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button className="btn btn-outline btn-sm" onClick={() => handleEditClick(img)}>Update</button>
                      <button className="btn btn-outline btn-sm" onClick={() => setDeletingId(img.id)}>Delete</button>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-admin">
            <p className="text-muted">No images in your portfolio yet. Add one above!</p>
          </div>
        )}
      </div>
    </section>
  );
};

export default Admin;
