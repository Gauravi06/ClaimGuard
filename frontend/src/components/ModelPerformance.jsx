import React, { useState, useEffect } from 'react';
import { getModelPerformance } from '../api/client';
import { Activity, Target, AlertTriangle, Maximize, BarChart2 } from 'lucide-react';

const ModelPerformance = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const perfData = await getModelPerformance();
        setData(perfData);
      } catch (err) {
        setError('Failed to load performance metrics.');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <div className="flex justify-center mt-20"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div></div>;
  if (error) return <div className="text-red-500 bg-red-50 p-4 rounded-lg">{error}</div>;

  if (data?.total_labeled === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-12 text-center max-w-2xl mx-auto mt-10">
        <Activity className="w-16 h-16 text-slate-300 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-slate-800 mb-2">Not Enough Data</h2>
        <p className="text-slate-500 mb-6">No labeled claims yet. Use the Simulator or manually label claims to see model performance metrics.</p>
      </div>
    );
  }

  const cm = data.confusion_matrix;

  const MetricCard = ({ title, value, icon: Icon, color }) => (
    <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6 flex flex-col items-center text-center">
      <div className={`p-3 rounded-full mb-4 ${color}`}>
        <Icon className="w-6 h-6" />
      </div>
      <div className="text-slate-500 text-sm font-medium mb-1">{title}</div>
      <div className="text-2xl font-bold text-slate-800">
        {value !== null && value !== undefined ? `${(value * 100).toFixed(1)}%` : 'N/A'}
      </div>
    </div>
  );

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex justify-between items-end mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Model Performance</h2>
          <p className="text-slate-500 mt-1">Evaluated on {data.total_labeled} labeled claims out of {data.total_predictions} total.</p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <MetricCard title="Accuracy" value={data.accuracy} icon={Target} color="bg-blue-50 text-blue-600" />
        <MetricCard title="Precision" value={data.precision} icon={Maximize} color="bg-indigo-50 text-indigo-600" />
        <MetricCard title="Recall" value={data.recall} icon={AlertTriangle} color="bg-amber-50 text-amber-600" />
        <MetricCard title="F1 Score" value={data.f1_score} icon={Activity} color="bg-emerald-50 text-emerald-600" />
        <MetricCard title="ROC AUC" value={data.roc_auc} icon={BarChart2} color="bg-purple-50 text-purple-600" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
          <h3 className="text-lg font-bold text-slate-800 mb-6">Confusion Matrix</h3>
          
          <div className="grid grid-cols-3 gap-2 text-center max-w-sm mx-auto">
            {/* Header */}
            <div></div>
            <div className="font-semibold text-slate-600 text-sm pb-2">Predicted Legit</div>
            <div className="font-semibold text-slate-600 text-sm pb-2">Predicted Fraud</div>
            
            {/* Actual Legitimate */}
            <div className="font-semibold text-slate-600 text-sm flex items-center justify-end pr-4">Actual Legit</div>
            <div className="bg-green-100 text-green-800 p-4 rounded-lg flex flex-col justify-center">
              <span className="text-2xl font-bold">{cm.tn}</span>
              <span className="text-xs opacity-70">True Negatives</span>
            </div>
            <div className="bg-red-50 text-red-600 p-4 rounded-lg flex flex-col justify-center border border-red-100">
              <span className="text-2xl font-bold">{cm.fp}</span>
              <span className="text-xs opacity-70">False Positives</span>
            </div>
            
            {/* Actual Fraud */}
            <div className="font-semibold text-slate-600 text-sm flex items-center justify-end pr-4">Actual Fraud</div>
            <div className="bg-red-50 text-red-600 p-4 rounded-lg flex flex-col justify-center border border-red-100">
              <span className="text-2xl font-bold">{cm.fn}</span>
              <span className="text-xs opacity-70">False Negatives</span>
            </div>
            <div className="bg-green-100 text-green-800 p-4 rounded-lg flex flex-col justify-center">
              <span className="text-2xl font-bold">{cm.tp}</span>
              <span className="text-xs opacity-70">True Positives</span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
          <h3 className="text-lg font-bold text-slate-800 mb-4">Metrics Explanation</h3>
          <div className="space-y-4 text-sm text-slate-600">
            <div>
              <strong className="text-slate-800">Precision:</strong> Out of all claims the model flagged as fraud, how many were actually fraud? High precision means fewer false alarms.
            </div>
            <div>
              <strong className="text-slate-800">Recall:</strong> Out of all actual fraudulent claims, how many did the model catch? High recall means fewer missed frauds.
            </div>
            <div>
              <strong className="text-slate-800">F1 Score:</strong> The harmonic mean of precision and recall. A good overall measure when the classes are imbalanced.
            </div>
            <div className="p-4 bg-indigo-50 text-indigo-800 rounded-lg mt-4">
              <p>In fraud detection, <strong>Recall</strong> is often prioritized over Precision, because missing a fraudulent claim is usually more costly than manually reviewing a legitimate one (False Positive).</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ModelPerformance;
