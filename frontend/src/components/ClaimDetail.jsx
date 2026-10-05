import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, User, Calendar, FileText, Activity, ShieldAlert, CheckCircle, XCircle, Clock, Search, Lock } from 'lucide-react';
import { getClaim, settleClaim } from '../api/client';
import {
  formatCurrency, formatScore, getRiskColor, getRiskTextColor, formatDate,
  isSettled, isPredictionCorrect, getOutcomeLabel,
} from '../utils/helpers';
import StatusBadge from './StatusBadge';

const DETAIL_LABELS = {
  fault: (v) => (v === 1 ? 'Policy holder' : 'Third party'),
  accident_area: (v) => (v === 1 ? 'Urban' : 'Rural'),
  address_change_claim: (v) => ['No change', '4-8 years ago', '2-3 years ago', 'Within 1 year', 'Under 6 months'][v] ?? v,
};

const ClaimDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [claim, setClaim] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [settling, setSettling] = useState(false);
  const [investigationDone, setInvestigationDone] = useState(false);

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
    setInvestigationDone(false);
    fetchClaim();
  }, [id]);

  const handleSettle = async (isFraud) => {
    try {
      setSettling(true);
      const updated = await settleClaim(id, isFraud);
      setClaim(updated);
    } catch (err) {
      alert(err?.response?.data?.detail || 'Failed to settle claim');
    } finally {
      setSettling(false);
    }
  };

  if (loading) return <div className="flex justify-center mt-20"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div></div>;
  if (error || !claim) return <div className="text-red-500 bg-red-50 p-4 rounded-lg">{error || 'Claim not found'}</div>;

  const settled = isSettled(claim);
  const correct = isPredictionCorrect(claim);
  const scoreDeg = (claim.fraud_score * 180).toFixed(2);
  const riskColorClass = getRiskTextColor(claim.risk_level);

  const Detail = ({ icon: Icon, label, children, span }) => (
    <div className={span ? 'md:col-span-2' : ''}>
      <div className="flex items-center text-slate-500 mb-1">{Icon && <Icon className="w-4 h-4 mr-2" />} {label}</div>
      <div className="font-medium text-slate-800">{children}</div>
    </div>
  );

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <button onClick={() => navigate(-1)} className="flex items-center text-slate-500 hover:text-indigo-600 transition-colors">
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back
        </button>
        <div className="flex items-center gap-4">
          <StatusBadge claim={claim} />
          <div className="text-sm text-slate-500 font-mono">ID: {claim.id}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
            <div className="p-6 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
              <div className="flex items-center">
                <div className="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center mr-4">
                  <User className="w-6 h-6" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-slate-800">{claim.claimant_name}</h2>
                  <p className="text-sm text-slate-500 capitalize">{claim.claim_type} claim</p>
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
                <Detail icon={Calendar} label="Incident Date">{formatDate(claim.incident_date)}</Detail>
                <Detail icon={Activity} label="Days to Report">{claim.days_to_report} days</Detail>
                <Detail icon={FileText} label="Prior Claims">{claim.prior_claims_count}</Detail>
                <Detail icon={User} label="Witnesses">{claim.witnesses}</Detail>
                <Detail icon={User} label="Driver Age / Rating">{claim.age} yrs / tier {claim.driver_rating}</Detail>
                <Detail icon={FileText} label="At Fault">{DETAIL_LABELS.fault(claim.fault)}</Detail>
                <Detail icon={FileText} label="Deductible">{formatCurrency(claim.deductible)}</Detail>
                <Detail icon={FileText} label="Accident Area">{DETAIL_LABELS.accident_area(claim.accident_area)}</Detail>
                <Detail icon={FileText} label="Address Change">{DETAIL_LABELS.address_change_claim(claim.address_change_claim)}</Detail>
                <Detail icon={FileText} label="Supplements Requested">{claim.number_of_suppliments}</Detail>
                <Detail icon={ShieldAlert} label="Police Report" span>
                  {claim.police_report_filed ? (
                    <span className="flex items-center text-green-600"><CheckCircle className="w-4 h-4 mr-1" /> Filed</span>
                  ) : (
                    <span className="flex items-center text-amber-600"><XCircle className="w-4 h-4 mr-1" /> Not Filed</span>
                  )}
                </Detail>
              </div>

              <h3 className="text-sm font-semibold text-slate-800 uppercase tracking-wider mb-2">Description</h3>
              <div className="bg-slate-50 p-4 rounded-lg text-slate-700 text-sm whitespace-pre-wrap border border-slate-100">
                {claim.description}
              </div>
            </div>
          </div>

          {/* Investigation / ground truth */}
          <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
            <h3 className="text-lg font-bold text-slate-800 mb-1">Investigation &amp; Ground Truth</h3>
            <p className="text-xs text-slate-500 mb-4">
              The investigation result is the real outcome of the claim. It is not another ML prediction.
            </p>

            {!settled && !investigationDone && (
              <div className="p-5 rounded-lg border border-amber-200 bg-amber-50">
                <div className="flex items-start">
                  <Clock className="w-6 h-6 text-amber-600 mr-3 mt-0.5 flex-shrink-0" />
                  <div className="text-sm text-amber-900">
                    <div className="font-bold uppercase tracking-wide mb-1">Investigation in progress</div>
                    Ground truth is unknown: <span className="font-mono">true_label = NULL</span>. The model has already scored this claim
                    ({claim.prediction ? 'predicted fraud' : 'predicted legitimate'}, {formatScore(claim.fraud_score)}), but nobody knows yet whether it was right.
                  </div>
                </div>
                <button
                  onClick={() => setInvestigationDone(true)}
                  className="mt-4 px-5 py-2 bg-amber-600 text-white font-medium rounded-lg hover:bg-amber-700 transition-colors flex items-center"
                >
                  <Search className="w-4 h-4 mr-2" /> Advance investigation (+30 days)
                </button>
              </div>
            )}

            {!settled && investigationDone && (
              <div className="p-5 rounded-lg border border-indigo-200 bg-indigo-50">
                <div className="text-sm text-indigo-900 mb-4">
                  <div className="font-bold uppercase tracking-wide mb-1">Investigation complete: reveal the ground truth</div>
                  Demo simulation: choose the real outcome the investigators found. This becomes the claim's true label and the claim is settled.
                  The original prediction stays exactly as it was.
                </div>
                <div className="flex flex-col sm:flex-row gap-4">
                  <button
                    onClick={() => handleSettle(false)}
                    disabled={settling}
                    className="flex-1 py-2.5 bg-green-50 text-green-700 border border-green-200 hover:bg-green-100 rounded-lg font-medium transition-colors flex justify-center items-center disabled:opacity-60"
                  >
                    <CheckCircle className="w-4 h-4 mr-2" /> Investigation result: LEGITIMATE
                  </button>
                  <button
                    onClick={() => handleSettle(true)}
                    disabled={settling}
                    className="flex-1 py-2.5 bg-red-50 text-red-700 border border-red-200 hover:bg-red-100 rounded-lg font-medium transition-colors flex justify-center items-center disabled:opacity-60"
                  >
                    <XCircle className="w-4 h-4 mr-2" /> Investigation result: FRAUD
                  </button>
                </div>
              </div>
            )}

            {settled && (
              <div className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="p-4 rounded-lg border border-slate-200 bg-slate-50">
                    <div className="flex items-center text-xs uppercase tracking-wide text-slate-500 mb-1"><Lock className="w-3 h-3 mr-1" /> Original prediction</div>
                    <div className={`text-lg font-bold ${claim.prediction ? 'text-red-600' : 'text-green-600'}`}>
                      {claim.prediction ? 'FRAUD' : 'LEGITIMATE'}
                    </div>
                    <div className="text-xs text-slate-500">{formatScore(claim.fraud_score)} fraud probability</div>
                  </div>
                  <div className="p-4 rounded-lg border border-slate-200 bg-slate-50">
                    <div className="text-xs uppercase tracking-wide text-slate-500 mb-1">Ground truth (investigation)</div>
                    <div className={`text-lg font-bold ${claim.true_label ? 'text-red-600' : 'text-green-600'}`}>
                      {claim.true_label ? 'FRAUD' : 'LEGITIMATE'}
                    </div>
                    <div className="text-xs text-slate-500">revealed after investigation</div>
                  </div>
                  <div className={`p-4 rounded-lg border ${correct ? 'border-emerald-200 bg-emerald-50' : 'border-red-200 bg-red-50'}`}>
                    <div className="text-xs uppercase tracking-wide text-slate-500 mb-1">Verdict</div>
                    <div className={`text-lg font-bold flex items-center ${correct ? 'text-emerald-700' : 'text-red-700'}`}>
                      {correct ? <CheckCircle className="w-5 h-5 mr-1" /> : <XCircle className="w-5 h-5 mr-1" />}
                      {correct ? 'CORRECT' : 'INCORRECT'}
                    </div>
                    <div className="text-xs text-slate-600">{getOutcomeLabel(claim)}</div>
                  </div>
                </div>
                <p className="text-xs text-slate-500">
                  The prediction above was stored when the claim was submitted. Settling the claim only added the ground-truth label;
                  the score, risk level, prediction and explanations were not re-computed.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: frozen prediction */}
        <div className="space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 flex flex-col items-center">
            <h3 className="text-lg font-bold text-slate-800 w-full text-center mb-1">Risk Assessment</h3>
            <p className="text-xs text-slate-500 mb-6">Made at submission time</p>

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
            <div className={`mt-3 text-sm font-semibold ${claim.prediction ? 'text-red-600' : 'text-green-600'}`}>
              Prediction: {claim.prediction ? 'FRAUD' : 'LEGITIMATE'}
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
            <h3 className="text-base font-bold text-slate-800 mb-4">Feature Explanations</h3>
            <p className="text-xs text-slate-500 mb-4">Tree-model feature importance behind the risk score.</p>

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