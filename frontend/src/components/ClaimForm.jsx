import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, AlertCircle, AlertTriangle, Clock, HelpCircle } from 'lucide-react';
import { submitClaim } from '../api/client';
import { formatScore, getRiskTextColor } from '../utils/helpers';
import StatusBadge from './StatusBadge';

const EMPTY_FORM = {
  claimant_name: '',
  claim_type: '',
  claim_amount: '',
  incident_date: '',
  description: '',
  days_to_report: '',
  prior_claims_count: '',
  police_report_filed: false,
  witnesses: '',
  fault: '',
  deductible: '',
  driver_rating: '',
  age: '',
  accident_area: '',
  address_change_claim: '',
  number_of_suppliments: '',
};

const today = () => new Date().toISOString().slice(0, 10);

// Demo presets: every model input is filled in explicitly and stays editable.
const EXAMPLES = {
  high: {
    claimant_name: 'Jordan Reyes',
    claim_type: 'sedan',
    claim_amount: '31000',
    description: 'Collision reported late, no police report, several supplements requested.',
    days_to_report: '25',
    prior_claims_count: '4',
    police_report_filed: false,
    witnesses: '0',
    fault: '1',
    deductible: '500',
    driver_rating: '3',
    age: '27',
    accident_area: '1',
    address_change_claim: '3',
    number_of_suppliments: '6',
  },
  low: {
    claimant_name: 'Alex Morgan',
    claim_type: 'sedan',
    claim_amount: '6500',
    description: 'Minor parking-lot collision, other driver at fault, police report filed.',
    days_to_report: '2',
    prior_claims_count: '0',
    police_report_filed: true,
    witnesses: '2',
    fault: '0',
    deductible: '400',
    driver_rating: '1',
    age: '47',
    accident_area: '1',
    address_change_claim: '0',
    number_of_suppliments: '0',
  },
};

const NUMERIC_FIELDS = [
  'claim_amount', 'days_to_report', 'prior_claims_count', 'witnesses', 'fault', 'deductible',
  'driver_rating', 'age', 'accident_area', 'address_change_claim', 'number_of_suppliments',
];

const inputCls = 'w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none bg-white';
const labelCls = 'block text-sm font-medium text-slate-700 mb-1';

const formatError = (err) => {
  const detail = err?.response?.data?.detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => `${(d.loc || []).slice(1).join('.') || 'input'}: ${d.msg}`).join('; ');
  }
  if (typeof detail === 'string') return detail;
  return 'Failed to submit claim. Please check your inputs and try again.';
};

const ClaimForm = () => {
  const [formData, setFormData] = useState(EMPTY_FORM);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({ ...prev, [name]: type === 'checkbox' ? checked : value }));
  };

  const loadExample = (kind) => {
    setFormData({ ...EXAMPLES[kind], incident_date: today() });
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload = { ...formData };
      NUMERIC_FIELDS.forEach((k) => { payload[k] = Number(formData[k]); });
      const data = await submitClaim(payload);
      setResult(data);
    } catch (err) {
      console.error('Error submitting claim:', err);
      setError(formatError(err));
    } finally {
      setLoading(false);
    }
  };

  if (result) {
    const riskColorClass = getRiskTextColor(result.risk_level);
    const scoreDeg = (result.fraud_score * 180).toFixed(2);

    return (
      <div className="max-w-3xl mx-auto">
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-8">
          <div className="text-center mb-6">
            <div className="mb-4"><StatusBadge claim={result} /></div>
            <h2 className="text-2xl font-bold text-slate-800 mb-2">Claim Scored Instantly</h2>
            <p className="text-slate-500">Claim ID: <span className="font-mono text-slate-800">{result.id}</span></p>
          </div>

          <div className="bg-slate-50 rounded-xl p-8 mb-6 border border-slate-100">
            <h3 className="text-lg font-medium text-slate-800 mb-6 text-center">Real-time AI Risk Assessment</h3>

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

              <div className="text-left space-y-3">
                <div>
                  <span className="text-sm text-slate-500 uppercase tracking-wider font-semibold">Fraud Probability</span>
                  <div className={`text-2xl font-bold mt-1 ${riskColorClass}`}>{formatScore(result.fraud_score)}</div>
                </div>
                <div>
                  <span className="text-sm text-slate-500 uppercase tracking-wider font-semibold">Risk Level</span>
                  <div className={`text-xl font-bold capitalize mt-1 ${riskColorClass}`}>{result.risk_level} Risk</div>
                </div>
                <div>
                  <span className="text-sm text-slate-500 uppercase tracking-wider font-semibold">Prediction</span>
                  <div className={`text-xl font-bold mt-1 ${result.prediction ? 'text-red-600' : 'text-green-600'}`}>
                    {result.prediction ? 'Predicted FRAUD' : 'Predicted LEGITIMATE'}
                  </div>
                </div>
                {result.risk_level === 'high' && (
                  <div className="flex items-center text-red-600 text-sm bg-red-50 p-2 rounded">
                    <AlertTriangle className="w-4 h-4 mr-2" />
                    Flagged for manual review
                  </div>
                )}
              </div>
            </div>

            {result.explanations && result.explanations.length > 0 && (
              <div className="mt-8 text-left">
                <h4 className="text-sm font-semibold text-slate-700 mb-1">Key Risk Factors</h4>
                <p className="text-xs text-slate-500 mb-3">Tree-model feature importance for this claim's inputs.</p>
                <div className="space-y-2">
                  {result.explanations.map((exp, i) => (
                    <div key={i} className="flex items-center justify-between text-sm">
                      <span className="text-slate-600 capitalize">{exp.feature.replace(/_/g, ' ')} <span className="text-slate-400">= {exp.value}</span></span>
                      <div className="flex items-center gap-2">
                        <div className="w-24 bg-slate-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${exp.direction === 'up' ? 'bg-red-400' : 'bg-green-400'}`}
                            style={{ width: `${Math.min(exp.importance * 100 * 3, 100)}%` }}
                          ></div>
                        </div>
                        <span className={`text-xs font-medium w-20 text-right ${exp.direction === 'up' ? 'text-red-500' : 'text-green-500'}`}>
                          {exp.direction === 'up' ? '↑ Risk' : '↓ Risk'} {(exp.importance * 100).toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 mb-8 flex items-start">
            <Clock className="w-6 h-6 text-amber-600 mr-3 mt-0.5 flex-shrink-0" />
            <div className="text-sm text-amber-900">
              <div className="font-bold uppercase tracking-wide mb-1">Pending investigation</div>
              <div className="flex items-center mb-1">
                <HelpCircle className="w-4 h-4 mr-1" /> Ground truth: <span className="font-mono ml-1">true_label = NULL</span> (not known yet)
              </div>
              This prediction is stored now and will not change. The real fraud label arrives only when the
              investigation completes, and the stored prediction is then evaluated against it.
            </div>
          </div>

          <div className="flex justify-center space-x-4">
            <button
              onClick={() => { setResult(null); setFormData(EMPTY_FORM); }}
              className="px-6 py-2 border border-slate-300 text-slate-700 font-medium rounded-lg hover:bg-slate-50 transition-colors"
            >
              Submit Another
            </button>
            <Link
              to={`/claims/${result.id}`}
              className="px-6 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors flex items-center"
            >
              Open Claim &amp; Run Investigation
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
        <div className="px-8 py-6 border-b border-slate-100 bg-slate-50 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-slate-800">Submit New Claim</h2>
            <p className="text-sm text-slate-500 mt-1">All 14 model inputs are required. The claim is scored immediately; its true label comes later.</p>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            <button type="button" onClick={() => loadExample('high')} className="px-3 py-1.5 text-xs font-medium rounded-lg border border-red-200 bg-red-50 text-red-700 hover:bg-red-100 transition-colors">
              Load high-risk example
            </button>
            <button type="button" onClick={() => loadExample('low')} className="px-3 py-1.5 text-xs font-medium rounded-lg border border-green-200 bg-green-50 text-green-700 hover:bg-green-100 transition-colors">
              Load low-risk example
            </button>
          </div>
        </div>

        {error && (
          <div className="mx-8 mt-6 p-4 bg-red-50 border border-red-100 text-red-600 rounded-lg flex items-start">
            <AlertCircle className="w-5 h-5 mr-3 mt-0.5 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="p-8 space-y-8">
          <div>
            <h3 className="text-base font-semibold text-slate-800 border-b border-slate-100 pb-2 mb-4">Claimant Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className={labelCls}>Full Name</label>
                <input required type="text" name="claimant_name" value={formData.claimant_name} onChange={handleChange} className={inputCls} placeholder="John Doe" />
              </div>
              <div>
                <label className={labelCls}>Driver / Policyholder Age</label>
                <input required type="number" name="age" min="16" max="100" step="1" value={formData.age} onChange={handleChange} className={inputCls} placeholder="40" />
              </div>
            </div>
          </div>

          <div>
            <h3 className="text-base font-semibold text-slate-800 border-b border-slate-100 pb-2 mb-4">Claim Details</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
              <div>
                <label className={labelCls}>Vehicle Category (model input)</label>
                <select required name="claim_type" value={formData.claim_type} onChange={handleChange} className={inputCls}>
                  <option value="" disabled>Select…</option>
                  <option value="sedan">Sedan</option>
                  <option value="sport">Sport</option>
                  <option value="utility">Utility / SUV</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Claim Amount ($)</label>
                <input required type="number" name="claim_amount" min="0" step="0.01" value={formData.claim_amount} onChange={handleChange} className={inputCls} placeholder="5000.00" />
              </div>
              <div>
                <label className={labelCls}>Incident Date</label>
                <input required type="date" name="incident_date" value={formData.incident_date} onChange={handleChange} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Who Was At Fault</label>
                <select required name="fault" value={formData.fault} onChange={handleChange} className={inputCls}>
                  <option value="" disabled>Select…</option>
                  <option value="1">Policy holder</option>
                  <option value="0">Third party</option>
                </select>
              </div>
            </div>
            <div>
              <label className={labelCls}>Description</label>
              <textarea required name="description" rows="3" value={formData.description} onChange={handleChange} className={`${inputCls} resize-none`} placeholder="Describe the incident..."></textarea>
            </div>
          </div>

          <div>
            <h3 className="text-base font-semibold text-slate-800 border-b border-slate-100 pb-2 mb-4">Risk Indicators</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <label className={labelCls}>Days to Report</label>
                <input required type="number" name="days_to_report" min="0" step="1" value={formData.days_to_report} onChange={handleChange} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Prior Claims</label>
                <input required type="number" name="prior_claims_count" min="0" step="1" value={formData.prior_claims_count} onChange={handleChange} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Witnesses</label>
                <input required type="number" name="witnesses" min="0" step="1" value={formData.witnesses} onChange={handleChange} className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Deductible</label>
                <select required name="deductible" value={formData.deductible} onChange={handleChange} className={inputCls}>
                  <option value="" disabled>Select…</option>
                  <option value="300">$300</option>
                  <option value="400">$400</option>
                  <option value="500">$500</option>
                  <option value="700">$700</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Driver Rating (1-4)</label>
                <select required name="driver_rating" value={formData.driver_rating} onChange={handleChange} className={inputCls}>
                  <option value="" disabled>Select…</option>
                  <option value="1">1</option>
                  <option value="2">2</option>
                  <option value="3">3</option>
                  <option value="4">4</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Accident Area</label>
                <select required name="accident_area" value={formData.accident_area} onChange={handleChange} className={inputCls}>
                  <option value="" disabled>Select…</option>
                  <option value="1">Urban</option>
                  <option value="0">Rural</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Address Change</label>
                <select required name="address_change_claim" value={formData.address_change_claim} onChange={handleChange} className={inputCls}>
                  <option value="" disabled>Select…</option>
                  <option value="0">No change</option>
                  <option value="1">4-8 years ago</option>
                  <option value="2">2-3 years ago</option>
                  <option value="3">Within 1 year</option>
                  <option value="4">Under 6 months</option>
                </select>
              </div>
              <div>
                <label className={labelCls}>Supplements Requested</label>
                <input required type="number" name="number_of_suppliments" min="0" step="0.5" value={formData.number_of_suppliments} onChange={handleChange} className={inputCls} />
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
              {loading ? 'Scoring...' : 'Submit Claim for Assessment'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ClaimForm;