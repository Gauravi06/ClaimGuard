import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
});

export const submitClaim = async (data) => {
  const response = await api.post('/claims', data);
  return response.data;
};

export const getClaims = async () => {
  const response = await api.get('/claims');
  return response.data;
};

export const getClaim = async (id) => {
  const response = await api.get(`/claims/${id}`);
  return response.data;
};

// Demo of the delayed investigation outcome: reveals the ground truth of a pending
// claim and marks it settled. The original prediction is never changed.
export const settleClaim = async (id, isFraud) => {
  const response = await api.post(`/claims/${id}/settle`, { true_label: isFraud });
  return response.data;
};

export const labelClaim = async (id, label) => {
  const response = await api.patch(`/claims/${id}/label`, { true_label: label });
  return response.data;
};

export const simulateLabels = async (count, fraudRate) => {
  const response = await api.post('/simulate/delayed-labels', { count, fraud_rate: fraudRate });
  return response.data;
};

export const seedDemoData = async () => {
  const response = await api.post('/seed');
  return response.data;
};

export const getStats = async () => {
  const response = await api.get('/analytics/stats');
  return response.data;
};

export const getModelPerformance = async () => {
  const response = await api.get('/analytics/model-performance');
  return response.data;
};