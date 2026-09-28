import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, User, Calendar, DollarSign, FileText, Activity, ShieldAlert, CheckCircle, XCircle } from 'lucide-react';
import { getClaim, labelClaim } from '../api/client';
import { formatCurrency, formatScore, getRiskColor, getRiskTextColor, formatDate } from '../utils/helpers';

const ClaimDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [claim, setClaim] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [labeling, setLabeling] = useState(false);

  useEffect(() => {
    const fetchClaim = async () => {
      try {
        setLoading(true);
        const data = await getClaim(id);
        setClaim(data);
      } catch (err) {
        setError('Failed to load claim details.');
      } finally {
        setLoading(false);
      }
    };
    fetchClaim();
  }, [id]);

  const handleLabel = async (isFraud) => {
    try {
      setLabeling(true);
      const updated = await labelClaim(id, isFraud);
      setClaim(updated);
    } catch (err) {
      alert('Failed to update label');
    } finally {
      setLabeling(false);
    }
  };

  if (loading) return <div className="flex justify-center mt-20"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div></div>;
  if (error || !claim) return <div className="text-red-500 bg-red-50 p-4 rounded-lg">{error || 'Claim not found'}</div>;

  const scoreDeg = (claim.fraud_score * 180).toFixed(2);
  const riskColorClass = getRiskTextColor(claim.risk_level);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button onClick={() => navigate(-1)} className="flex items-center text-slate-500 hover:text-indigo-600 transition-colors">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </button>
        <div className="text-sm text-slate-500 font-mono">ID: {claim.id}</div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Details */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
            <div className="p-6 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
              <div className="flex items-center">
                <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center mr-4">
                  <User className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-slate-800">{claim.claimant_name}</h2>
                  <p className="text-sm text-slate-500 capitalize">{claim.claim_type} Insurance Claim</p>
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-slate-800">{formatCurrency(claim.claim_amount)}</div>
                <div className="text-sm text-slate-500">Claim Amount</div>
              </div>
            </div>
            
            <div className="p-6">
              <h3 className="text-sm font-semibold text-slate-800 uppercase tracking-wider mb-4">Claim Details</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-y-6 gap-x-8 mb-8">
                <div>
                  <div className="flex items-center text-slate-500 mb-1"><Calendar className="w-4 h-4 mr-2" /> Incident Date</div>
                  <div className="font-medium text-slate-800">{formatDate(claim.incident_date)}</div>
                </div>
                <div>
                  <div className="flex items-center text-slate-500 mb-1"><Activity className="w-4 h-4 mr-2" /> Days to Report</div>
                  <div className="font-medium text-slate-800">{claim.days_to_report} days</div>
                </div>
                <div>
                  <div className="flex items-center text-slate-500 mb-1"><FileText className="w-4 h-4 mr-2" /> Prior Claims</div>
                  <div className="font-medium text-slate-800">{claim.prior_claims_count}</div>
                </div>
                <div>
                  <div className="flex items-center text-slate-500 mb-1"><User className="w-4 h-4 mr-2" /> Witnesses</div>
                  <div className="font-medium text-slate-800">{claim.witnesses}</div>
                </div>
                <div className="md:col-span-2">
                  <div className="flex items-center text-slate-500 mb-1"><ShieldAlert className="w-4 h-4 mr-2" /> Police Report</div>
                  <div className="font-medium text-slate-800">
                    {claim.police_report_filed ? (
                      <span className="flex items-center text-green-600"><CheckCircle className="w-4 h-4 mr-1"/> Filed</span>
                    ) : (
                      <span className="flex items-center text-amber-600"><XCircle className="w-4 h-4 mr-1"/> Not Filed</span>
                    )}
                  </div>
                </div>
              </div>

              <h3 className="text-sm font-semibold text-slate-800 uppercase tracking-wider mb-2">Description</h3>
              <div className="bg-slate-50 p-4 rounded-lg text-slate-700 text-sm whitespace-pre-wrap border border-slate-100">
                {claim.description}
              </div>
            </div>
          </div>
          
          {/* Label Section */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
            <h3 className="text-lg font-bold text-slate-800 mb-4">Ground Truth Label</h3>
            
            {claim.true_label !== null && claim.true_label !== undefined ? (
              <div className={`p-4 rounded-lg border flex items-start ${claim.true_label ? 'bg-red-50 border-red-100 text-red-800' : 'bg-green-50 border-green-100 text-green-800'}`}>
                {claim.true_label ? <XCircle className="w-6 h-6 mr-3 mt-0.5" /> : <CheckCircle className="w-6 h-6 mr-3 mt-0.5" />}
                <div>
                  <div className="font-bold text-lg">Marked as {claim.true_label ? 'Fraud' : 'Legitimate'}</div>
                </div>
              </div>
            ) : (
              <div>
                <p className="text-slate-600 mb-4">This claim has not been labeled yet. Review the risk assessment and investigate before applying a label.</p>
                <div className="flex space-x-4">
                  <button 
                    onClick={() => handleLabel(false)}
                    disabled={labeling}
                    className="flex-1 py-2 bg-green-50 text-green-700 border border-green-200 hover:bg-green-100 rounded-lg font-medium transition-colors flex justify-center items-center"
                  >
                    <CheckCircle className="w-4 h-4 mr-2" /> Mark Legitimate
                  </button>
                  <button 
                    onClick={() => handleLabel(true)}
                    disabled={labeling}
                    className="flex-1 py-2 bg-red-50 text-red-700 border border-red-200 hover:bg-red-100 rounded-lg font-medium transition-colors flex justify-center items-center"
                  >
                    <XCircle className="w-4 h-4 mr-2" /> Mark as Fraud
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Risk Assessment */}
        <div className="space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 flex flex-col items-center">
            <h3 className="text-lg font-bold text-slate-800 w-full text-center mb-6">Risk Assessment</h3>
            
            <div className="relative w-48 h-24 overflow-hidden flex flex-col items-center mb-6">
              <div className="w-48 h-48 rounded-full border-[16px] border-slate-100 absolute top-0"></div>
              <div 
                className={`w-48 h-48 rounded-full border-[16px] border-transparent absolute top-0 transition-transform duration-1000 ease-out ${claim.risk_level === 'high' ? 'border-t-red-500 border-l-red-500' : claim.risk_level === 'medium' ? 'border-t-amber-500 border-l-amber-500' : 'border-t-green-500 border-l-green-500'}`}
                style={{ transform: `rotate(${scoreDeg - 135}deg)` }}
              ></div>
              <div className="absolute bottom-0 w-full text-center">
                <span className={`text-3xl font-bold ${riskColorClass}`}>{formatScore(claim.fraud_score)}</span>
              </div>
            </div>
            
            <span className={`px-4 py-1.5 rounded-full text-sm font-bold uppercase tracking-wider ${getRiskColor(claim.risk_level)}`}>
              {claim.risk_level} Risk
            </span>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
            <h3 className="text-base font-bold text-slate-800 mb-4">Feature Explanations</h3>
            <p className="text-xs text-slate-500 mb-4">Factors contributing to the risk score.</p>
            
            <div className="space-y-4">
              {claim.explanations && claim.explanations.length > 0 ? (
                claim.explanations.map((exp, idx) => (
                  <div key={idx}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="font-medium text-slate-700 capitalize">{exp.feature.replace(/_/g, ' ')}</span>
                      <span className={exp.direction === 'up' ? 'text-red-500' : 'text-green-500'}>
                        {exp.direction === 'up' ? '↑' : '↓'} {(exp.importance * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-slate-100 rounded-full h-1.5">
                      <div 
                        className={`h-1.5 rounded-full ${exp.direction === 'up' ? 'bg-red-400' : 'bg-green-400'}`}
                        style={{ width: `${Math.min(exp.importance * 100 * 3, 100)}%` }}
                      ></div>
                    </div>
                    <div className="text-xs text-slate-400 mt-1">Value: {exp.value}</div>
                  </div>
                ))
              ) : (
                <div className="text-sm text-slate-500 italic text-center py-4">No explanations available.</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ClaimDetail;
