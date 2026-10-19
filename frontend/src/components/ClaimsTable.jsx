import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, RefreshCw, CheckCircle, XCircle } from 'lucide-react';
import { getClaims } from '../api/client';
import { formatCurrency, formatScore, getRiskColor, truncateId, formatDate, isSettled, isPredictionCorrect } from '../utils/helpers';
import StatusBadge from './StatusBadge';

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'pending', label: 'Pending' },
  { key: 'settled', label: 'Settled' },
];

const ClaimsTable = () => {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filter, setFilter] = useState('all');
  const navigate = useNavigate();

  const fetchClaims = async () => {
    try {
      setLoading(true);
      const data = await getClaims();
      setClaims(data);
    } catch (err) {
      console.error('Error fetching claims:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClaims();
  }, []);

  const counts = {
    all: claims.length,
    pending: claims.filter((c) => !isSettled(c)).length,
    settled: claims.filter((c) => isSettled(c)).length,
  };

  const filteredClaims = claims.filter((c) => {
    if (filter === 'pending' && isSettled(c)) return false;
    if (filter === 'settled' && !isSettled(c)) return false;
    const q = searchTerm.toLowerCase();
    return c.claimant_name.toLowerCase().includes(q) || c.id.toLowerCase().includes(q);
  });

  const getGroundTruth = (claim) => {
    if (claim.true_label === true) return <span className="px-2 py-1 rounded bg-red-100 text-red-700 text-xs font-medium">Fraud</span>;
    if (claim.true_label === false) return <span className="px-2 py-1 rounded bg-green-100 text-green-700 text-xs font-medium">Legitimate</span>;
    return <span className="px-2 py-1 rounded bg-slate-100 text-slate-400 text-xs font-medium">Unknown</span>;
  };

  const getResult = (claim) => {
    const ok = isPredictionCorrect(claim);
    if (ok === null) return <span className="text-slate-300">-</span>;
    return ok ? (
      <span className="inline-flex items-center text-emerald-700 text-xs font-semibold"><CheckCircle className="w-4 h-4 mr-1" /> Correct</span>
    ) : (
      <span className="inline-flex items-center text-red-700 text-xs font-semibold"><XCircle className="w-4 h-4 mr-1" /> Incorrect</span>
    );
  };

  const th = 'px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider';

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden flex flex-col h-full">
      <div className="p-6 border-b border-slate-100 flex flex-col lg:flex-row justify-between items-center gap-4">
        <div className="flex gap-2">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === f.key ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {f.label} ({counts[f.key]})
            </button>
          ))}
        </div>
        <div className="flex items-center gap-4 w-full lg:w-auto">
          <div className="relative w-full sm:w-72">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <Search className="h-4 w-4 text-slate-400" />
            </div>
            <input
              type="text"
              className="block w-full pl-10 pr-3 py-2 border border-slate-300 rounded-lg leading-5 bg-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm transition-colors"
              placeholder="Search claimant or ID..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <button
            onClick={fetchClaims}
            disabled={loading}
            className="flex items-center px-4 py-2 bg-white border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      <div className="overflow-x-auto flex-1">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th scope="col" className={th}>ID</th>
              <th scope="col" className={th}>Claimant</th>
              <th scope="col" className={th}>Amount</th>
              <th scope="col" className={th}>Date</th>
              <th scope="col" className={th}>Fraud Prob.</th>
              <th scope="col" className={th}>Risk</th>
              <th scope="col" className={th}>Prediction</th>
              <th scope="col" className={th}>Status</th>
              <th scope="col" className={th}>Ground Truth</th>
              <th scope="col" className={th}>Result</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-slate-100">
            {loading && claims.length === 0 ? (
              <tr><td colSpan="10" className="px-6 py-10 text-center text-slate-500">Loading claims...</td></tr>
            ) : filteredClaims.length === 0 ? (
              <tr><td colSpan="10" className="px-6 py-10 text-center text-slate-500">No claims found.</td></tr>
            ) : (
              filteredClaims.map((claim) => (
                <tr
                  key={claim.id}
                  onClick={() => navigate(`/claims/${claim.id}`)}
                  className="hover:bg-indigo-50/50 cursor-pointer transition-colors"
                >
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-slate-500">{truncateId(claim.id)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">{claim.claimant_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{formatCurrency(claim.claim_amount)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{formatDate(claim.incident_date)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">{formatScore(claim.fraud_score)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className={`px-2.5 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getRiskColor(claim.risk_level)}`}>
                      {claim.risk_level}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className={`text-xs font-semibold ${claim.prediction ? 'text-red-600' : 'text-green-600'}`}>
                      {claim.prediction ? 'Fraud' : 'Legitimate'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm"><StatusBadge claim={claim} /></td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{getGroundTruth(claim)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">{getResult(claim)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ClaimsTable;