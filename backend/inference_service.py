"""
ML Inference Service for Power Grid Fault Classification
Loads trained model and provides real-time predictions on sliding window data.
"""

import numpy as np
import pickle
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
from collections import deque
import uuid

from feature_extractor import PowerFeatureExtractor, extract_features_for_ml
from power_fault_simulator import FAULT_LABELS


class FaultInferenceService:
    """
    Real-time inference service for fault classification.
    Processes sliding window data and returns predictions with confidence scores.
    """

    def __init__(self, model_path: str = 'fault_classifier.pkl',
                 window_size_ms: int = 100,
                 sampling_rate: int = 1000):
        """
        Initialize inference service.

        Args:
            model_path: Path to trained model file
            window_size_ms: Sliding window size in milliseconds
            sampling_rate: Sampling rate in Hz
        """
        self.model_path = model_path
        self.window_size_ms = window_size_ms
        self.sampling_rate = sampling_rate
        self.window_size_samples = int(sampling_rate * window_size_ms / 1000)

        self.model = None
        self.scaler = None
        self.feature_extractor = None
        self.feature_names = None

        # Sliding window buffer (6 channels: V_A, V_B, V_C, I_A, I_B, I_C)
        self.data_buffer = deque(maxlen=self.window_size_samples)
        self.buffer_full = False

        # Prediction history for smoothing
        self.prediction_history = deque(maxlen=5)
        self.last_prediction = None

    def load_model(self, model_path: str = None) -> bool:
        """
        Load trained model from disk.

        Args:
            model_path: Override default model path

        Returns:
            True if successful
        """
        path = model_path or self.model_path

        try:
            with open(path, 'rb') as f:
                model_data = pickle.load(f)

            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_names = model_data['feature_names']
            self.sampling_rate = model_data.get('sampling_rate', self.sampling_rate)

            # Reinitialize feature extractor with correct sampling rate
            self.feature_extractor = PowerFeatureExtractor(
                sampling_rate=self.sampling_rate
            )

            # Reset buffer with correct size
            self.window_size_samples = int(
                self.sampling_rate * self.window_size_ms / 1000
            )
            self.data_buffer = deque(maxlen=self.window_size_samples)
            self.buffer_full = False

            print(f"Model loaded successfully from: {path}")
            print(f"  Window size: {self.window_size_samples} samples ({self.window_size_ms}ms)")
            print(f"  Features: {len(self.feature_names)}")

            return True

        except FileNotFoundError:
            print(f"Model file not found: {path}")
            print("Please train a model first using train_model.py")
            return False
        except Exception as e:
            print(f"Error loading model: {e}")
            return False

    def add_sample(self, voltages: Dict[str, float], currents: Dict[str, float]) -> Optional[Dict[str, Any]]:
        """
        Add a new sample to the sliding window and return prediction if buffer is full.

        Args:
            voltages: Dict with voltage_A, voltage_B, voltage_C
            currents: Dict with current_A, current_B, current_C

        Returns:
            Prediction dict if buffer is full, None otherwise
        """
        # Add to buffer
        sample = [
            voltages.get('voltage_A', 0),
            voltages.get('voltage_B', 0),
            voltages.get('voltage_C', 0),
            currents.get('current_A', 0),
            currents.get('current_B', 0),
            currents.get('current_C', 0)
        ]
        self.data_buffer.append(sample)

        # Check if buffer is full
        if len(self.data_buffer) >= self.window_size_samples:
            self.buffer_full = True
            return self.predict()

        return None

    def add_sample_array(self, sample: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Add a sample from numpy array to the sliding window.

        Args:
            sample: Array of shape (6,) with [V_A, V_B, V_C, I_A, I_B, I_C]

        Returns:
            Prediction dict if buffer is full, None otherwise
        """
        self.data_buffer.append(sample.tolist())

        if len(self.data_buffer) >= self.window_size_samples:
            self.buffer_full = True
            return self.predict()

        return None

    def predict(self) -> Optional[Dict[str, Any]]:
        """
        Make prediction on current window data.

        Returns:
            Prediction dict with status, type, confidence, location estimate
            None if model not loaded or buffer not full
        """
        if self.model is None or not self.buffer_full:
            return None

        # Convert buffer to array
        window_data = np.array(list(self.data_buffer))  # Shape: (window_size, 6)

        # Extract features
        try:
            features = self.feature_extractor.extract_features_from_window(window_data)
            features_scaled = self.scaler.transform([features])
        except Exception as e:
            print(f"Feature extraction error: {e}")
            return None

        # Get prediction and probabilities
        prediction = self.model.predict(features_scaled)[0]
        probabilities = self.model.predict_proba(features_scaled)[0]

        # Add to history for smoothing
        self.prediction_history.append(prediction)

        # Get most common prediction in history (smoothing)
        if len(self.prediction_history) >= 3:
            smoothed_prediction = int(np.bincount(list(self.prediction_history)).argmax())
        else:
            smoothed_prediction = int(prediction)

        # Build result
        fault_type = FAULT_LABELS.get(smoothed_prediction, "Unknown")
        confidence = float(probabilities[smoothed_prediction])

        # Determine status
        status = "NORMAL" if smoothed_prediction == 0 else "FAULT"

        # Estimate location (simplified - based on which phase has highest deviation)
        location_est = self._estimate_fault_location(window_data)

        result = {
            "status": status,
            "type": fault_type if status == "FAULT" else "Normal",
            "fault_label": smoothed_prediction,
            "confidence": round(confidence, 4),
            "all_probabilities": {
                FAULT_LABELS[i]: round(float(probabilities[i]), 4)
                for i in range(len(probabilities))
            },
            "location_est": location_est,
            "timestamp": datetime.now().isoformat(),
            "window_size_ms": self.window_size_ms,
            "fault_id": str(uuid.uuid4()) if status == "FAULT" else None
        }

        self.last_prediction = result
        return result

    def _estimate_fault_location(self, window_data: np.ndarray) -> str:
        """
        Estimate fault location based on phase analysis.
        Simplified estimation based on which phase shows most deviation.

        Args:
            window_data: Window of data (window_size, 6)

        Returns:
            Location estimate string
        """
        # Calculate RMS per phase
        v_rms = [
            np.sqrt(np.mean(window_data[:, 0] ** 2)),
            np.sqrt(np.mean(window_data[:, 1] ** 2)),
            np.sqrt(np.mean(window_data[:, 2] ** 2))
        ]
        c_rms = [
            np.sqrt(np.mean(window_data[:, 3] ** 2)),
            np.sqrt(np.mean(window_data[:, 4] ** 2)),
            np.sqrt(np.mean(window_data[:, 5] ** 2))
        ]

        # Find phase with highest current deviation (indicates faulted phase)
        c_avg = np.mean(c_rms)
        deviations = [abs(c - c_avg) / c_avg if c_avg > 0 else 0 for c in c_rms]
        max_dev_phase = np.argmax(deviations)

        phase_names = ['A', 'B', 'C']

        # If all phases relatively balanced, fault might be downstream
        if max(deviations) < 0.1:
            return "Downstream (balanced fault)"

        return f"Phase {phase_names[max_dev_phase]} - Estimated Pole #42"

    def get_buffer_status(self) -> Dict[str, Any]:
        """Get current buffer status."""
        return {
            "buffer_size": len(self.data_buffer),
            "window_size": self.window_size_samples,
            "buffer_full": self.buffer_full,
            "buffer_percentage": round(len(self.data_buffer) / self.window_size_samples * 100, 2)
        }

    def reset_buffer(self):
        """Reset the data buffer."""
        self.data_buffer.clear()
        self.buffer_full = False
        self.prediction_history.clear()
        self.last_prediction = None

    def batch_predict(self, X: np.ndarray) -> List[Dict[str, Any]]:
        """
        Make predictions on a batch of windows.

        Args:
            X: Array of shape (n_samples, window_size, 6)

        Returns:
            List of prediction dicts
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load_model() first.")

        results = []
        for i in range(X.shape[0]):
            window_data = X[i]
            features = self.feature_extractor.extract_features_from_window(window_data)
            features_scaled = self.scaler.transform([features])

            prediction = self.model.predict(features_scaled)[0]
            probabilities = self.model.predict_proba(features_scaled)[0]

            fault_type = FAULT_LABELS.get(int(prediction), "Unknown")
            confidence = float(probabilities[prediction])
            status = "NORMAL" if prediction == 0 else "FAULT"

            results.append({
                "status": status,
                "type": fault_type if status == "FAULT" else "Normal",
                "fault_label": int(prediction),
                "confidence": round(confidence, 4),
                "all_probabilities": {
                    FAULT_LABELS[i]: round(float(probabilities[i]), 4)
                    for i in range(len(probabilities))
                },
                "fault_id": str(uuid.uuid4()) if status == "FAULT" else None
            })

        return results


def create_inference_service(model_path: str = 'fault_classifier.pkl') -> FaultInferenceService:
    """
    Factory function to create and initialize inference service.

    Args:
        model_path: Path to trained model

    Returns:
        Initialized FaultInferenceService
    """
    service = FaultInferenceService(model_path=model_path)
    service.load_model()
    return service


# Demo/test function
if __name__ == "__main__":
    print("=" * 60)
    print("Fault Inference Service - Demo")
    print("=" * 60)

    # Create service
    service = create_inference_service()

    if service.model is None:
        print("\nModel not loaded. Please run train_model.py first.")
    else:
        # Simulate incoming data
        print("\nSimulating incoming 3-phase data...")

        from power_fault_simulator import PowerFaultSimulator

        simulator = PowerFaultSimulator(duration_seconds=0.5, sampling_rate=1000)

        # Generate a fault cycle
        _, phase_data, fault_info = simulator.generate_3phase_cycle(
            fault_probability=1.0,
            lg_fault_weight=1.0,
            ll_fault_weight=0.0,
            hif_fault_weight=0.0
        )

        print(f"\nActual fault type: {fault_info['type']}")
        print(f"Description: {fault_info['description']}")

        # Stream data through inference service
        print("\nStreaming data through inference service...")

        predictions = []
        for i in range(len(simulator.time)):
            voltages = {
                'voltage_A': phase_data['voltage_A'][i],
                'voltage_B': phase_data['voltage_B'][i],
                'voltage_C': phase_data['voltage_C'][i]
            }
            currents = {
                'current_A': phase_data['current_A'][i],
                'current_B': phase_data['current_B'][i],
                'current_C': phase_data['current_C'][i]
            }

            result = service.add_sample(voltages, currents)
            if result:
                predictions.append(result)

        # Show last few predictions
        if predictions:
            print(f"\nTotal predictions made: {len(predictions)}")
            print("\nLast 5 predictions:")
            for i, pred in enumerate(predictions[-5:]):
                print(f"  {i+1}. Status: {pred['status']}, Type: {pred['type']}, "
                      f"Confidence: {pred['confidence']:.2%}")
