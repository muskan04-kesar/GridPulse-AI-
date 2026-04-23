"""
Feature Extractor for Power Grid Fault Classification
Extracts electrical indicators from 3-phase waveforms for ML model input.

Features:
- RMS (Root Mean Square): True voltage/current levels per phase
- THD (Total Harmonic Distortion): High-frequency noise from arcing/non-linear loads
- Phase Unbalance: Asymmetry between phases A, B, C
- Crest Factor: Peak/RMS ratio for detecting transients
- Zero-Crossing Rate: Frequency deviation detection
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy import fft
from scipy.stats import skew, kurtosis


class PowerFeatureExtractor:
    """
    Extracts interpretable electrical features from 3-phase power waveforms.
    Designed for fault classification in Indian grid (50Hz, 230V RMS).
    """

    def __init__(self, sampling_rate: int = 1000, fundamental_freq: float = 50.0):
        """
        Initialize feature extractor.

        Args:
            sampling_rate: Samples per second (Hz)
            fundamental_freq: Fundamental frequency (50Hz for Indian grid)
        """
        self.sampling_rate = sampling_rate
        self.fundamental_freq = fundamental_freq
        self.nyquist = sampling_rate / 2

    def calculate_rms(self, signal: np.ndarray) -> float:
        """
        Calculate RMS (Root Mean Square) value of a signal.

        Args:
            signal: Input signal array

        Returns:
            RMS value
        """
        return np.sqrt(np.mean(signal ** 2))

    def calculate_rms_per_phase(self, voltages: Dict[str, np.ndarray],
                                 currents: Dict[str, np.ndarray]) -> Dict[str, float]:
        """
        Calculate RMS values for each phase.

        Args:
            voltages: Dict with voltage_A, voltage_B, voltage_C
            currents: Dict with current_A, current_B, current_C

        Returns:
            Dict with RMS values for each phase
        """
        return {
            'voltage_rms_A': self.calculate_rms(voltages['voltage_A']),
            'voltage_rms_B': self.calculate_rms(voltages['voltage_B']),
            'voltage_rms_C': self.calculate_rms(voltages['voltage_C']),
            'current_rms_A': self.calculate_rms(currents['current_A']),
            'current_rms_B': self.calculate_rms(currents['current_B']),
            'current_rms_C': self.calculate_rms(currents['current_C']),
            'voltage_rms_avg': np.mean([
                self.calculate_rms(voltages['voltage_A']),
                self.calculate_rms(voltages['voltage_B']),
                self.calculate_rms(voltages['voltage_C'])
            ]),
            'current_rms_avg': np.mean([
                self.calculate_rms(currents['current_A']),
                self.calculate_rms(currents['current_B']),
                self.calculate_rms(currents['current_C'])
            ])
        }

    def calculate_thd(self, signal: np.ndarray, n_harmonics: int = 10) -> float:
        """
        Calculate Total Harmonic Distortion (THD).

        THD = sqrt(V2^2 + V3^2 + ... + Vn^2) / V1

        Args:
            signal: Input signal array
            n_harmonics: Number of harmonics to consider

        Returns:
            THD as a ratio (multiply by 100 for percentage)
        """
        # Compute FFT
        n = len(signal)
        fft_result = fft.fft(signal)
        magnitude = np.abs(fft_result[:n // 2])

        # Frequency resolution
        freq_resolution = self.sampling_rate / n
        frequencies = np.arange(len(magnitude)) * freq_resolution

        # Find fundamental (50Hz)
        fundamental_idx = np.argmin(np.abs(frequencies - self.fundamental_freq))

        # Get fundamental magnitude
        fundamental_mag = magnitude[fundamental_idx]

        if fundamental_mag < 1e-10:
            return 0.0

        # Sum harmonic magnitudes (2nd to nth harmonic)
        harmonic_power = 0.0
        for h in range(2, n_harmonics + 1):
            harmonic_freq = h * self.fundamental_freq
            harmonic_idx = np.argmin(np.abs(frequencies - harmonic_freq))
            harmonic_power += magnitude[harmonic_idx] ** 2

        thd = np.sqrt(harmonic_power) / fundamental_mag
        return thd

    def calculate_thd_per_phase(self, voltages: Dict[str, np.ndarray],
                                 currents: Dict[str, np.ndarray],
                                 n_harmonics: int = 10) -> Dict[str, float]:
        """
        Calculate THD for each phase voltage and current.

        Args:
            voltages: Dict with voltage_A, voltage_B, voltage_C
            currents: Dict with current_A, current_B, current_C
            n_harmonics: Number of harmonics to consider

        Returns:
            Dict with THD values for each phase
        """
        return {
            'thd_voltage_A': self.calculate_thd(voltages['voltage_A'], n_harmonics),
            'thd_voltage_B': self.calculate_thd(voltages['voltage_B'], n_harmonics),
            'thd_voltage_C': self.calculate_thd(voltages['voltage_C'], n_harmonics),
            'thd_current_A': self.calculate_thd(currents['current_A'], n_harmonics),
            'thd_current_B': self.calculate_thd(currents['current_B'], n_harmonics),
            'thd_current_C': self.calculate_thd(currents['current_C'], n_harmonics),
            'thd_voltage_avg': np.mean([
                self.calculate_thd(voltages['voltage_A'], n_harmonics),
                self.calculate_thd(voltages['voltage_B'], n_harmonics),
                self.calculate_thd(voltages['voltage_C'], n_harmonics)
            ]),
            'thd_current_avg': np.mean([
                self.calculate_thd(currents['current_A'], n_harmonics),
                self.calculate_thd(currents['current_B'], n_harmonics),
                self.calculate_thd(currents['current_C'], n_harmonics)
            ])
        }

    def calculate_phase_unbalance(self, voltages: Dict[str, np.ndarray],
                                   currents: Dict[str, np.ndarray]) -> Dict[str, float]:
        """
        Calculate phase unbalance factors.

        Phase unbalance indicates asymmetrical faults (like LG faults).
        Uses NEMA definition: max deviation from average / average

        Args:
            voltages: Dict with voltage_A, voltage_B, voltage_C
            currents: Dict with current_A, current_B, current_C

        Returns:
            Dict with unbalance factors
        """
        v_rms = [
            self.calculate_rms(voltages['voltage_A']),
            self.calculate_rms(voltages['voltage_B']),
            self.calculate_rms(voltages['voltage_C'])
        ]
        c_rms = [
            self.calculate_rms(currents['current_A']),
            self.calculate_rms(currents['current_B']),
            self.calculate_rms(currents['current_C'])
        ]

        v_avg = np.mean(v_rms)
        c_avg = np.mean(c_rms)

        # NEMA unbalance: max deviation / average
        voltage_unbalance = max(abs(v - v_avg) for v in v_rms) / v_avg if v_avg > 0 else 0
        current_unbalance = max(abs(c - c_avg) for c in c_rms) / c_avg if c_avg > 0 else 0

        # Also calculate zero-sequence component (indicates ground faults)
        # V0 = (Va + Vb + Vc) / 3
        v0_component = np.abs(np.mean([
            voltages['voltage_A'] + voltages['voltage_B'] + voltages['voltage_C']
        ], axis=0))
        zero_sequence_ratio = self.calculate_rms(v0_component) / v_avg if v_avg > 0 else 0

        return {
            'voltage_unbalance': voltage_unbalance,
            'current_unbalance': current_unbalance,
            'zero_sequence_ratio': zero_sequence_ratio
        }

    def calculate_crest_factor(self, signal: np.ndarray) -> float:
        """
        Calculate crest factor (peak/RMS ratio).

        High crest factor indicates transients or impulses.
        For pure sine wave: crest factor = sqrt(2) ≈ 1.414

        Args:
            signal: Input signal array

        Returns:
            Crest factor
        """
        rms = self.calculate_rms(signal)
        peak = np.max(np.abs(signal))
        return peak / rms if rms > 0 else 0

    def calculate_crest_factors(self, voltages: Dict[str, np.ndarray],
                                 currents: Dict[str, np.ndarray]) -> Dict[str, float]:
        """Calculate crest factors for all phases."""
        return {
            'crest_voltage_A': self.calculate_crest_factor(voltages['voltage_A']),
            'crest_voltage_B': self.calculate_crest_factor(voltages['voltage_B']),
            'crest_voltage_C': self.calculate_crest_factor(voltages['voltage_C']),
            'crest_current_A': self.calculate_crest_factor(currents['current_A']),
            'crest_current_B': self.calculate_crest_factor(currents['current_B']),
            'crest_current_C': self.calculate_crest_factor(currents['current_C'])
        }

    def calculate_zero_crossing_rate(self, signal: np.ndarray) -> float:
        """
        Calculate zero-crossing rate.

        Useful for detecting frequency deviations.
        For 50Hz: expected ZCR = 100 zero crossings per second

        Args:
            signal: Input signal array

        Returns:
            Zero crossings per second
        """
        # Find zero crossings
        sign_changes = np.where(np.diff(np.sign(signal)))[0]
        n_crossings = len(sign_changes)

        # Convert to rate (crossings per second)
        duration = len(signal) / self.sampling_rate
        return n_crossings / duration

    def calculate_waveform_features(self, signal: np.ndarray) -> Dict[str, float]:
        """
        Calculate statistical features of waveform shape.

        Args:
            signal: Input signal array

        Returns:
            Dict with skewness, kurtosis, and other shape features
        """
        return {
            'skewness': skew(signal),
            'kurtosis': kurtosis(signal),
            'std_dev': np.std(signal),
            'variance': np.var(signal),
            'peak_to_peak': np.max(signal) - np.min(signal),
            'mean_abs_value': np.mean(np.abs(signal))
        }

    def extract_features_from_window(
        self,
        window_data: np.ndarray,
        channel_names: List[str] = None
    ) -> np.ndarray:
        """
        Extract comprehensive feature vector from a data window.

        Args:
            window_data: Array of shape (window_size, n_channels)
                        Default channels: V_A, V_B, V_C, I_A, I_B, I_C
            channel_names: Optional list of channel names

        Returns:
            Feature vector (1D array)
        """
        if channel_names is None:
            channel_names = ['voltage_A', 'voltage_B', 'voltage_C',
                           'current_A', 'current_B', 'current_C']

        features = {}

        # Organize data by channel
        data_dict = {name: window_data[:, i] for i, name in enumerate(channel_names)}

        # RMS features
        for name in channel_names:
            features[f'rms_{name}'] = self.calculate_rms(data_dict[name])

        # THD features
        for name in channel_names:
            features[f'thd_{name}'] = self.calculate_thd(data_dict[name])

        # Crest factors
        for name in channel_names:
            features[f'crest_{name}'] = self.calculate_crest_factor(data_dict[name])

        # Phase unbalance (for 3-phase systems)
        voltages = {k: v for k, v in data_dict.items() if 'voltage' in k}
        currents = {k: v for k, v in data_dict.items() if 'current' in k}

        if len(voltages) == 3 and len(currents) == 3:
            unbalance = self.calculate_phase_unbalance(
                {'voltage_A': voltages['voltage_A'],
                 'voltage_B': voltages['voltage_B'],
                 'voltage_C': voltages['voltage_C']},
                {'current_A': currents['current_A'],
                 'current_B': currents['current_B'],
                 'current_C': currents['current_C']}
            )
            features.update(unbalance)

        # Convert to array
        feature_vector = np.array(list(features.values()))
        return feature_vector

    def extract_features_batch(
        self,
        X: np.ndarray,
        channel_names: List[str] = None
    ) -> np.ndarray:
        """
        Extract features from a batch of windows.

        Args:
            X: Array of shape (n_samples, window_size, n_channels)
            channel_names: Optional list of channel names

        Returns:
            Feature matrix of shape (n_samples, n_features)
        """
        n_samples = X.shape[0]
        feature_list = []

        for i in range(n_samples):
            features = self.extract_features_from_window(X[i], channel_names)
            feature_list.append(features)

        return np.array(feature_list)

    def get_feature_names(self, n_channels: int = 6) -> List[str]:
        """
        Get list of feature names for interpretability.

        Args:
            n_channels: Number of input channels

        Returns:
            List of feature names
        """
        channel_names = ['voltage_A', 'voltage_B', 'voltage_C',
                        'current_A', 'current_B', 'current_C'][:n_channels]

        names = []

        # RMS features
        for name in channel_names:
            names.append(f'rms_{name}')

        # THD features
        for name in channel_names:
            names.append(f'thd_{name}')

        # Crest factors
        for name in channel_names:
            names.append(f'crest_{name}')

        # Unbalance features (only for 3-phase)
        if n_channels >= 6:
            names.extend(['voltage_unbalance', 'current_unbalance', 'zero_sequence_ratio'])

        return names


def extract_features_for_ml(X: np.ndarray, y: np.ndarray = None,
                            sampling_rate: int = 1000) -> Tuple[np.ndarray, ...]:
    """
    Convenience function to extract features for ML training.

    Args:
        X: Raw waveform data of shape (n_samples, window_size, 6)
        y: Optional labels
        sampling_rate: Sampling rate in Hz

    Returns:
        Tuple of (X_features, y if provided, feature_names)
    """
    extractor = PowerFeatureExtractor(sampling_rate=sampling_rate)

    feature_names = [
        # RMS (6)
        'rms_VA', 'rms_VB', 'rms_VC', 'rms_IA', 'rms_IB', 'rms_IC',
        # THD (6)
        'thd_VA', 'thd_VB', 'thd_VC', 'thd_IA', 'thd_IB', 'thd_IC',
        # Crest (6)
        'crest_VA', 'crest_VB', 'crest_VC', 'crest_IA', 'crest_IB', 'crest_IC',
        # Unbalance (3)
        'voltage_unbalance', 'current_unbalance', 'zero_sequence_ratio'
    ]

    X_features = extractor.extract_features_batch(X)

    if y is not None:
        return X_features, y, feature_names
    return X_features, feature_names
