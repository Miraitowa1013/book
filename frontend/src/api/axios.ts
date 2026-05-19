import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 180000,
});

// 请求拦截：根据数据类型自动设置 Content-Type
api.interceptors.request.use((config) => {
  // FormData 不能手动设 Content-Type，交给浏览器自动设 boundary
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type'];
  } else if (!config.headers['Content-Type']) {
    config.headers['Content-Type'] = 'application/json';
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API请求错误:', error);
    return Promise.reject(error);
  }
);

export default api;
