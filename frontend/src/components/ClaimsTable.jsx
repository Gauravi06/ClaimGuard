import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, RefreshCw } from 'lucide-react';
import { getClaims } from '../api/client';
import { formatCurrency, formatScore, getRiskColor, truncateId, formatDate } from '../utils/helpers';

const ClaimsTable = () => {
  const [claims, setClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
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

  const filteredClaims = claims.filter(c => 
    c.claimant_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getLabelBadge = (trueLabel) => {
    if (trueLabel === true) return <span className="px-2 py-1 rounded bg-red-100 text-red-700 text-xs font-medium">Fraud</span>;
    if (trueLabel === false) return <span className="px-2 py-1 rounded bg-green-100 text-green-700 text-xs font-medium">Legitimate</span>;
    return <span className="px-2 py-1 rounded bg-slate-100 text-slate-500 text-xs font-medium">Unlabeled</span>;
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden flex flex-col h-full">
      <div className="p-6 border-b border-slate-100 flex flex-col sm:flex-row justify-between items-center gap-4">
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
      
      <div className="overflow-x-auto flex-1">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">ID</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Claimant</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Type</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Amount</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Date</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Risk Score</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Risk Level</th>
              <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-slate-100">
            {loading && claims.length === 0 ? (
              <tr><td colSpan="8" className="px-6 py-10 text-center text-slate-500">Loading claims...</td></tr>
            ) : filteredClaims.length === 0 ? (
              <tr><td colSpan="8" className="px-6 py-10 text-center text-slate-500">No claims found.</td></tr>
            ) : (
              filteredClaims.map((claim) => (
                <tr 
                  key={claim.id} 
                  onClick={() => navigate(`/claims/${claim.id}`)}
                  className="hover:bg-indigo-50/50 cursor-pointer transition-colors"
                >
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-slate-500">{truncateId(claim.id)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">{claim.claimant_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 capitalize">{claim.claim_type}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{formatCurrency(claim.claim_amount)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">{formatDate(claim.incident_date)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">{formatScore(claim.fraud_score)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className={`px-2.5 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getRiskColor(claim.risk_level)}`}>
                      {claim.risk_level}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {getLabelBadge(claim.true_label)}
                  </td>
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
