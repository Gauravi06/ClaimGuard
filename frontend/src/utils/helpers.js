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

// A claim is SETTLED once its ground-truth label has arrived; until then it is PENDING.
export const isSettled = (claim) => claim != null && claim.true_label != null;

// Original stored prediction vs the ground truth that arrived later (null while pending).
export const isPredictionCorrect = (claim) =>
  isSettled(claim) ? Boolean(claim.prediction) === Boolean(claim.true_label) : null;

// Confusion-matrix cell of the original prediction (null while pending).
export const getOutcomeLabel = (claim) => {
  if (!isSettled(claim)) return null;
  const predicted = Boolean(claim.prediction);
  const actual = Boolean(claim.true_label);
  if (predicted && actual) return 'True positive: fraud caught';
  if (predicted && !actual) return 'False positive: false alarm';
  if (!predicted && actual) return 'False negative: fraud missed';
  return 'True negative: legitimate cleared';
};