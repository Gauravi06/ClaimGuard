import React, { useState, useEffect, useCallback } from 'react';
import {
  Calendar,
  FastForward,
  Play,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Activity,
  Award,
  Layers,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  TrendingUp,
  Inbox,
  Clock,
  RefreshCw
} from 'lucide-react';
import {
  getSimClock,
  advanceSim,
  getSimPending,
  getSimSettled,
  getSimMetrics
} from '../api/client';

const SimulationDashboard = () => {
  const [clockDate, setClockDate] = useState('...');
  const [metrics, setMetrics] = useState(null);
  const [pendingData, setPendingData] = useState({ count: 0, claims: [] });
  const [settledData, setSettledData] = useState({ count: 0, claims: [] });
  const [advanceDays, setAdvanceDays] = useState(7);
  const [loading, setLoading] = useState(true);
  const [advancing, setAdvancing] = useState(false);
  const [activeTab, setActiveTab] = useState('pending'); // 'pending' | 'settled'
  const [lastAdvanceResult, setLastAdvanceResult] = useState(null);
  const [error, setError] = useState(null);

  // Fetch all simulation state from /api/sim
  const fetchSimulationState = useCallback(async () => {
    try {
      setError(null);
      const [clockRes, metricsRes, pendingRes, settledRes] = await Promise.all([
        getSimClock(),
        getSimMetrics(),
        getSimPending(),
        getSimSettled(),
      ]);

      setClockDate(clockRes.simulated_date);
      setMetrics(metricsRes);
      setPendingData(pendingRes);
      setSettledData(settledRes);
    } catch (err) {
      console.error('Failed to load simulation data:', err);
      setError('Unable to connect to the simulation API. Ensure the backend is running.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSimulationState();
  }, [fetchSimulationState]);

  // Handle advancing the simulation clock
  const handleAdvance = async (days = advanceDays) => {
    try {
      setAdvancing(true);
      setError(null);
      const result = await advanceSim(days);
      setLastAdvanceResult(result);
      await fetchSimulationState();
    } catch (err) {
      console.error('Failed to advance simulation:', err);
      setError('Failed to advance the simulation clock. Please try again.');
    } finally {
      setAdvancing(false);
    }
  };

  // Helper for rendering risk badges
  const renderRiskBadge = (level) => {
    const normalized = (level || 'low').toLowerCase();
    if (normalized === 'high') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">
          <ShieldAlert className="w-3 h-3 mr-1" /> High Risk
        </span>
      );
    }
    if (normalized === 'medium') {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">
          <AlertTriangle className="w-3 h-3 mr-1" /> Medium
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
        <ShieldCheck className="w-3 h-3 mr-1" /> Low Risk
      </span>
    );
  };

  // Helper for rendering prediction status
  const renderPredictionBadge = (prediction, score) => {
    const isFraud = prediction ?? (score > 0.5);
    return isFraud ? (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-50 text-red-700 border border-red-200">
        Predicted Fraud
      </span>
    ) : (
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700">
        Legitimate
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[500px]">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mb-4"></div>
        <p className="text-slate-600 font-medium">Loading simulation pipeline...</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Top Banner & Clock Card */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-6 bg-gradient-to-r from-slate-900 to-indigo-950 text-white flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-indigo-400 text-sm font-semibold tracking-wider uppercase mb-1">
              <Clock className="w-4 h-4" />
              <span>Temporal Simulation Pipeline</span>
            </div>
            <h1 className="text-2xl font-bold text-white">Live Batch Fraud Simulator</h1>
            <p className="text-slate-300 text-sm mt-1 max-w-xl">
              Simulates real-world claims aging and delayed investigation feedback. The clock advances 7 days per step,
              monitoring newly settled claims and automatically retraining the model.
            </p>
          </div>

          {/* Current Clock Date & Advance Controls */}
          <div className="bg-white/10 backdrop-blur-md border border-white/10 rounded-xl p-4 flex flex-col sm:flex-row items-center gap-4">
            <div className="text-center sm:text-left">
              <span className="block text-xs uppercase text-slate-300 font-medium tracking-wide">
                Simulated Date
              </span>
              <div className="flex items-center space-x-2 mt-1">
                <Calendar className="w-5 h-5 text-indigo-400" />
                <span className="text-2xl font-black font-mono tracking-tight text-white">
                  {clockDate}
                </span>
              </div>
            </div>

            <div className="flex items-center space-x-2 w-full sm:w-auto">
              <button
                id="advance-7-days-btn"
                onClick={() => handleAdvance(7)}
                disabled={advancing}
                className="flex-1 sm:flex-none px-5 py-2.5 bg-indigo-500 hover:bg-indigo-600 disabled:bg-indigo-400 text-white font-semibold rounded-lg shadow-sm transition-all flex items-center justify-center space-x-2 cursor-pointer"
              >
                {advancing ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Advancing...</span>
                  </>
                ) : (
                  <>
                    <FastForward className="w-4 h-4" />
                    <span>Advance 7 Days</span>
                  </>
                )}
              </button>

              <select
                aria-label="Select days to advance"
                value={advanceDays}
                onChange={(e) => setAdvanceDays(Number(e.target.value))}
                className="bg-slate-800 text-white text-xs border border-slate-700 rounded-lg px-2.5 py-2.5 focus:outline-none focus:ring-1 focus:ring-indigo-400"
              >
                <option value={7}>+7d</option>
                <option value={14}>+14d</option>
                <option value={28}>+28d</option>
              </select>
            </div>
          </div>
        </div>

        {/* Retraining Alert Banner */}
        {lastAdvanceResult && (
          <div
            className={`px-6 py-4 border-t flex items-center justify-between transition-all ${
              lastAdvanceResult.retrained
                ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                : 'bg-slate-50 border-slate-200 text-slate-800'
            }`}
          >
            <div className="flex items-center space-x-3">
              {lastAdvanceResult.retrained ? (
                <div className="p-2 bg-emerald-100 text-emerald-700 rounded-full">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
              ) : (
                <div className="p-2 bg-slate-200 text-slate-700 rounded-full">
                  <FastForward className="w-5 h-5" />
                </div>
              )}
              <div>
                <p className="font-semibold text-sm">
                  {lastAdvanceResult.retrained ? (
                    <>
                      Model Automatically Retrained to{' '}
                      <span className="underline font-bold">v{lastAdvanceResult.model_version}</span>!
                    </>
                  ) : (
                    <>Clock Advanced to {lastAdvanceResult.simulated_date}</>
                  )}
                </p>
                <p className="text-xs opacity-90 mt-0.5">
                  {lastAdvanceResult.newly_settled} claims newly settled in this window.
                  {lastAdvanceResult.retrained && ' Training completed & metrics updated.'}
                </p>
              </div>
            </div>

            <div className="text-right">
              <span className="inline-block text-xs font-mono font-bold px-2 py-1 rounded bg-white/80 border border-current shadow-xs">
                Active Model: v{lastAdvanceResult.model_version}
              </span>
            </div>
          </div>
        )}

        {error && (
          <div className="px-6 py-3 bg-rose-50 border-t border-rose-200 text-rose-700 text-sm flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
            Model Version
          </span>
          <div className="mt-2 flex items-baseline space-x-1">
            <span className="text-2xl font-bold text-slate-900">
              {metrics && metrics.model_version > 0 ? `v${metrics.model_version}` : 'No Model'}
            </span>
          </div>
          <span className="text-xs text-slate-400 mt-1 block">
            {metrics && metrics.model_version > 0 ? 'Active in Pipeline' : 'Awaiting 1st Retrain'}
          </span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
            Training Size
          </span>
          <div className="mt-2 flex items-baseline space-x-1">
            <span className="text-2xl font-bold text-slate-900">{metrics?.n_train || 0}</span>
            <span className="text-xs text-slate-500">claims</span>
          </div>
          <span className="text-xs text-slate-400 mt-1 block">Labeled dataset</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
            Precision
          </span>
          <div className="mt-2 flex items-baseline space-x-1">
            <span className="text-2xl font-bold text-indigo-600">
              {metrics ? (metrics.precision * 100).toFixed(1) : '0.0'}%
            </span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2 overflow-hidden">
            <div
              className="bg-indigo-600 h-1.5 rounded-full"
              style={{ width: `${(metrics?.precision || 0) * 100}%` }}
            ></div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
            Recall
          </span>
          <div className="mt-2 flex items-baseline space-x-1">
            <span className="text-2xl font-bold text-indigo-600">
              {metrics ? (metrics.recall * 100).toFixed(1) : '0.0'}%
            </span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2 overflow-hidden">
            <div
              className="bg-indigo-600 h-1.5 rounded-full"
              style={{ width: `${(metrics?.recall || 0) * 100}%` }}
            ></div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
            F1-Score
          </span>
          <div className="mt-2 flex items-baseline space-x-1">
            <span className="text-2xl font-bold text-indigo-600">
              {metrics ? (metrics.f1 * 100).toFixed(1) : '0.0'}%
            </span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2 overflow-hidden">
            <div
              className="bg-indigo-600 h-1.5 rounded-full"
              style={{ width: `${(metrics?.f1 || 0) * 100}%` }}
            ></div>
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
            PR-AUC
          </span>
          <div className="mt-2 flex items-baseline space-x-1">
            <span className="text-2xl font-bold text-emerald-600">
              {metrics ? (metrics.pr_auc * 100).toFixed(1) : '0.0'}%
            </span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-1.5 mt-2 overflow-hidden">
            <div
              className="bg-emerald-600 h-1.5 rounded-full"
              style={{ width: `${(metrics?.pr_auc || 0) * 100}%` }}
            ></div>
          </div>
        </div>
      </div>

      {/* Tabs & Claims Tables View */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-200 px-6 pt-4 space-x-4 bg-slate-50/50">
          <button
            onClick={() => setActiveTab('pending')}
            className={`pb-3 px-2 font-semibold text-sm flex items-center space-x-2 border-b-2 transition-colors cursor-pointer ${
              activeTab === 'pending'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <Clock className="w-4 h-4" />
            <span>Pending Under Investigation</span>
            <span className="ml-2 px-2 py-0.5 rounded-full text-xs bg-slate-200 text-slate-700">
              {pendingData.count}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('settled')}
            className={`pb-3 px-2 font-semibold text-sm flex items-center space-x-2 border-b-2 transition-colors cursor-pointer ${
              activeTab === 'settled'
                ? 'border-indigo-600 text-indigo-600'
                : 'border-transparent text-slate-500 hover:text-slate-800'
            }`}
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Settled Claims (Ground Truth)</span>
            <span className="ml-2 px-2 py-0.5 rounded-full text-xs bg-indigo-100 text-indigo-700">
              {settledData.count}
            </span>
          </button>
        </div>

        {/* Tab 1: Pending Claims */}
        {activeTab === 'pending' && (
          <div>
            <div className="p-4 bg-amber-50/60 border-b border-amber-100 text-amber-800 text-xs flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <ShieldAlert className="w-4 h-4 text-amber-600" />
                <span>
                  <strong>Strict Leak Prevention:</strong> Pending claims hide truth labels (
                  <code>is_fraud</code>, <code>investigation_days</code>, <code>label_available_at</code>) to prevent data leakage.
                </span>
              </div>
              <span className="font-mono text-slate-500">As of: {pendingData.as_of}</span>
            </div>

            {pendingData.claims.length === 0 ? (
              <div className="p-12 text-center text-slate-400">
                <Inbox className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="font-medium text-slate-600">No pending claims as of {clockDate}.</p>
                <p className="text-xs text-slate-400 mt-1">Advance the clock to ingest or settle claims.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-600">
                  <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-500 border-b border-slate-200">
                    <tr>
                      <th className="py-3 px-4">Claim ID</th>
                      <th className="py-3 px-4">Filed Date</th>
                      <th className="py-3 px-4">Amount</th>
                      <th className="py-3 px-4">Severity</th>
                      <th className="py-3 px-4">Fraud Probability</th>
                      <th className="py-3 px-4">Prediction</th>
                      <th className="py-3 px-4">Risk Level</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {pendingData.claims.map((claim) => (
                      <tr key={claim.claim_id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="py-3 px-4 font-mono font-medium text-slate-900">
                          {claim.claim_id}
                        </td>
                        <td className="py-3 px-4 font-mono text-xs">{claim.filed_at}</td>
                        <td className="py-3 px-4 font-medium text-slate-900">
                          ${Number(claim.total_claim_amount || 0).toLocaleString()}
                        </td>
                        <td className="py-3 px-4">
                          <span className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded">
                            {claim.incident_severity || 'Minor'}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex items-center space-x-2">
                            <span className="font-mono font-bold text-slate-800">
                              {(Number(claim.fraud_score || 0) * 100).toFixed(1)}%
                            </span>
                            <div className="w-16 bg-slate-200 rounded-full h-1.5 overflow-hidden">
                              <div
                                className={`h-1.5 rounded-full ${
                                  claim.fraud_score >= 0.7
                                    ? 'bg-rose-500'
                                    : claim.fraud_score >= 0.3
                                    ? 'bg-amber-500'
                                    : 'bg-emerald-500'
                                }`}
                                style={{ width: `${(claim.fraud_score || 0) * 100}%` }}
                              ></div>
                            </div>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          {renderPredictionBadge(claim.prediction, claim.fraud_score)}
                        </td>
                        <td className="py-3 px-4">{renderRiskBadge(claim.risk_level)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Settled Claims */}
        {activeTab === 'settled' && (
          <div>
            <div className="p-4 bg-emerald-50/60 border-b border-emerald-100 text-emerald-800 text-xs flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>
                  <strong>Ground Truth Verification:</strong> Completed claims with finalized investigation outcomes (
                  <code>is_fraud</code>) and the date labels arrived.
                </span>
              </div>
              <span className="font-mono text-slate-500">As of: {settledData.as_of}</span>
            </div>

            {settledData.claims.length === 0 ? (
              <div className="p-12 text-center text-slate-400">
                <Inbox className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p className="font-medium text-slate-600">No settled claims yet on {clockDate}.</p>
                <p className="text-xs text-slate-400 mt-1">
                  Investigation takes 10–30 days. Advance the clock 2–3 weeks to settle claims.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-600">
                  <thead className="bg-slate-50 text-xs uppercase font-semibold text-slate-500 border-b border-slate-200">
                    <tr>
                      <th className="py-3 px-4">Claim ID</th>
                      <th className="py-3 px-4">Filed</th>
                      <th className="py-3 px-4">Settled At</th>
                      <th className="py-3 px-4">Amount</th>
                      <th className="py-3 px-4">Fraud Score</th>
                      <th className="py-3 px-4">Prediction</th>
                      <th className="py-3 px-4">True Label</th>
                      <th className="py-3 px-4">Accuracy Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {settledData.claims.map((claim) => {
                      const isFraud = claim.is_fraud === 1 || claim.is_fraud === true;
                      const predFraud = claim.prediction ?? (claim.fraud_score > 0.5);
                      const isCorrect = predFraud === isFraud;

                      return (
                        <tr key={claim.claim_id} className="hover:bg-slate-50/80 transition-colors">
                          <td className="py-3 px-4 font-mono font-medium text-slate-900">
                            {claim.claim_id}
                          </td>
                          <td className="py-3 px-4 font-mono text-xs text-slate-500">{claim.filed_at}</td>
                          <td className="py-3 px-4 font-mono text-xs font-semibold text-slate-700">
                            {claim.label_available_at}
                          </td>
                          <td className="py-3 px-4 font-medium text-slate-900">
                            ${Number(claim.total_claim_amount || 0).toLocaleString()}
                          </td>
                          <td className="py-3 px-4">
                            <span className="font-mono font-semibold text-slate-800">
                              {(Number(claim.fraud_score || 0) * 100).toFixed(1)}%
                            </span>
                          </td>
                          <td className="py-3 px-4">
                            {renderPredictionBadge(claim.prediction, claim.fraud_score)}
                          </td>
                          <td className="py-3 px-4">
                            {isFraud ? (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-200">
                                FRAUD
                              </span>
                            ) : (
                              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                                LEGIT
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-4">
                            {isCorrect ? (
                              <span className="text-xs font-medium text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded flex items-center w-fit">
                                <CheckCircle2 className="w-3 h-3 mr-1" /> Match
                              </span>
                            ) : (
                              <span className="text-xs font-medium text-rose-700 bg-rose-50 px-2 py-0.5 rounded flex items-center w-fit">
                                <AlertTriangle className="w-3 h-3 mr-1" /> Misclassification
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default SimulationDashboard;
