"""
Power Grid Fault Simulator - Multi-Class Fault Classification
Generates 3-phase 50Hz sine waves with multi-class fault labels:
- Normal (0): Balanced 50Hz sine waves
- Single Line-to-Ground LG (1): One phase contacts ground (~70% of faults)
- Line-to-Line LL (2): Two phases touching without ground
- High-Impedance Fault HIF (3): Noisy arcing fault (tree branch, etc.)
"""

import numpy as np
import pandas as pd
import json
import random
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict, Any

# Fault type labels
FAULT_NORMAL = 0
FAULT_LG = 1      # Single Line-to-Ground
FAULT_LL = 2      # Line-to-Line
FAULT_HIF = 3     # High-Impedance Fault

FAULT_LABELS = {
    0: "Normal",
    1: "Line-to-Ground",
    2: "Line-to-Line",
    3: "High-Impedance"
}


class PowerFaultSimulator:
    """
    Simulates 3-phase power grid data with normal operation and multi-class fault conditions.
    Indian Standard: 50Hz, 230V RMS (phase-to-neutral)
    """

    def __init__(self, duration_seconds: float = 10.0, sampling_rate: int = 1000):
        """
        Initialize the simulator.

        Args:
            duration_seconds: Total simulation duration in seconds
            sampling_rate: Samples per second (Hz)
        """
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")
        if sampling_rate <= 0:
            raise ValueError("sampling_rate must be positive")

        self.duration = duration_seconds
        self.sampling_rate = sampling_rate
        self.frequency = 50.0  # Indian standard: 50Hz
        self.voltage_rms = 230.0  # Indian standard: 230V RMS (phase-to-neutral)
        self.current_rms = 10.0  # Example: 10A RMS current

        # Calculate peak values
        self.voltage_peak = self.voltage_rms * np.sqrt(2)
        self.current_peak = self.current_rms * np.sqrt(2)

        # 3-phase angles (120 degrees apart)
        self.phase_angles = [0, -2 * np.pi / 3, 2 * np.pi / 3]  # A, B, C

        # Generate time array
        self.num_samples = int(duration_seconds * sampling_rate)
        self.time = np.arange(self.num_samples) / self.sampling_rate

        # Generate timestamps
        self.start_time = datetime.now()
        self.timestamps = [self.start_time + timedelta(seconds=t) for t in self.time]

    def generate_normal_3phase(self) -> Dict[str, np.ndarray]:
        """
        Generate balanced 3-phase sine waves for voltage and current.

        Returns:
            Dictionary with keys: voltage_A, voltage_B, voltage_C, current_A, current_B, current_C
        """
        voltage_A = self.voltage_peak * np.sin(2 * np.pi * self.frequency * self.time + self.phase_angles[0])
        voltage_B = self.voltage_peak * np.sin(2 * np.pi * self.frequency * self.time + self.phase_angles[1])
        voltage_C = self.voltage_peak * np.sin(2 * np.pi * self.frequency * self.time + self.phase_angles[2])

        current_A = self.current_peak * np.sin(2 * np.pi * self.frequency * self.time + self.phase_angles[0])
        current_B = self.current_peak * np.sin(2 * np.pi * self.frequency * self.time + self.phase_angles[1])
        current_C = self.current_peak * np.sin(2 * np.pi * self.frequency * self.time + self.phase_angles[2])

        return {
            'voltage_A': voltage_A, 'voltage_B': voltage_B, 'voltage_C': voltage_C,
            'current_A': current_A, 'current_B': current_B, 'current_C': current_C,
            'fault_label': FAULT_NORMAL,
            'fault_type': 'Normal'
        }

    def generate_normal_waveform(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate normal sine waves for voltage and current (single phase, legacy).

        Returns:
            Tuple of (voltage_array, current_array)
        """
        voltage = self.voltage_peak * np.sin(2 * np.pi * self.frequency * self.time)
        current = self.current_peak * np.sin(2 * np.pi * self.frequency * self.time)
        return voltage, current

    def inject_lg_fault(self, voltages: Dict[str, np.ndarray], currents: Dict[str, np.ndarray],
                        fault_phase: str, start_idx: int, duration_samples: int,
                        ground_resistance: float = 0.1) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
        """
        Inject Single Line-to-Ground (LG) fault.
        One phase contacts the ground - most common fault (~70% of all faults).

        Args:
            voltages: Dict with voltage_A, voltage_B, voltage_C
            currents: Dict with current_A, current_B, current_C
            fault_phase: Phase with fault ('A', 'B', or 'C')
            start_idx: Starting index for fault
            duration_samples: Duration of fault in samples
            ground_resistance: Fault resistance to ground (ohms, normalized)

        Returns:
            Tuple of (modified_voltages, modified_currents)
        """
        v_fault = {k: v.copy() for k, v in voltages.items()}
        c_fault = {k: v.copy() for k, v in currents.items()}
        end_idx = min(start_idx + duration_samples, self.num_samples)

        # Faulted phase voltage drops significantly (to near zero through ground)
        v_key = f'voltage_{fault_phase}'
        c_key = f'current_{fault_phase}'

        # Voltage on faulted phase drops
        decay = np.linspace(1.0, ground_resistance, end_idx - start_idx)
        v_fault[v_key][start_idx:end_idx] *= decay

        # Current on faulted phase spikes (3-5x normal)
        current_spike = 4.0  # 4x current spike
        c_fault[c_key][start_idx:end_idx] *= current_spike

        # Ground current appears (sum of phase currents no longer zero)
        # Add zero-sequence current component
        if 'current_ground' in v_fault:
            c_fault['current_ground'] = c_fault[c_key][start_idx:end_idx] * 0.3

        return v_fault, c_fault

    def inject_ll_fault(self, voltages: Dict[str, np.ndarray], currents: Dict[str, np.ndarray],
                        fault_phases: Tuple[str, str], start_idx: int, duration_samples: int) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
        """
        Inject Line-to-Line (LL) fault.
        Two phases touching without involving the ground.

        Args:
            voltages: Dict with voltage_A, voltage_B, voltage_C
            currents: Dict with current_A, current_B, current_C
            fault_phases: Tuple of two phases with fault (e.g., ('A', 'B'))
            start_idx: Starting index for fault
            duration_samples: Duration of fault in samples

        Returns:
            Tuple of (modified_voltages, modified_currents)
        """
        v_fault = {k: v.copy() for k, v in voltages.items()}
        c_fault = {k: v.copy() for k, v in currents.items()}
        end_idx = min(start_idx + duration_samples, self.num_samples)

        phase1, phase2 = fault_phases

        # Voltages on faulted phases tend to equalize
        v1_key, v2_key = f'voltage_{phase1}', f'voltage_{phase2}'
        c1_key, c2_key = f'current_{phase1}', f'current_{phase2}'

        # Mix the voltages (they try to equalize)
        mixed_v = (v_fault[v1_key][start_idx:end_idx] + v_fault[v2_key][start_idx:end_idx]) / 2
        v_fault[v1_key][start_idx:end_idx] = mixed_v * 1.1  # Slight imbalance
        v_fault[v2_key][start_idx:end_idx] = mixed_v * 0.9

        # Currents spike in opposite directions on faulted phases
        c_fault[c1_key][start_idx:end_idx] *= 3.5
        c_fault[c2_key][start_idx:end_idx] *= -3.0  # Opposite direction

        # Third phase remains relatively normal
        third_phase = {'A', 'B', 'C'} - set(fault_phases)
        if third_phase:
            tp = third_phase.pop()
            # Slight disturbance on healthy phase
            c_fault[f'current_{tp}'][start_idx:end_idx] *= 1.2

        return v_fault, c_fault

    def inject_high_impedance_fault(self, voltages: Dict[str, np.ndarray], currents: Dict[str, np.ndarray],
                                     fault_phase: str, start_idx: int, duration_samples: int) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray]]:
        """
        Inject High-Impedance Fault (HIF).
        A "noisy" fault like a tree branch touching a wire - often bypasses traditional breakers.
        Characterized by harmonics and asymmetry.

        Args:
            voltages: Dict with voltage_A, voltage_B, voltage_C
            currents: Dict with current_A, current_B, current_C
            fault_phase: Phase with fault ('A', 'B', or 'C')
            start_idx: Starting index for fault
            duration_samples: Duration of fault in samples

        Returns:
            Tuple of (modified_voltages, modified_currents)
        """
        v_fault = {k: v.copy() for k, v in voltages.items()}
        c_fault = {k: v.copy() for k, v in currents.items()}
        end_idx = min(start_idx + duration_samples, self.num_samples)

        v_key = f'voltage_{fault_phase}'
        c_key = f'current_{fault_phase}'

        t_fault = self.time[start_idx:end_idx]

        # Voltage distortion - slight sag with harmonics
        h3 = 0.15 * self.voltage_peak * np.sin(2 * np.pi * 3 * self.frequency * t_fault)  # 3rd harmonic (150Hz)
        h5 = 0.08 * self.voltage_peak * np.sin(2 * np.pi * 5 * self.frequency * t_fault)  # 5th harmonic (250Hz)
        h7 = 0.05 * self.voltage_peak * np.sin(2 * np.pi * 7 * self.frequency * t_fault)  # 7th harmonic (350Hz)

        voltage_distortion = h3 + h5 + h7
        voltage_distortion += np.random.normal(0, 0.05 * self.voltage_peak, len(t_fault))

        v_fault[v_key][start_idx:end_idx] = v_fault[v_key][start_idx:end_idx] * 0.85 + voltage_distortion

        # Current becomes highly distorted with DC offset and harmonics
        # HIF characteristic: asymmetric current waveform
        dc_offset = 0.2 * self.current_peak * np.exp(-3 * (t_fault - t_fault[0]))

        # Arcing noise - random bursts
        arcing_noise = np.zeros(len(t_fault))
        arc_positions = np.random.choice(len(t_fault), size=int(len(t_fault) * 0.1), replace=False)
        arcing_noise[arc_positions] = np.random.normal(0, 0.3 * self.current_peak, len(arc_positions))

        current_hif = (
            c_fault[c_key][start_idx:end_idx] * 0.6 +  # Reduced fundamental
            dc_offset +
            0.25 * self.current_peak * np.sin(2 * np.pi * 3 * self.frequency * t_fault) +
            0.15 * self.current_peak * np.sin(2 * np.pi * 5 * self.frequency * t_fault) +
            arcing_noise
        )

        c_fault[c_key][start_idx:end_idx] = current_hif

        return v_fault, c_fault

    def inject_voltage_sag(self, voltage: np.ndarray, start_idx: int,
                           duration_samples: int) -> np.ndarray:
        """
        Inject a voltage sag (50% sudden drop) - legacy single-phase method.

        Args:
            voltage: Original voltage array
            start_idx: Starting index for the sag
            duration_samples: Duration of sag in samples

        Returns:
            Modified voltage array with sag
        """
        voltage_fault = voltage.copy()
        end_idx = min(start_idx + duration_samples, len(voltage))
        voltage_fault[start_idx:end_idx] *= 0.5  # 50% drop
        return voltage_fault

    def inject_high_impedance_fault(self, voltage: np.ndarray,
                                     current: np.ndarray,
                                     start_idx: int,
                                     duration_samples: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Inject a high impedance fault (noisy, irregular waveform).
        Simulates a branch touching a power line.

        Args:
            voltage: Original voltage array
            current: Original current array
            start_idx: Starting index for fault
            duration_samples: Duration of fault in samples

        Returns:
            Tuple of (modified_voltage, modified_current)
        """
        voltage_fault = voltage.copy()
        current_fault = current.copy()
        end_idx = min(start_idx + duration_samples, len(voltage))

        # Generate high frequency noise (arcing characteristics)
        noise_freq = 2000  # 2kHz arcing noise
        t_fault = self.time[start_idx:end_idx]

        # Voltage becomes noisy and irregular
        voltage_noise = 0.3 * self.voltage_peak * np.sin(2 * np.pi * noise_freq * t_fault)
        voltage_noise += np.random.normal(0, 0.1 * self.voltage_peak, len(t_fault))
        voltage_fault[start_idx:end_idx] = voltage[start_idx:end_idx] * 0.7 + voltage_noise

        # Current becomes erratic with high impedance
        current_noise = np.random.normal(0, 0.2 * self.current_peak, len(t_fault))
        current_fault[start_idx:end_idx] = current[start_idx:end_idx] * 0.5 + current_noise

        return voltage_fault, current_fault

    def inject_total_breakage(self, voltage: np.ndarray, current: np.ndarray,
                               start_idx: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        Inject total breakage (values go to zero).

        Args:
            voltage: Original voltage array
            current: Original current array
            start_idx: Starting index for breakage

        Returns:
            Tuple of (modified_voltage, modified_current)
        """
        voltage_fault = voltage.copy()
        current_fault = current.copy()

        voltage_fault[start_idx:] = 0.0
        current_fault[start_idx:] = 0.0

        return voltage_fault, current_fault

    def generate_stream_cycle(
        self,
        fault_probability: float = 0.3
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, Optional[Dict[str, Any]]]:
        """
        Generate a single streaming cycle with at most one fault (legacy single-phase).

        Returns:
            Tuple of (time_array, voltage_array, current_array, fault_info)
        """
        voltage, current = self.generate_normal_waveform()
        fault_info = None

        if random.random() < fault_probability:
            fault_type = random.choice(['sag', 'high_impedance', 'breakage'])
            start_idx = random.randint(
                int(0.2 * self.num_samples),
                int(0.6 * self.num_samples)
            )

            fault_info = {
                'type': fault_type,
                'start_sample': start_idx,
                'start_time_offset_seconds': round(self.time[start_idx], 6)
            }

            if fault_type == 'sag':
                duration_samples = int(0.3 * self.num_samples)
                voltage = self.inject_voltage_sag(voltage, start_idx, duration_samples)
                fault_info['description'] = '50% voltage sag'
                fault_info['duration_samples'] = duration_samples
                fault_info['duration_seconds'] = round(duration_samples / self.sampling_rate, 6)

            elif fault_type == 'high_impedance':
                duration_samples = int(0.5 * self.num_samples)
                voltage, current = self.inject_high_impedance_fault(
                    voltage, current, start_idx, duration_samples
                )
                fault_info['description'] = 'High impedance fault (noisy/arcing)'
                fault_info['duration_samples'] = duration_samples
                fault_info['duration_seconds'] = round(duration_samples / self.sampling_rate, 6)

            elif fault_type == 'breakage':
                voltage, current = self.inject_total_breakage(voltage, current, start_idx)
                fault_info['description'] = 'Total line breakage'
                fault_info['duration_samples'] = self.num_samples - start_idx
                fault_info['duration_seconds'] = round(
                    (self.num_samples - start_idx) / self.sampling_rate, 6
                )

        return self.time.copy(), voltage, current, fault_info

    def generate_3phase_cycle(
        self,
        fault_probability: float = 0.4,
        # LG faults are ~70% of all faults in real grids
        lg_fault_weight: float = 0.70,
        ll_fault_weight: float = 0.15,
        hif_fault_weight: float = 0.15
    ) -> Tuple[np.ndarray, Dict[str, np.ndarray], Optional[Dict[str, Any]]]:
        """
        Generate a single 3-phase streaming cycle with multi-class fault injection.

        Args:
            fault_probability: Probability of any fault occurring (0-1)
            lg_fault_weight: Weight for LG faults (default 70% - most common)
            ll_fault_weight: Weight for LL faults (default 15%)
            hif_fault_weight: Weight for HIF faults (default 15%)

        Returns:
            Tuple of (time_array, phase_data_dict, fault_info)
            phase_data_dict contains: voltage_A/B/C, current_A/B/C, fault_label, fault_type
        """
        # Start with normal balanced 3-phase
        phase_data = self.generate_normal_3phase()
        fault_info = None

        if random.random() < fault_probability:
            # Choose fault type with weighted probabilities
            fault_choice = random.random()
            total_weight = lg_fault_weight + ll_fault_weight + hif_fault_weight

            if fault_choice < lg_fault_weight / total_weight:
                fault_type = 'LG'
                fault_label = FAULT_LG
            elif fault_choice < (lg_fault_weight + ll_fault_weight) / total_weight:
                fault_type = 'LL'
                fault_label = FAULT_LL
            else:
                fault_type = 'HIF'
                fault_label = FAULT_HIF

            # Random start time (avoid edges for clean analysis)
            start_idx = random.randint(
                int(0.15 * self.num_samples),
                int(0.50 * self.num_samples)
            )
            duration_samples = random.randint(
                int(0.20 * self.num_samples),
                int(0.50 * self.num_samples)
            )

            fault_info = {
                'type': fault_type,
                'fault_label': fault_label,
                'fault_type_name': FAULT_LABELS[fault_label],
                'start_sample': start_idx,
                'start_time_offset_seconds': round(self.time[start_idx], 6),
                'duration_samples': duration_samples,
                'duration_seconds': round(duration_samples / self.sampling_rate, 6)
            }

            # Extract voltage and current dicts for fault injection
            voltages = {
                'voltage_A': phase_data['voltage_A'],
                'voltage_B': phase_data['voltage_B'],
                'voltage_C': phase_data['voltage_C']
            }
            currents = {
                'current_A': phase_data['current_A'],
                'current_B': phase_data['current_B'],
                'current_C': phase_data['current_C']
            }

            if fault_type == 'LG':
                # Single Line-to-Ground: random phase
                fault_phase = random.choice(['A', 'B', 'C'])
                fault_info['faulted_phase'] = fault_phase
                fault_info['description'] = f'Single Line-to-Ground fault on phase {fault_phase}'
                voltages, currents = self.inject_lg_fault(
                    voltages, currents, fault_phase, start_idx, duration_samples
                )

            elif fault_type == 'LL':
                # Line-to-Line: random pair of phases
                fault_phases = random.choice([('A', 'B'), ('B', 'C'), ('A', 'C')])
                fault_info['faulted_phases'] = fault_phases
                fault_info['description'] = f'Line-to-Line fault between phases {fault_phases[0]} and {fault_phases[1]}'
                voltages, currents = self.inject_ll_fault(
                    voltages, currents, fault_phases, start_idx, duration_samples
                )

            elif fault_type == 'HIF':
                # High-Impedance Fault: random phase
                fault_phase = random.choice(['A', 'B', 'C'])
                fault_info['faulted_phase'] = fault_phase
                fault_info['description'] = f'High-Impedance Fault on phase {fault_phase} (arcing/noisy)'
                voltages, currents = self.inject_high_impedance_fault(
                    voltages, currents, fault_phase, start_idx, duration_samples
                )

            # Update phase_data with faulted values
            phase_data['voltage_A'] = voltages['voltage_A']
            phase_data['voltage_B'] = voltages['voltage_B']
            phase_data['voltage_C'] = voltages['voltage_C']
            phase_data['current_A'] = currents['current_A']
            phase_data['current_B'] = currents['current_B']
            phase_data['current_C'] = currents['current_C']
            phase_data['fault_label'] = fault_label
            phase_data['fault_type'] = fault_type

        return self.time.copy(), phase_data, fault_info

    def generate_fault_data(self, fault_probability: float = 0.3,
                          max_faults: int = 3) -> Tuple[np.ndarray, np.ndarray, List[dict]]:
        """
        Generate data with random fault injection.

        Args:
            fault_probability: Probability of a fault occurring (0-1)
            max_faults: Maximum number of faults to inject

        Returns:
            Tuple of (voltage_array, current_array, fault_log)
        """
        voltage, current = self.generate_normal_waveform()
        fault_log = []

        # Randomly decide to inject faults
        if random.random() < fault_probability:
            num_faults = random.randint(1, max_faults)

            for i in range(num_faults):
                # Random fault type
                fault_type = random.choice(['sag', 'high_impedance', 'breakage'])

                # Random start time (avoid edges)
                start_idx = random.randint(int(0.1 * self.num_samples),
                                          int(0.7 * self.num_samples))

                fault_info = {
                    'fault_number': i + 1,
                    'type': fault_type,
                    'start_time': self.timestamps[start_idx].isoformat(),
                    'start_sample': start_idx
                }

                if fault_type == 'sag':
                    duration = random.uniform(0.1, 0.5)  # 100-500ms sag
                    duration_samples = int(duration * self.sampling_rate)
                    voltage = self.inject_voltage_sag(voltage, start_idx, duration_samples)
                    fault_info['duration_seconds'] = duration
                    fault_info['description'] = '50% voltage sag'

                elif fault_type == 'high_impedance':
                    duration = random.uniform(0.2, 1.0)  # 200ms-1s fault
                    duration_samples = int(duration * self.sampling_rate)
                    voltage, current = self.inject_high_impedance_fault(
                        voltage, current, start_idx, duration_samples
                    )
                    fault_info['duration_seconds'] = duration
                    fault_info['description'] = 'High impedance fault (noisy/arcing)'

                elif fault_type == 'breakage':
                    voltage, current = self.inject_total_breakage(
                        voltage, current, start_idx
                    )
                    fault_info['duration_seconds'] = self.duration - (start_idx / self.sampling_rate)
                    fault_info['description'] = 'Total line breakage'

                fault_log.append(fault_info)

        return voltage, current, fault_log

    def generate_labeled_dataset(
        self,
        samples_per_class: int = 500,
        window_size: int = 100,
        noise_level: float = 0.02
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate a balanced labeled dataset for ML training.

        Args:
            samples_per_class: Number of samples per fault class
            window_size: Number of samples per instance (for sliding window)
            noise_level: Gaussian noise standard deviation (normalized)

        Returns:
            Tuple of (X, y) where:
                X: Feature array of shape (n_samples, window_size, 6)
                   6 channels: V_A, V_B, V_C, I_A, I_B, I_C
                y: Labels array of shape (n_samples,)
        """
        X_list = []
        y_list = []

        # Class distribution: Normal, LG, LL, HIF
        # LG faults weighted to ~70% of fault samples as per real grid statistics
        classes = [FAULT_NORMAL, FAULT_LG, FAULT_LL, FAULT_HIF]

        for class_label in classes:
            for _ in range(samples_per_class):
                # Generate appropriate cycle
                if class_label == FAULT_NORMAL:
                    # Normal: no fault
                    _, phase_data, _ = self.generate_3phase_cycle(fault_probability=0.0)
                else:
                    # Fault classes: force specific fault type
                    if class_label == FAULT_LG:
                        _, phase_data, _ = self.generate_3phase_cycle(
                            fault_probability=1.0,
                            lg_fault_weight=1.0,
                            ll_fault_weight=0.0,
                            hif_fault_weight=0.0
                        )
                    elif class_label == FAULT_LL:
                        _, phase_data, _ = self.generate_3phase_cycle(
                            fault_probability=1.0,
                            lg_fault_weight=0.0,
                            ll_fault_weight=1.0,
                            hif_fault_weight=0.0
                        )
                    else:  # HIF
                        _, phase_data, _ = self.generate_3phase_cycle(
                            fault_probability=1.0,
                            lg_fault_weight=0.0,
                            ll_fault_weight=0.0,
                            hif_fault_weight=1.0
                        )

                # Extract window of data
                start_idx = random.randint(0, max(0, self.num_samples - window_size))
                end_idx = start_idx + window_size

                # Build 6-channel sample
                sample = np.zeros((window_size, 6))
                sample[:, 0] = phase_data['voltage_A'][start_idx:end_idx]
                sample[:, 1] = phase_data['voltage_B'][start_idx:end_idx]
                sample[:, 2] = phase_data['voltage_C'][start_idx:end_idx]
                sample[:, 3] = phase_data['current_A'][start_idx:end_idx]
                sample[:, 4] = phase_data['current_B'][start_idx:end_idx]
                sample[:, 5] = phase_data['current_C'][start_idx:end_idx]

                # Add small measurement noise
                sample += np.random.normal(0, noise_level * self.voltage_peak, sample.shape)

                X_list.append(sample)
                y_list.append(class_label)

        X = np.array(X_list)
        y = np.array(y_list)

        # Shuffle dataset
        indices = np.random.permutation(len(X))
        X = X[indices]
        y = y[indices]

        print(f"Generated labeled dataset: X shape = {X.shape}, y shape = {y.shape}")
        print(f"Class distribution: Normal={np.sum(y==0)}, LG={np.sum(y==1)}, LL={np.sum(y==2)}, HIF={np.sum(y==3)}")

        return X, y

    def export_to_csv(self, voltage: np.ndarray, current: np.ndarray,
                      filename: str = 'power_data.csv'):
        """
        Export data to CSV file.

        Args:
            voltage: Voltage array
            current: Current array
            filename: Output filename
        """
        df = pd.DataFrame({
            'timestamp': [t.isoformat() for t in self.timestamps],
            'time_seconds': self.time,
            'voltage': np.round(voltage, 4),
            'current': np.round(current, 4),
            'power': np.round(voltage * current, 4)
        })
        df.to_csv(filename, index=False)
        print(f"Data exported to CSV: {filename}")
        return df

    def export_to_json(self, voltage: np.ndarray, current: np.ndarray,
                       fault_log: List[dict],
                       filename: str = 'power_data.json'):
        """
        Export data to JSON file.

        Args:
            voltage: Voltage array
            current: Current array
            fault_log: List of fault information
            filename: Output filename
        """
        data = {
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'frequency_hz': self.frequency,
                'sampling_rate_hz': self.sampling_rate,
                'duration_seconds': self.duration,
                'nominal_voltage_rms': self.voltage_rms,
                'nominal_current_rms': self.current_rms
            },
            'faults': fault_log,
            'readings': [
                {
                    'timestamp': self.timestamps[i].isoformat(),
                    'time_seconds': round(self.time[i], 6),
                    'voltage': round(voltage[i], 4),
                    'current': round(current[i], 4),
                    'power': round(voltage[i] * current[i], 4)
                }
                for i in range(len(self.time))
            ]
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Data exported to JSON: {filename}")
        return data

    def generate_summary(self, voltage: np.ndarray, current: np.ndarray,
                         fault_log: List[dict]) -> dict:
        """
        Generate a summary of the simulation.

        Args:
            voltage: Voltage array
            current: Current array
            fault_log: List of fault information

        Returns:
            Summary dictionary
        """
        summary = {
            'simulation_duration_seconds': self.duration,
            'sampling_rate_hz': self.sampling_rate,
            'total_samples': self.num_samples,
            'frequency_hz': self.frequency,
            'nominal_voltage_rms_v': self.voltage_rms,
            'nominal_current_rms_a': self.current_rms,
            'actual_voltage_rms_v': round(np.sqrt(np.mean(voltage**2)), 2),
            'actual_current_rms_a': round(np.sqrt(np.mean(current**2)), 2),
            'number_of_faults': len(fault_log),
            'faults': fault_log
        }
        return summary


def main():
    """Main execution function - demonstrates multi-class 3-phase fault simulation."""
    print("=" * 60)
    print("Power Grid Fault Simulator - Multi-Class Classification")
    print("Indian Standard: 50Hz, 230V RMS (3-phase)")
    print("Fault Types: Normal(0), LG(1), LL(2), HIF(3)")
    print("=" * 60)

    # Initialize simulator (2 seconds, 1000 Hz sampling for ML dataset)
    simulator = PowerFaultSimulator(duration_seconds=2.0, sampling_rate=1000)

    # Demo 1: Generate individual 3-phase cycles with different fault types
    print("\n" + "=" * 60)
    print("DEMO 1: 3-Phase Cycle Generation")
    print("=" * 60)

    for fault_name, fault_label in [("Normal", 0), ("LG (Line-to-Ground)", 1),
                                     ("LL (Line-to-Line)", 2), ("HIF (High-Impedance)", 3)]:
        if fault_label == 0:
            _, phase_data, _ = simulator.generate_3phase_cycle(fault_probability=0.0)
        else:
            _, phase_data, fault_info = simulator.generate_3phase_cycle(
                fault_probability=1.0,
                lg_fault_weight=1.0 if fault_label == 1 else 0.0,
                ll_fault_weight=1.0 if fault_label == 2 else 0.0,
                hif_fault_weight=1.0 if fault_label == 3 else 0.0
            )
        print(f"\n{fault_name}:")
        print(f"  Voltage RMS A: {np.sqrt(np.mean(phase_data['voltage_A']**2)):.2f} V")
        print(f"  Voltage RMS B: {np.sqrt(np.mean(phase_data['voltage_B']**2)):.2f} V")
        print(f"  Voltage RMS C: {np.sqrt(np.mean(phase_data['voltage_C']**2)):.2f} V")
        print(f"  Current RMS A: {np.sqrt(np.mean(phase_data['current_A']**2)):.2f} A")

    # Demo 2: Generate labeled ML dataset
    print("\n" + "=" * 60)
    print("DEMO 2: Generate Labeled ML Dataset")
    print("=" * 60)

    X, y = simulator.generate_labeled_dataset(
        samples_per_class=100,  # 100 samples per class = 400 total
        window_size=100,         # 100 samples per window (100ms at 1kHz)
        noise_level=0.02
    )

    print(f"\nDataset ready for ML training:")
    print(f"  X shape: {X.shape} (samples, window_size, 6 channels)")
    print(f"  y shape: {y.shape}")
    print(f"  Classes: 0=Normal, 1=LG, 2=LL, 3=HIF")

    # Save dataset for training
    np.save('ml_dataset_X.npy', X)
    np.save('ml_labels_y.npy', y)
    print(f"\nDataset saved to: ml_dataset_X.npy, ml_labels_y.npy")

    print(f"\n{'='*60}")
    print("Simulation complete!")
    print(f"{'='*60}")

    return simulator, X, y


if __name__ == "__main__":
    simulator, X, y = main()


if __name__ == "__main__":
    simulator, voltage, current, fault_log = main()
