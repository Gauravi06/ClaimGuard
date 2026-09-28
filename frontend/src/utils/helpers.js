export const formatCurrency = (amount) => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
};

export const formatDate = (dateStr) => {
  if (!dateStr) return 'N/A';
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
};

export const formatScore = (score) => {
  if (score === null || score === undefined) return 'N/A';
  return `${(score * 100).toFixed(1)}%`;
};

export const getRiskColor = (level) => {
  switch (level?.toLowerCase()) {
    case 'low':
      return 'text-green-600 bg-green-100';
    case 'medium':
      return 'text-amber-600 bg-amber-100';
    case 'high':
      return 'text-red-600 bg-red-100';
    default:
      return 'text-slate-600 bg-slate-100';
  }
};

export const getRiskTextColor = (level) => {
    switch (level?.toLowerCase()) {
      case 'low':
        return 'text-green-500';
      case 'medium':
        return 'text-amber-500';
      case 'high':
        return 'text-red-500';
      default:
        return 'text-slate-500';
    }
};

export const truncateId = (id) => {
  if (!id) return '';
  return id.substring(0, 8);
};
