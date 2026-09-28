import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react';
import { submitClaim } from '../api/client';
import { formatScore, getRiskTextColor } from '../utils/helpers';

const ClaimForm = () => {
  const [formData, setFormData] = useState({
    claimant_name: '',
    claim_type: 'auto',
    claim_amount: '',
    incident_date: '',
    description: '',
    days_to_report: 0,
    prior_claims_count: 0,
    police_report_filed: false,
    witnesses: 0,
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : 
              type === 'number' ? (value ? Number(value) : '') : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await submitClaim(formData);
      setResult(data);
    } catch (err) {
      console.error('Error submitting claim:', err);
      setError('Failed to submit claim. Please check your inputs and try again.');
    } finally {
      setLoading(false);
    }
  };

  if (result) {
    const riskColorClass = getRiskTextColor(result.risk_level);
    const scoreDeg = (result.fraud_score * 180).toFixed(2);
    
    return (
      <div className="max-w-3xl mx-auto">
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-8 text-center">
          <div className="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-8 h-8" />
          </div>
          <h2 className="text-2xl font-bold text-slate-800 mb-2">Claim Submitted Successfully</h2>
          <p className="text-slate-500 mb-8">Claim ID: <span className="font-mono text-slate-800">{result.id}</span></p>

          <div className="bg-slate-50 rounded-xl p-8 mb-8 border border-slate-100">
            <h3 className="text-lg font-medium text-slate-800 mb-6">Real-time AI Risk Assessment</h3>
            
            <div className="flex flex-col md:flex-row items-center justify-center gap-12">
              <div className="relative w-48 h-24 overflow-hidden flex flex-col items-center">
                <div className="w-48 h-48 rounded-full border-[16px] border-slate-200 absolute top-0"></div>
                <div 
                  className="w-48 h-48 rounded-full border-[16px] border-transparent border-t-indigo-500 border-l-indigo-500 absolute top-0 transition-transform duration-1000 ease-out"
                  style={{ transform: `rotate(${scoreDeg - 135}deg)` }}
                ></div>
                <div className="absolute bottom-0 w-full text-center">
                  <span className={`text-3xl font-bold ${riskColorClass}`}>{formatScore(result.fraud_score)}</span>
                </div>
              </div>
              
              <div className="text-left">
                <div className="mb-2">
                  <span className="text-sm text-slate-500 uppercase tracking-wider font-semibold">Risk Level</span>
                  <div className={`text-2xl font-bold capitalize mt-1 ${riskColorClass}`}>
                    {result.risk_level} Risk
                  </div>
                </div>
                {result.risk_level === 'high' && (
                  <div className="flex items-center text-red-600 text-sm mt-3 bg-red-50 p-2 rounded">
                    <AlertTriangle className="w-4 h-4 mr-2" />
                    Flagged for manual review
                  </div>
                )}
              </div>
            </div>

            {/* Feature Explanations */}
            {result.explanations && result.explanations.length > 0 && (
              <div className="mt-8 text-left">
                <h4 className="text-sm font-semibold text-slate-700 mb-3">Key Risk Factors</h4>
                <div className="space-y-2">
                  {result.explanations.map((exp, i) => (
                    <div key={i} className="flex items-center justify-between text-sm">
                      <span className="text-slate-600 capitalize">{exp.feature.replace(/_/g, ' ')}</span>
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-slate-200 rounded-full h-2">
                          <div 
                            className={`h-2 rounded-full ${exp.direction === 'up' ? 'bg-red-400' : 'bg-green-400'}`}
                            style={{ width: `${Math.min(exp.importance * 100 * 3, 100)}%` }}
                          ></div>
                        </div>
                        <span className={`text-xs font-medium ${exp.direction === 'up' ? 'text-red-500' : 'text-green-500'}`}>
                          {exp.direction === 'up' ? '↑ Risk' : '↓ Risk'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-center space-x-4">
            <button 
              onClick={() => { setResult(null); setFormData({ ...formData, claimant_name: '', claim_amount: '', description: '' }); }}
              className="px-6 py-2 border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-50 transition-colors"
            >
              Submit Another
            </button>
            <Link 
              to={`/claims/${result.id}`}
              className="px-6 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors flex items-center"
            >
              View Full Details
              <ArrowRight className="w-4 h-4 ml-2" />
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto">
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="px-8 py-6 border-b border-slate-100 bg-slate-50">
          <h2 className="text-xl font-bold text-slate-800">Submit New Claim</h2>
          <p className="text-sm text-slate-500 mt-1">Enter claim details for instant risk assessment.</p>
        </div>
        
        {error && (
          <div className="mx-8 mt-6 p-4 bg-red-50 border border-red-100 text-red-600 rounded-lg flex items-start">
            <AlertCircle className="w-5 h-5 mr-3 mt-0.5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="p-8 space-y-8">
          {/* Section 1 */}
          <div>
            <h3 className="text-base font-semibold text-slate-800 border-b border-slate-100 pb-2 mb-4">Claimant Information</h3>
            <div className="grid grid-cols-1 gap-6">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Full Name</label>
                <input required type="text" name="claimant_name" value={formData.claimant_name} onChange={handleChange} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-shadow" placeholder="John Doe" />
              </div>
            </div>
          </div>

          {/* Section 2 */}
          <div>
            <h3 className="text-base font-semibold text-slate-800 border-b border-slate-100 pb-2 mb-4">Claim Details</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Claim Type</label>
                <select name="claim_type" value={formData.claim_type} onChange={handleChange} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none bg-white">
                  <option value="auto">Auto</option>
                  <option value="health">Health</option>
                  <option value="property">Property</option>
                  <option value="life">Life</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Amount ($)</label>
                <input required type="number" name="claim_amount" min="0" step="0.01" value={formData.claim_amount} onChange={handleChange} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" placeholder="5000.00" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Incident Date</label>
                <input required type="date" name="incident_date" value={formData.incident_date} onChange={handleChange} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
              <textarea required name="description" rows="3" value={formData.description} onChange={handleChange} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none resize-none" placeholder="Describe the incident..."></textarea>
            </div>
          </div>

          {/* Section 3 */}
          <div>
            <h3 className="text-base font-semibold text-slate-800 border-b border-slate-100 pb-2 mb-4">Risk Indicators</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Days to Report</label>
                <input type="number" name="days_to_report" min="0" value={formData.days_to_report} onChange={handleChange} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Prior Claims</label>
                <input type="number" name="prior_claims_count" min="0" value={formData.prior_claims_count} onChange={handleChange} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Witnesses</label>
                <input type="number" name="witnesses" min="0" value={formData.witnesses} onChange={handleChange} className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" />
              </div>
            </div>
            <div className="mt-6 flex items-center">
              <input type="checkbox" id="police_report_filed" name="police_report_filed" checked={formData.police_report_filed} onChange={handleChange} className="w-4 h-4 text-indigo-600 border-slate-300 rounded focus:ring-indigo-500" />
              <label htmlFor="police_report_filed" className="ml-2 block text-sm text-slate-700">
                Police report was filed
              </label>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-100 flex justify-end">
            <button 
              type="submit" 
              disabled={loading}
              className={`px-6 py-2.5 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors flex items-center ${loading ? 'opacity-70 cursor-not-allowed' : ''}`}
            >
              {loading ? 'Processing...' : 'Submit Claim for Assessment'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ClaimForm;
