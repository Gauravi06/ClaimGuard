import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';
import { FileText, AlertTriangle, Activity, Clock, Database } from 'lucide-react';
import { getStats, getClaims, getModelPerformance, seedDemoData } from '../api/client';
import { formatCurrency, formatScore, getRiskColor, truncateId, formatDate } from '../utils/helpers';
import StatusBadge from './StatusBadge';

const Dashboard = () => {
  const [stats, setStats] = useState(null);
  const [perf, setPerf] = useState(null);
  const [recentClaims, setRecentClaims] = useState([]);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [statsData, claimsData, perfData] = await Promise.all([getStats(), getClaims(), getModelPerformance()]);
      setStats(statsData);
      setPerf(perfData);
      setRecentClaims(claimsData.slice(0, 5));
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError('Failed to load dashboard data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleSeed = async () => {
    try {
      setSeeding(true);
      await seedDemoData();
      await fetchData();
    } catch (err) {
      setError('Failed to load demo data.');
    } finally {
      setSeeding(false);
    }
  };

  if (loading && !stats) return <div className="flex justify-center items-center h-full"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div></div>;
  if (error) return <div className="text-red-500 bg-red-50 p-4 rounded-lg">{error}</div>;
  if (!stats) return null;

  const riskData = [
    { name: 'Low Risk', value: stats.claims_by_risk?.low || 0, color: '#22c55e' },
    { name: 'Medium Risk', value: stats.claims_by_risk?.medium || 0, color: '#f59e0b' },
    { name: 'High Risk', value: stats.claims_by_risk?.high || 0, color: '#ef4444' },
  ];

  const typeData = Object.entries(stats.claims_by_type || {}).map(([name, value]) => ({ name, value }));
  const settledCount = perf?.total_labeled ?? 0;

  return (
    <div className="space-y-6">
      {stats.total_claims === 0 && (
        <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-sm text-indigo-900">
            <div className="font-bold mb-1">No claims yet</div>
            Load 20 demo claims (14 settled, 6 pending) or submit your own claim.
          </div>
          <div className="flex gap-3">
            <button onClick={handleSeed} disabled={seeding} className="px-5 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors flex items-center disabled:opacity-60">
              <Database className="w-4 h-4 mr-2" /> {seeding ? 'Loading...' : 'Load demo data'}
            </button>
            <Link to="/submit" className="px-5 py-2 bg-white border border-indigo-200 text-indigo-700 font-medium rounded-lg hover:bg-indigo-100 transition-colors">
              Submit a claim
            </Link>
          </div>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-100 flex items-center">
          <div className="p-4 rounded-lg bg-indigo-50 text-indigo-600 mr-4">
            <FileText className="w-6 h-6" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-500">Total Claims</p>
            <p className="text-2xl font-bold text-slate-800">{stats.total_claims}</p>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-100 flex items-center">
          <div className="p-4 rounded-lg bg-red-50 text-red-600 mr-4">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-500">Flagged Claims</p>
            <p className="text-2xl font-bold text-slate-800">{stats.flagged_claims}</p>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-100 flex items-center">
          <div className="p-4 rounded-lg bg-amber-50 text-amber-600 mr-4">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-500">Avg Risk Score</p>
            <p className="text-2xl font-bold text-slate-800">{formatScore(stats.avg_fraud_score)}</p>
          </div>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-6 border border-slate-100 flex items-center">
          <div className="p-4 rounded-lg bg-amber-50 text-amber-600 mr-4">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <p className="text-sm font-medium text-slate-500">Pending Investigation</p>
            <p className="text-2xl font-bold text-slate-800">{stats.pending_claims ?? 0}</p>
          </div>
        </div>
      </div>

      {/* Settled-claim performance */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-slate-800">Settled-Claim Performance</h3>
            <p className="text-xs text-slate-500">Original predictions vs. ground truth. Pending claims are excluded.</p>
          </div>
          <Link to="/performance" className="text-sm font-medium text-indigo-600 hover:text-indigo-800">Details</Link>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
          <div className="p-4 rounded-lg bg-slate-50">
            <div className="text-2xl font-bold text-slate-800">{settledCount}</div>
            <div className="text-xs text-slate-500 uppercase tracking-wide">Settled</div>
          </div>
          <div className="p-4 rounded-lg bg-emerald-50">
            <div className="text-2xl font-bold text-emerald-700">{perf?.correct_predictions ?? 0}</div>
            <div className="text-xs text-slate-500 uppercase tracking-wide">Correct</div>
          </div>
          <div className="p-4 rounded-lg bg-red-50">
            <div className="text-2xl font-bold text-red-700">{perf?.incorrect_predictions ?? 0}</div>
            <div className="text-xs text-slate-500 uppercase tracking-wide">Incorrect</div>
          </div>
          <div className="p-4 rounded-lg bg-indigo-50">
            <div className="text-2xl font-bold text-indigo-700">
              {perf?.accuracy != null ? `${(perf.accuracy * 100).toFixed(1)}%` : 'N/A'}
            </div>
            <div className="text-xs text-slate-500 uppercase tracking-wide">Accuracy</div>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Claims by Risk Level</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={riskData} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                  {riskData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <RechartsTooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex justify-center space-x-4 mt-2">
            {riskData.map((entry) => (
              <div key={entry.name} className="flex items-center text-sm">
                <div className="w-3 h-3 rounded-full mr-2" style={{ backgroundColor: entry.color }}></div>
                <span className="text-slate-600">{entry.name}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-100">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Claims by Type</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={typeData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="name" axisLine={false} tickLine={false} />
                <YAxis axisLine={false} tickLine={false} allowDecimals={false} />
                <RechartsTooltip cursor={{ fill: '#f1f5f9' }} />
                <Bar dataKey="value" fill="#4f46e5" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Recent Claims Table */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex justify-between items-center">
          <h3 className="text-lg font-semibold text-slate-800">Recent Claims</h3>
          <Link to="/claims" className="text-sm font-medium text-indigo-600 hover:text-indigo-800">View all</Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 text-slate-500 text-sm">
                <th className="px-6 py-3 font-medium">ID</th>
                <th className="px-6 py-3 font-medium">Claimant</th>
                <th className="px-6 py-3 font-medium">Amount</th>
                <th className="px-6 py-3 font-medium">Date</th>
                <th className="px-6 py-3 font-medium">Risk Score</th>
                <th className="px-6 py-3 font-medium">Risk Level</th>
                <th className="px-6 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-sm">
              {recentClaims.length === 0 ? (
                <tr>
                  <td colSpan="7" className="px-6 py-8 text-center text-slate-500">No claims found.</td>
                </tr>
              ) : (
                recentClaims.map((claim) => (
                  <tr key={claim.id} className="hover:bg-slate-50">
                    <td className="px-6 py-4 font-mono text-xs text-slate-500">
                      <Link to={`/claims/${claim.id}`} className="hover:text-indigo-600 hover:underline">{truncateId(claim.id)}</Link>
                    </td>
                    <td className="px-6 py-4 font-medium text-slate-800">{claim.claimant_name}</td>
                    <td className="px-6 py-4">{formatCurrency(claim.claim_amount)}</td>
                    <td className="px-6 py-4 text-slate-500">{formatDate(claim.incident_date)}</td>
                    <td className="px-6 py-4 font-medium">{formatScore(claim.fraud_score)}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${getRiskColor(claim.risk_level)}`}>
                        {claim.risk_level}
                      </span>
                    </td>
                    <td className="px-6 py-4"><StatusBadge claim={claim} /></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;