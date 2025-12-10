"""
Anomaly Detection Agent - Detects unusual financial transactions using Isolation Forest
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any
from datetime import datetime
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import uuid


class AnomalyDetectionAgent:
    """Worker agent for detecting anomalous transactions using Isolation Forest"""
    
    def __init__(self, chroma_manager):
        """
        Initialize Anomaly Detection Agent
        
        Args:
            chroma_manager: FinancialChromaManager instance
        """
        self.chroma_manager = chroma_manager
        
        # Isolation Forest parameters
        self.contamination = 0.1  # Expected % of anomalies (10%)
        self.random_state = 42
        
    def detect_anomalies(self, project_id: str, transactions: List[Dict]) -> Dict[str, Any]:
        """
        Detect anomalous transactions using Isolation Forest algorithm
        
        Args:
            project_id: Project identifier
            transactions: List of transaction dictionaries from ChromaDB
            
        Returns:
            Dict with anomaly detection results
        """
        try:
            print(f"🔍 Running anomaly detection for project {project_id[:8]}...")
            
            if not transactions or len(transactions) < 5:
                print("   ⚠️ Not enough transactions for anomaly detection (minimum: 5)")
                return {
                    'success': False,
                    'message': 'Insufficient transactions for analysis',
                    'count': len(transactions),
                    'anomalies_detected': 0
                }
            
            # Convert transactions to DataFrame
            df = self._prepare_dataframe(transactions)
            
            if df.empty or len(df) < 5:
                print("   ⚠️ No valid numerical data for anomaly detection")
                return {
                    'success': False,
                    'message': 'No valid numerical data',
                    'count': 0,
                    'anomalies_detected': 0
                }
            
            # Extract features for Isolation Forest
            features_df = self._extract_features(df)
            
            # Train Isolation Forest
            iso_forest = IsolationForest(
                contamination=self.contamination,
                random_state=self.random_state,
                n_estimators=100
            )
            
            # Predict anomalies (-1 = anomaly, 1 = normal)
            predictions = iso_forest.fit_predict(features_df)
            
            # Get anomaly scores (lower = more anomalous)
            anomaly_scores = iso_forest.score_samples(features_df)
            
            # Add predictions and scores to dataframe
            df['is_anomaly'] = predictions == -1
            df['anomaly_score'] = anomaly_scores
            
            # Calculate severity (normalized 0-100, higher = more severe)
            df['severity'] = self._calculate_severity(anomaly_scores)
            
            # Filter only anomalies
            anomalies_df = df[df['is_anomaly'] == True].copy()
            
            print(f"   ✅ Detected {len(anomalies_df)} anomalies out of {len(df)} transactions")
            
            # Store anomalies in ChromaDB
            if len(anomalies_df) > 0:
                self._store_anomalies(project_id, anomalies_df)
            
            # Generate summary statistics
            summary = self._generate_summary(df, anomalies_df)
            
            return {
                'success': True,
                'total_transactions': len(df),
                'anomalies_detected': len(anomalies_df),
                'anomaly_rate': round((len(anomalies_df) / len(df)) * 100, 2),
                'summary': summary,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error in anomaly detection: {e}")
            return {
                'success': False,
                'error': str(e),
                'anomalies_detected': 0
            }
    
    def _prepare_dataframe(self, transactions: List[Dict]) -> pd.DataFrame:
        """Convert transactions from ChromaDB format to pandas DataFrame"""
        data = []
        
        for txn in transactions:
            metadata = txn.get('metadata', {})
            
            # Extract relevant fields
            data.append({
                'id': txn.get('id', ''),
                'description': txn.get('text', ''),
                'amount': float(metadata.get('amount', 0)),
                'transaction_type': metadata.get('transaction_type', 'expense'),
                'category': metadata.get('category', 'general'),
                'vendor_recipient': metadata.get('vendor_recipient', ''),
                'date': metadata.get('date', 'unknown'),
                'status': metadata.get('status', 'unknown'),
                'payment_method': metadata.get('payment_method', 'unknown')
            })
        
        df = pd.DataFrame(data)
        
        # Filter out zero amounts
        df = df[df['amount'] > 0]
        
        return df
    
    def _extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract numerical features for Isolation Forest"""
        features = pd.DataFrame()
        
        # Feature 1: Transaction amount (primary feature)
        features['amount'] = df['amount']
        
        # Feature 2: Log-transformed amount (handles scale differences)
        features['log_amount'] = np.log1p(df['amount'])
        
        # Feature 3: Category-based average deviation
        category_avg = df.groupby('category')['amount'].transform('mean')
        features['category_deviation'] = (df['amount'] - category_avg).abs()
        
        # Feature 4: Vendor-based average deviation (if vendor has multiple transactions)
        vendor_counts = df['vendor_recipient'].value_counts()
        frequent_vendors = vendor_counts[vendor_counts > 1].index
        
        vendor_deviation = []
        for idx, row in df.iterrows():
            if row['vendor_recipient'] in frequent_vendors:
                vendor_avg = df[df['vendor_recipient'] == row['vendor_recipient']]['amount'].mean()
                vendor_deviation.append(abs(row['amount'] - vendor_avg))
            else:
                vendor_deviation.append(0)
        
        features['vendor_deviation'] = vendor_deviation
        
        # Feature 5: Global z-score
        features['z_score'] = np.abs((df['amount'] - df['amount'].mean()) / df['amount'].std())
        
        # Standardize features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        return pd.DataFrame(features_scaled, columns=features.columns)
    
    def _calculate_severity(self, anomaly_scores: np.ndarray) -> List[int]:
        """
        Calculate severity level (0-100) from anomaly scores
        Lower scores = more anomalous = higher severity
        """
        # Normalize scores to 0-100 scale
        min_score = anomaly_scores.min()
        max_score = anomaly_scores.max()
        
        # Invert so lower anomaly_score = higher severity
        severity = 100 * (1 - (anomaly_scores - min_score) / (max_score - min_score + 1e-10))
        
        return severity.astype(int).tolist()
    
    def _store_anomalies(self, project_id: str, anomalies_df: pd.DataFrame):
        """Store detected anomalies in ChromaDB"""
        try:
            data_items = []
            
            for _, row in anomalies_df.iterrows():
                # Determine severity level
                severity_score = row['severity']
                if severity_score >= 80:
                    severity_level = 'critical'
                elif severity_score >= 60:
                    severity_level = 'high'
                elif severity_score >= 40:
                    severity_level = 'medium'
                else:
                    severity_level = 'low'
                
                data_items.append({
                    'id': f"anomaly_{project_id[:8]}_{str(uuid.uuid4())[:8]}",
                    'text': f"Anomalous transaction: {row['description']}",
                    'metadata': {
                        'project_id': project_id,
                        'transaction_id': row['id'],
                        'amount': float(row['amount']),
                        'transaction_type': row['transaction_type'],
                        'category': row['category'],
                        'vendor_recipient': row['vendor_recipient'],
                        'date': row['date'],
                        'anomaly_score': float(row['anomaly_score']),
                        'severity': int(row['severity']),
                        'severity_level': severity_level,
                        'status': 'unreviewed',
                        'detected_at': datetime.now().isoformat()
                    }
                })
            
            self.chroma_manager.store_financial_data(
                'anomaly_alerts', data_items, project_id, 'anomaly'
            )
            
            print(f"   ✅ Stored {len(data_items)} anomalies in ChromaDB")
            
        except Exception as e:
            print(f"Error storing anomalies: {e}")
    
    def _generate_summary(self, df: pd.DataFrame, anomalies_df: pd.DataFrame) -> Dict:
        """Generate summary statistics"""
        summary = {
            'total_amount': float(df['amount'].sum()),
            'avg_amount': float(df['amount'].mean()),
            'median_amount': float(df['amount'].median()),
            'std_amount': float(df['amount'].std())
        }
        
        if len(anomalies_df) > 0:
            summary.update({
                'anomaly_total_amount': float(anomalies_df['amount'].sum()),
                'anomaly_avg_amount': float(anomalies_df['amount'].mean()),
                'anomaly_max_amount': float(anomalies_df['amount'].max()),
                'anomaly_categories': anomalies_df['category'].value_counts().to_dict(),
                'severity_distribution': {
                    'critical': int((anomalies_df['severity'] >= 80).sum()),
                    'high': int((anomalies_df['severity'] >= 60).sum() - (anomalies_df['severity'] >= 80).sum()),
                    'medium': int((anomalies_df['severity'] >= 40).sum() - (anomalies_df['severity'] >= 60).sum()),
                    'low': int((anomalies_df['severity'] < 40).sum())
                }
            })
        
        return summary
    
    def get_anomalies(self, project_id: str, filters: Dict = None) -> List[Dict]:
        """Get all detected anomalies for a project"""
        try:
            # Get all anomalies first (ChromaDB metadata filtering can be unreliable)
            anomalies = self.chroma_manager.get_financial_data(
                'anomaly_alerts', project_id, None
            )
            
            # Apply filters in Python for more reliable filtering
            if filters:
                filtered_anomalies = []
                for anomaly in anomalies:
                    metadata = anomaly.get('metadata', {})
                    match = True
                    
                    # Check severity_level filter
                    if 'severity_level' in filters:
                        if metadata.get('severity_level') != filters['severity_level']:
                            match = False
                    
                    # Check status filter
                    if 'status' in filters:
                        if metadata.get('status') != filters['status']:
                            match = False
                    
                    if match:
                        filtered_anomalies.append(anomaly)
                
                anomalies = filtered_anomalies
            
            # Sort by severity (highest first)
            anomalies.sort(
                key=lambda x: x.get('metadata', {}).get('severity', 0),
                reverse=True
            )
            
            return anomalies
            
        except Exception as e:
            print(f"Error getting anomalies: {e}")
            return []
    
    def update_anomaly_status(self, anomaly_id: str, status: str, notes: str = None) -> bool:
        """Update the review status of an anomaly"""
        try:
            # Get current anomaly data
            collection = self.chroma_manager.get_financial_collection('anomaly_alerts')
            if not collection:
                return False
            
            result = collection.get(ids=[anomaly_id], include=['documents', 'metadatas'])
            
            if not result or not result['ids']:
                return False
            
            # Update metadata
            metadata = result['metadatas'][0]
            metadata['status'] = status
            metadata['reviewed_at'] = datetime.now().isoformat()
            
            if notes:
                metadata['review_notes'] = notes
            
            # Update in ChromaDB
            self.chroma_manager.update_financial_data(
                'anomaly_alerts',
                anomaly_id,
                {
                    'text': result['documents'][0],
                    'metadata': metadata
                }
            )
            
            # If reviewed or dismissed, store in reviewed_anomalies collection for history
            if status in ['reviewed', 'dismissed']:
                self._store_reviewed_anomaly(anomaly_id, result['documents'][0], metadata)
            
            return True
            
        except Exception as e:
            print(f"Error updating anomaly status: {e}")
            return False
    
    def _store_reviewed_anomaly(self, anomaly_id: str, document: str, metadata: Dict):
        """Store reviewed anomaly in separate collection for history tracking"""
        try:
            import uuid
            review_data = [{
                'id': f"review_{str(uuid.uuid4())[:8]}_{anomaly_id}",
                'text': document,
                'metadata': {
                    **metadata,
                    'original_anomaly_id': anomaly_id,
                    'review_timestamp': datetime.now().isoformat()
                }
            }]
            
            self.chroma_manager.store_financial_data(
                'reviewed_anomalies',
                review_data,
                metadata.get('project_id'),
                'reviewed_anomaly'
            )
            
            print(f"   ✅ Stored reviewed anomaly in history")
            
        except Exception as e:
            print(f"Error storing reviewed anomaly: {e}")
    
    def get_reviewed_anomalies(self, project_id: str) -> List[Dict]:
        """Get all reviewed anomalies for a project"""
        try:
            reviewed = self.chroma_manager.get_financial_data(
                'reviewed_anomalies', project_id, None
            )
            
            # Sort by review timestamp (most recent first)
            reviewed.sort(
                key=lambda x: x.get('metadata', {}).get('review_timestamp', ''),
                reverse=True
            )
            
            return reviewed
            
        except Exception as e:
            print(f"Error getting reviewed anomalies: {e}")
            return []

