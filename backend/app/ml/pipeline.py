import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from typing import Dict, Any, Tuple, List
from app.ml.dataset import generate_synthetic_data

class MLPipeline:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        self.feature_names = [
            'claim_amount', 'claim_type_encoded', 'days_to_report', 
            'prior_claims_count', 'police_report_filed', 'witnesses', 
            'amount_to_avg_ratio'
        ]
        self.is_trained = False
        self.claim_type_map = {'auto': 0, 'health': 1, 'property': 2, 'life': 3}
        self.avg_amounts = {0: 4000, 1: 12000, 2: 8000, 3: 50000}

    def train(self):
        df = generate_synthetic_data(n_samples=500)
        X = df[self.feature_names]
        y = df['is_fraud']
        self.model.fit(X, y)
        self.is_trained = True
        
    def _extract_features(self, claim_data: Dict[str, Any]) -> Tuple[pd.DataFrame, List[float]]:
        claim_type_encoded = self.claim_type_map.get(claim_data['claim_type'].lower(), 0)
        amount_to_avg_ratio = claim_data['claim_amount'] / self.avg_amounts.get(claim_type_encoded, 10000)
        
        feature_values = [
            claim_data['claim_amount'],
            claim_type_encoded,
            claim_data['days_to_report'],
            claim_data['prior_claims_count'],
            int(claim_data['police_report_filed']),
            claim_data['witnesses'],
            amount_to_avg_ratio
        ]
        
        df = pd.DataFrame([feature_values], columns=self.feature_names)
        return df, feature_values

    def predict(self, claim_data: Dict[str, Any]) -> float:
        if not self.is_trained:
            return 0.0
        X, _ = self._extract_features(claim_data)
        return float(self.model.predict_proba(X)[0][1])
        
    def explain(self, claim_data: Dict[str, Any], score: float) -> List[Dict[str, Any]]:
        if not self.is_trained:
            return []
            
        _, feature_values = self._extract_features(claim_data)
        importances = self.model.feature_importances_
        
        explanations = []
        for name, imp, val in zip(self.feature_names, importances, feature_values):
            if imp > 0.05:
                direction = "up"
                if name == "witnesses" and val > 0: direction = "down"
                if name == "police_report_filed" and val == 1: direction = "down"
                if name == "days_to_report" and val > 15: direction = "up"
                if name == "claim_amount" and val > 10000: direction = "up"
                if name == "prior_claims_count" and val > 1: direction = "up"
                
                explanations.append({
                    "feature": name,
                    "importance": float(imp),
                    "value": float(val),
                    "direction": direction
                })
        
        explanations.sort(key=lambda x: x["importance"], reverse=True)
        return explanations

ml_pipeline = MLPipeline()
