import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Clock, Settings, Play, Database, CheckCircle, Activity } from 'lucide-react';
import { simulateLabels } from '../api/client';

const Simulator = () => {
  const [count, setCount] = useState(20);
  const [fraudRate, setFraudRate] = useState(20);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const navigate = useNavigate();

  const handleSimulate = async () => {
    try {
      setLoading(true);
      setResult(null);
      const claims = await simulateLabels(count, fraudRate / 100);
      const fraudCount = claims.filter(c => c.true_label === true).length;
      setResult({
        total: claims.length,
        fraud: fraudCount,
        legit: claims.length - fraudCount,
      });
    } catch (err) {
      alert('Simulation failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-xl shadow-sm border border-slate-100 overflow-hidden mb-8">
        <div className="p-8 border-b border-slate-100 bg-indigo-600 text-white">
          <div className="flex items-center mb-2">
            <Clock className="w-8 h-8 mr-3" />
            <h2 className="text-2xl font-bold">Delayed Label Simulator</h2>
          </div>
          <p className="text-indigo-100 max-w-2xl">
            In the real world, insurance claims aren't instantly known to be fraud or legitimate. 
            Investigations take weeks. This tool simulates generating historical claims that have 
            already completed their investigation process and received a ground-truth label.
          </p>
        </div>

        <div className="p-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
            <div className="space-y-6">
              <div className="flex items-center text-slate-800 font-semibold mb-2">
                <Settings className="w-5 h-5 mr-2 text-indigo-600" />
                Simulation Parameters
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Number of Claims to Generate: {count}
                </label>
                <input 
                  type="range" 
                  min="5" max="100" step="5"
                  value={count} 
                  onChange={(e) => setCount(Number(e.target.value))}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                />
                <div className="flex justify-between text-xs text-slate-400 mt-1">
                  <span>5</span>
                  <span>100</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Target Fraud Rate: {fraudRate}%
                </label>
                <input 
                  type="range" 
                  min="5" max="50" step="1"
                  value={fraudRate} 
                  onChange={(e) => setFraudRate(Number(e.target.value))}
                  className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                />
                <div className="flex justify-between text-xs text-slate-400 mt-1">
                  <span>5%</span>
                  <span>50%</span>
                </div>
              </div>

              <button 
                onClick={handleSimulate}
                disabled={loading}
                className="w-full py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors flex justify-center items-center"
              >
                {loading ? (
                  <><div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white mr-2"></div> Generating...</>
                ) : (
                  <><Play className="w-5 h-5 mr-2" /> Generate & Label Claims</>
                )}
              </button>
            </div>

            <div className="bg-slate-50 p-6 rounded-xl border border-slate-100">
              <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider mb-4">How it works</h3>
              <ul className="space-y-3 text-sm text-slate-600">
                <li className="flex items-start">
                  <div className="bg-indigo-100 text-indigo-600 rounded-full p-1 mr-3 mt-0.5"><Database className="w-3 h-3" /></div>
                  Generates realistic claim profiles with fraud-correlated features.
                </li>
                <li className="flex items-start">
                  <div className="bg-indigo-100 text-indigo-600 rounded-full p-1 mr-3 mt-0.5"><Activity className="w-3 h-3" /></div>
                  Runs each claim through the ML model to get a fraud prediction score.
                </li>
                <li className="flex items-start">
                  <div className="bg-indigo-100 text-indigo-600 rounded-full p-1 mr-3 mt-0.5"><CheckCircle className="w-3 h-3" /></div>
                  Assigns ground truth labels (Fraud/Legitimate) simulating completed investigation.
                </li>
              </ul>
            </div>
          </div>

          {result && (
            <div className="mt-8">
              <div className="bg-green-50 border border-green-200 rounded-xl p-6 text-center">
                <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
                <h3 className="text-xl font-bold text-green-800 mb-2">Simulation Complete</h3>
                <p className="text-green-700 mb-6">
                  Successfully generated and labeled <strong className="font-bold">{result.total}</strong> claims.
                  <br/>
                  <span className="text-sm">({result.fraud} Fraud, {result.legit} Legitimate)</span>
                </p>
                <div className="flex justify-center space-x-4">
                  <button 
                    onClick={() => navigate('/claims')}
                    className="px-6 py-2 bg-white text-green-700 border border-green-300 font-medium rounded-lg hover:bg-green-50 transition-colors"
                  >
                    View All Claims
                  </button>
                  <button 
                    onClick={() => navigate('/performance')}
                    className="px-6 py-2 bg-green-600 text-white font-medium rounded-lg hover:bg-green-700 transition-colors"
                  >
                    View Model Performance
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Simulator;
