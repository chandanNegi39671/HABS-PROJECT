import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
});

const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  let userId = localStorage.getItem('user_id');
  const userStr = localStorage.getItem('user');

  // Validate UUID format; fall back to user.id from parsed localStorage object
  if (!userId || !UUID_REGEX.test(userId)) {
    if (userStr) {
      try { userId = JSON.parse(userStr).id; } catch(e) { userId = null; }
    } else {
      userId = null;
    }
  }

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  // Only set header when value is a valid UUID
  if (userId && UUID_REGEX.test(userId)) {
    config.headers['X-User-Id'] = userId;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Don't logout if the 401 is caused by a bad UUID header — that's a
      // client-side data issue, not an expired/missing auth token.
      const detail = error.response.data?.detail || '';
      const isBadUuid = detail.toLowerCase().includes('invalid user id');
      if (!isBadUuid) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        localStorage.removeItem('user_id');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;
