import React from 'react';
import { Clock, CheckCircle } from 'lucide-react';
import { isSettled } from '../utils/helpers';

const StatusBadge = ({ claim }) =>
  isSettled(claim) ? (
    <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-700 text-xs font-semibold uppercase tracking-wide">
      <CheckCircle className="w-3 h-3 mr-1" /> Settled
    </span>
  ) : (
    <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-amber-100 text-amber-700 text-xs font-semibold uppercase tracking-wide">
      <Clock className="w-3 h-3 mr-1" /> Pending investigation
    </span>
  );

export default StatusBadge;