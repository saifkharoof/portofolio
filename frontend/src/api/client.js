export const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

export const getHeaders = () => {
  const token = localStorage.getItem('auth_token');
  return {
    ...(token && { Authorization: `Bearer ${token}` })
  };
};

export const fetchAPI = async (endpoint, options = {}) => {
  const url = `${API_BASE}${endpoint}`;
  
  const isFormData = options.body instanceof FormData;
  const initHeaders = {
    ...getHeaders(),
    ...(!isFormData && { 'Content-Type': 'application/json' }),
    ...options.headers
  };

  const response = await fetch(url, {
    ...options,
    headers: initHeaders
  });

  if (response.status === 401) {
    localStorage.removeItem('auth_token');
    
    // Only force a brutal page redirect if the user wasn't strictly explicitly trying to login right now!
    if (!endpoint.includes('/login')) {
      window.location.href = '/login';
    }
    
    throw new Error('Either the username or password is incorrect');
  }

  if (!response.ok) {
    let errorDetail = 'Something went wrong';
    try {
      const data = await response.json();
      errorDetail = data.detail || errorDetail;
    } catch (e) {
      // Ignored
    }
    throw new Error(errorDetail);
  }

  // Handle 204 No Content
  if (response.status === 204) return null;

  return response.json();
};

