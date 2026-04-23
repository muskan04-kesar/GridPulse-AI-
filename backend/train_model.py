"""
Model Training Script for Power Grid Fault Classification
Trains a Random Forest classifier on extracted electrical features.

Features:
- RMS values per phase
- Total Harmonic Distortion (THD)
- Phase unbalance factors
- Crest factors

Evaluation:
- Confusion Matrix
- Classification Report (precision, recall, F1)
- Cross-validation
"""

import numpy as np
import json
import pickle
from pathlib import Path
from typing import Tuple, Dict, Any
from datetime import datetime

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import (
    confusion_matrix, classification_report, accuracy_score,
    precision_score, recall_score, f1_score
)
from sklearn.preprocessing import StandardScaler
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns

from feature_extractor import PowerFeatureExtractor, extract_features_for_ml
from power_fault_simulator import FAULT_LABELS


class FaultClassifierTrainer:
    """
    Trainer for power grid fault classification models.
    """

    def __init__(self, sampling_rate: int = 1000):
        """
        Initialize trainer.

        Args:
            sampling_rate: Sampling rate in Hz
        """
        self.sampling_rate = sampling_rate
        self.feature_extractor = PowerFeatureExtractor(sampling_rate=sampling_rate)
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = None
        self.training_history = {}

    def prepare_data(self, X: np.ndarray, y: np.ndarray,
                     test_size: float = 0.2,
                     random_state: int = 42) -> Tuple[np.ndarray, ...]:
        """
        Prepare data for training (extract features, split, scale).

        Args:
            X: Raw waveform data (n_samples, window_size, 6)
            y: Labels (n_samples,)
            test_size: Test set proportion
            random_state: Random seed

        Returns:
            Tuple of (X_train, X_test, y_train, y_test, feature_names)
        """
        print("Extracting features from raw waveforms...")

        # Extract features
        X_features, y, feature_names = extract_features_for_ml(X, y, self.sampling_rate)
        self.feature_names = feature_names

        print(f"Feature matrix shape: {X_features.shape}")
        print(f"Features: {feature_names}")

        # Split data (stratified to maintain class balance)
        X_train, X_test, y_train, y_test = train_test_split(
            X_features, y,
            test_size=test_size,
            random_state=random_state,
            stratify=y
        )

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        print(f"\nData split:")
        print(f"  Training samples: {len(X_train)}")
        print(f"  Test samples: {len(X_test)}")
        print(f"  Class distribution (train): {np.bincount(y_train)}")
        print(f"  Class distribution (test): {np.bincount(y_test)}")

        return X_train_scaled, X_test_scaled, y_train, y_test

    def train_random_forest(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        n_estimators: int = 100,
        max_depth: int = 20,
        min_samples_split: int = 5,
        min_samples_leaf: int = 2,
        random_state: int = 42
    ) -> RandomForestClassifier:
        """
        Train Random Forest classifier.

        Args:
            X_train: Scaled training features
            y_train: Training labels
            n_estimators: Number of trees
            max_depth: Maximum tree depth
            min_samples_split: Minimum samples for split
            min_samples_leaf: Minimum samples per leaf
            random_state: Random seed

        Returns:
            Trained RandomForestClassifier
        """
        print(f"\nTraining Random Forest...")
        print(f"  n_estimators: {n_estimators}")
        print(f"  max_depth: {max_depth}")

        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            min_samples_leaf=min_samples_leaf,
            random_state=random_state,
            n_jobs=-1,
            class_weight='balanced'  # Handle any class imbalance
        )

        self.model.fit(X_train, y_train)

        # Store training info
        self.training_history['random_forest'] = {
            'n_estimators': n_estimators,
            'max_depth': max_depth,
            'feature_importances': self.model.feature_importances_
        }

        return self.model

    def evaluate_model(
        self,
        X_test: np.ndarray,
        y_test: np.ndarray,
        model: RandomForestClassifier = None
    ) -> Dict[str, Any]:
        """
        Evaluate model performance.

        Args:
            X_test: Scaled test features
            y_test: Test labels
            model: Model to evaluate (uses self.model if None)

        Returns:
            Dictionary with evaluation metrics
        """
        if model is None:
            model = self.model

        if model is None:
            raise ValueError("No model available. Train a model first.")

        # Predictions
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test) if hasattr(model, 'predict_proba') else None

        # Basic metrics
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average='weighted')
        recall = recall_score(y_test, y_pred, average='weighted')
        f1 = f1_score(y_test, y_pred, average='weighted')

        # Per-class metrics
        class_metrics = {}
        for class_idx in range(len(FAULT_LABELS)):
            class_mask = y_test == class_idx
            if np.sum(class_mask) > 0:
                class_metrics[FAULT_LABELS[class_idx]] = {
                    'precision': precision_score(y_test, y_pred, labels=[class_idx], average='micro'),
                    'recall': recall_score(y_test, y_pred, labels=[class_idx], average='micro'),
                    'f1': f1_score(y_test, y_pred, labels=[class_idx], average='micro'),
                    'support': int(np.sum(class_mask))
                }

        # Confusion matrix
        cm = confusion_matrix(y_test, y_pred)

        # Cross-validation
        cv_scores = cross_val_score(model, X_test, y_test, cv=5, scoring='accuracy')

        results = {
            'accuracy': float(accuracy),
            'precision': float(precision),
            'recall': float(recall),
            'f1_score': float(f1),
            'class_metrics': class_metrics,
            'confusion_matrix': cm.tolist(),
            'cross_validation': {
                'mean_accuracy': float(cv_scores.mean()),
                'std_accuracy': float(cv_scores.std()),
                'scores': cv_scores.tolist()
            },
            'predictions': y_pred.tolist(),
            'true_labels': y_test.tolist()
        }

        if y_pred_proba is not None:
            results['prediction_probabilities'] = y_pred_proba.tolist()

        return results

    def plot_confusion_matrix(
        self,
        cm: np.ndarray,
        save_path: str = 'confusion_matrix.png',
        title: str = 'Confusion Matrix'
    ):
        """
        Plot and save confusion matrix.

        Args:
            cm: Confusion matrix (n_classes, n_classes)
            save_path: Path to save figure
            title: Plot title
        """
        cm = np.array(cm)
        class_names = [FAULT_LABELS[i] for i in range(len(FAULT_LABELS))]

        plt.figure(figsize=(10, 8))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                    xticklabels=class_names, yticklabels=class_names)
        plt.title(title)
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"Confusion matrix saved to: {save_path}")

    def plot_feature_importance(
        self,
        save_path: str = 'feature_importance.png',
        top_n: int = 15
    ):
        """
        Plot and save feature importance chart.

        Args:
            save_path: Path to save figure
            top_n: Number of top features to show
        """
        if self.model is None or self.feature_names is None:
            print("No model or feature names available for plotting.")
            return

        importances = self.model.feature_importances_
        indices = np.argsort(importances)[::-1][:top_n]

        plt.figure(figsize=(12, 6))
        plt.bar(range(top_n), importances[indices])
        plt.xticks(range(top_n), [self.feature_names[i] for i in indices], rotation=45, ha='right')
        plt.title(f'Top {top_n} Feature Importances')
        plt.xlabel('Feature')
        plt.ylabel('Importance')
        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"Feature importance saved to: {save_path}")

    def save_model(self, path: str = 'fault_classifier.pkl'):
        """
        Save trained model and preprocessing objects.

        Args:
            path: Path to save model
        """
        if self.model is None:
            raise ValueError("No model to save. Train a model first.")

        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'sampling_rate': self.sampling_rate,
            'training_history': self.training_history,
            'timestamp': datetime.now().isoformat()
        }

        with open(path, 'wb') as f:
            pickle.dump(model_data, f)

        print(f"Model saved to: {path}")

    def load_model(self, path: str = 'fault_classifier.pkl'):
        """
        Load trained model and preprocessing objects.

        Args:
            path: Path to load model from
        """
        with open(path, 'rb') as f:
            model_data = pickle.load(f)

        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_names = model_data['feature_names']
        self.sampling_rate = model_data['sampling_rate']
        self.training_history = model_data.get('training_history', {})

        print(f"Model loaded from: {path}")
        return self


def generate_and_train(
    samples_per_class: int = 500,
    window_size: int = 100,
    n_estimators: int = 100,
    max_depth: int = 20,
    save_model: bool = True
) -> Tuple[FaultClassifierTrainer, Dict[str, Any]]:
    """
    Complete pipeline: generate data, train model, evaluate, and save.

    Args:
        samples_per_class: Samples per fault class
        window_size: Window size for feature extraction
        n_estimators: Random Forest trees
        max_depth: Max tree depth
        save_model: Whether to save the model

    Returns:
        Tuple of (trainer, evaluation_results)
    """
    print("=" * 60)
    print("Power Grid Fault Classification - Model Training")
    print("=" * 60)

    # Step 1: Generate dataset
    print("\n[Step 1] Generating labeled dataset...")
    from power_fault_simulator import PowerFaultSimulator

    simulator = PowerFaultSimulator(duration_seconds=1.0, sampling_rate=1000)
    X, y = simulator.generate_labeled_dataset(
        samples_per_class=samples_per_class,
        window_size=window_size
    )

    # Step 2: Initialize trainer
    print("\n[Step 2] Initializing trainer...")
    trainer = FaultClassifierTrainer(sampling_rate=1000)

    # Step 3: Prepare data
    print("\n[Step 3] Preparing data...")
    X_train, X_test, y_train, y_test = trainer.prepare_data(X, y, test_size=0.2)

    # Step 4: Train model
    print("\n[Step 4] Training Random Forest classifier...")
    trainer.train_random_forest(
        X_train, y_train,
        n_estimators=n_estimators,
        max_depth=max_depth
    )

    # Step 5: Evaluate
    print("\n[Step 5] Evaluating model...")
    results = trainer.evaluate_model(X_test, y_test)

    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    print(f"Accuracy: {results['accuracy']:.4f}")
    print(f"Precision (weighted): {results['precision']:.4f}")
    print(f"Recall (weighted): {results['recall']:.4f}")
    print(f"F1 Score (weighted): {results['f1_score']:.4f}")
    print(f"\nCross-Validation Accuracy: {results['cross_validation']['mean_accuracy']:.4f} (+/- {results['cross_validation']['std_accuracy']:.4f})")

    print("\nPer-Class Metrics:")
    for class_name, metrics in results['class_metrics'].items():
        print(f"  {class_name}: P={metrics['precision']:.3f}, R={metrics['recall']:.3f}, F1={metrics['f1']:.3f}")

    print("\nConfusion Matrix:")
    cm = np.array(results['confusion_matrix'])
    class_names = [FAULT_LABELS[i] for i in range(len(FAULT_LABELS))]
    print(f"Labels: {class_names}")
    print(cm)

    # Step 6: Visualize
    print("\n[Step 6] Generating visualizations...")
    trainer.plot_confusion_matrix(
        cm,
        save_path='confusion_matrix.png',
        title='Fault Classification Confusion Matrix'
    )
    trainer.plot_feature_importance(
        save_path='feature_importance.png',
        top_n=15
    )

    # Step 7: Save model
    if save_model:
        print("\n[Step 7] Saving model...")
        trainer.save_model('fault_classifier.pkl')

        # Save evaluation report
        report = {
            'training_config': {
                'samples_per_class': samples_per_class,
                'window_size': window_size,
                'n_estimators': n_estimators,
                'max_depth': max_depth
            },
            'evaluation_results': results,
            'feature_names': trainer.feature_names,
            'timestamp': datetime.now().isoformat()
        }

        with open('training_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        print("Training report saved to: training_report.json")

    print("\n" + "=" * 60)
    print("Training Complete!")
    print("=" * 60)
    print("\nGenerated files:")
    print("  - fault_classifier.pkl (trained model)")
    print("  - confusion_matrix.png (visualization)")
    print("  - feature_importance.png (visualization)")
    print("  - training_report.json (metrics)")

    return trainer, results


if __name__ == "__main__":
    trainer, results = generate_and_train(
        samples_per_class=500,  # 500 samples x 4 classes = 2000 total
        window_size=100,         # 100 samples = 100ms at 1kHz
        n_estimators=100,
        max_depth=20,
        save_model=True
    )
