"""
GridSeva - Smart Grid Anomaly Detection API
Phase 3: Multi-Class Fault Classification with ML

This module provides a FastAPI application that:
- Streams 3-phase power grid data in a background task
- Provides real-time fault classification using trained ML model
- Returns fault type, confidence, and location estimates
- Supports sliding window inference (100ms window)
"""

import asyncio
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Union
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from power_fault_simulator import PowerFaultSimulator, FAULT_LABELS
from inference_service import FaultInferenceService
from field_agent import FieldAgent, GridConsultant
from database import db_manager
import uuid

# ============== Data Models ==============

class PowerReading(BaseModel):
    """Model for a single power reading."""
    timestamp: str
    time_seconds: float
    voltage_A: float = 0.0
    voltage_B: float = 0.0
    voltage_C: float = 0.0
    current_A: float = 0.0
    current_B: float = 0.0
    current_C: float = 0.0
    is_faulty: bool = False
    fault_type: Optional[str] = None


class PowerReadingSinglePhase(BaseModel):
    """Model for single-phase power reading (legacy compatibility)."""
    timestamp: str
    time_seconds: float
    voltage: float
    current: float
    power: float
    is_faulty: bool = False
    fault_type: Optional[str] = None


class ClassifyRequest(BaseModel):
    """Request for fault classification."""
    voltages: Dict[str, List[float]] = None  # voltage_A, voltage_B, voltage_C
    currents: Dict[str, List[float]] = None  # current_A, current_B, current_C
    window_size_ms: int = 100


class ClassifyResponse(BaseModel):
    """Response from fault classification."""
    status: str  # "NORMAL" or "FAULT"
    type: str  # Fault type name
    fault_label: int  # 0=Normal, 1=LG, 2=LL, 3=HIF
    confidence: float  # 0-1 confidence score
    all_probabilities: Dict[str, float]  # All class probabilities
    location_est: str  # Estimated location
    timestamp: str
    window_size_ms: int
    fault_id: Optional[str] = None  # Unique ID for linking feedback


class StatusResponse(BaseModel):
    """Model for system status response."""
    status: str
    uptime_seconds: float
    total_readings: int
    current_cycle: int
    latest_reading: Optional[PowerReading] = None
    faults_detected_in_cycle: int = 0
    ml_model_loaded: bool = False


class DataSummaryResponse(BaseModel):
    """Model for data summary."""
    total_readings: int
    current_cycle: int
    voltage_stats: Dict[str, float]
    current_stats: Dict[str, float]
    recent_faults: List[Dict[str, Any]]


class FaultFeedback(BaseModel):
    """Model for technician field feedback."""
    fault_id: str
    confirmed_type: str  # e.g., "Confirmed: LG Fault", "False Positive", "Tree Branch Found"
    is_correct: bool
    technician_id: str
    comments: Optional[str] = None
    actual_location: Optional[str] = None


class UserQuestion(BaseModel):
    """Model for user natural language questions."""
    question: str

# ============== Global State ==============

class DataStore:
    """Thread-safe data store for 3-phase power readings."""

    def __init__(self, max_readings: int = 10000):
        self.readings: List[PowerReading] = []
        self.max_readings = max_readings
        self.cycle_count = 0
        self.start_time: Optional[datetime] = None
        self.faults_in_current_cycle = 0
        self.total_faults = 0
        self._lock = asyncio.Lock()
        # Sliding window for ML inference
        self.window_buffer: List[Dict[str, float]] = []
        self.last_classification: Optional[Dict[str, Any]] = None

    async def add_reading(self, reading: PowerReading):
        """Add a 3-phase reading to the store."""
        async with self._lock:
            self.readings.append(reading)
            if len(self.readings) > self.max_readings:
                self.readings.pop(0)
            if reading.is_faulty:
                self.faults_in_current_cycle += 1
                self.total_faults += 1

            # Add to window buffer for ML inference
            self.window_buffer.append({
                'voltage_A': reading.voltage_A,
                'voltage_B': reading.voltage_B,
                'voltage_C': reading.voltage_C,
                'current_A': reading.current_A,
                'current_B': reading.current_B,
                'current_C': reading.current_C
            })
            # Keep buffer at ~100ms (100 samples at 1kHz)
            if len(self.window_buffer) > 100:
                self.window_buffer.pop(0)

    async def add_reading_single_phase(self, reading: PowerReadingSinglePhase):
        """Add a single-phase reading (legacy compatibility)."""
        async with self._lock:
            self.readings.append(reading)
            if len(self.readings) > self.max_readings:
                self.readings.pop(0)
            if reading.is_faulty:
                self.faults_in_current_cycle += 1
                self.total_faults += 1

    async def start_new_cycle(self):
        """Reset cycle counters."""
        async with self._lock:
            self.cycle_count += 1
            self.faults_in_current_cycle = 0
            if self.start_time is None:
                self.start_time = datetime.now()

    async def get_recent_readings(self, count: int = 100) -> List[PowerReading]:
        """Get recent readings."""
        async with self._lock:
            return list(self.readings[-count:]) if self.readings else []

    async def get_statistics(self) -> Dict[str, Any]:
        """Calculate statistics from stored 3-phase readings."""
        async with self._lock:
            if not self.readings:
                return {
                    'voltage': {'mean': 0, 'std': 0, 'min': 0, 'max': 0},
                    'current': {'mean': 0, 'std': 0, 'min': 0, 'max': 0}
                }

            # Handle both 3-phase and single-phase readings
            voltages_a = [getattr(r, 'voltage_A', getattr(r, 'voltage', 0)) for r in self.readings]
            currents_a = [getattr(r, 'current_A', getattr(r, 'current', 0)) for r in self.readings]

            return {
                'voltage_A': {
                    'mean': round(float(np.mean(voltages_a)), 2),
                    'std': round(float(np.std(voltages_a)), 2),
                    'min': round(min(voltages_a), 2),
                    'max': round(max(voltages_a), 2)
                },
                'current_A': {
                    'mean': round(float(np.mean(currents_a)), 2),
                    'std': round(float(np.std(currents_a)), 2),
                    'min': round(min(currents_a), 2),
                    'max': round(max(currents_a), 2)
                }
            }

    async def get_window_buffer(self) -> List[Dict[str, float]]:
        """Get current sliding window buffer for ML inference."""
        async with self._lock:
            return list(self.window_buffer)

    async def set_classification(self, classification: Dict[str, Any]):
        """Store the latest classification result."""
        async with self._lock:
            self.last_classification = classification

    async def get_last_classification(self) -> Optional[Dict[str, Any]]:
        """Get the latest classification result."""
        async with self._lock:
            return self.last_classification

    async def get_recent_faults(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent faults."""
        async with self._lock:
            faults = []
            for r in reversed(self.readings):
                if r.is_faulty and len(faults) < count:
                    faults.append({
                        'timestamp': r.timestamp,
                        'fault_type': r.fault_type,
                        'voltage': r.voltage,
                        'current': r.current
                    })
            return faults

    async def get_status_snapshot(self) -> Dict[str, Any]:
        """Get a consistent snapshot for the status endpoint."""
        async with self._lock:
            uptime = 0.0
            if self.start_time is not None:
                uptime = (datetime.now() - self.start_time).total_seconds()

            return {
                'uptime_seconds': round(uptime, 2),
                'total_readings': len(self.readings),
                'current_cycle': self.cycle_count,
                'latest_reading': self.readings[-1] if self.readings else None,
                'faults_detected_in_cycle': self.faults_in_current_cycle
            }


# Global data store instance
data_store = DataStore(max_readings=50000)
simulator = PowerFaultSimulator(duration_seconds=2.0, sampling_rate=1000)  # 3-phase capable

# ML Inference Service (loaded on startup)
ml_service: Optional[FaultInferenceService] = None


# ============== Background Task ==============

async def data_streaming_task():
    """
    Background task that continuously generates 3-phase power data.
    Runs in an infinite loop, simulating real-time sensor readings.
    Includes real-time ML classification on sliding window.
    """
    global ml_service
    print("[Background Task] Starting 3-phase data streaming...")

    while True:
        cycle_start = datetime.now()
        await data_store.start_new_cycle()

        # Generate one 3-phase cycle with potential fault
        time_arr, phase_data, fault_info = simulator.generate_3phase_cycle(
            fault_probability=0.3,  # 30% chance of fault
            lg_fault_weight=0.70,   # 70% LG faults
            ll_fault_weight=0.15,   # 15% LL faults
            hif_fault_weight=0.15   # 15% HIF faults
        )

        # Stream each reading with timestamp
        for i in range(len(time_arr)):
            timestamp = cycle_start + timedelta(seconds=time_arr[i])
            is_faulty = bool(fault_info) and i >= fault_info.get('start_sample', 0)

            reading = PowerReading(
                timestamp=timestamp.isoformat(),
                time_seconds=time_arr[i],
                voltage_A=round(phase_data['voltage_A'][i], 4),
                voltage_B=round(phase_data['voltage_B'][i], 4),
                voltage_C=round(phase_data['voltage_C'][i], 4),
                current_A=round(phase_data['current_A'][i], 4),
                current_B=round(phase_data['current_B'][i], 4),
                current_C=round(phase_data['current_C'][i], 4),
                is_faulty=is_faulty,
                fault_type=fault_info.get('type') if is_faulty and fault_info else None
            )

            await data_store.add_reading(reading)

            # Run ML inference if service is loaded
            if ml_service is not None and ml_service.model is not None:
                ml_result = ml_service.add_sample(
                    voltages={
                        'voltage_A': phase_data['voltage_A'][i],
                        'voltage_B': phase_data['voltage_B'][i],
                        'voltage_C': phase_data['voltage_C'][i]
                    },
                    currents={
                        'current_A': phase_data['current_A'][i],
                        'current_B': phase_data['current_B'][i],
                        'current_C': phase_data['current_C'][i]
                    }
                )
                if ml_result:
                    await data_store.set_classification(ml_result)

            # Small delay to simulate real-time streaming
            await asyncio.sleep(1 / simulator.sampling_rate)

        if fault_info:
            print(f"[Background Task] Cycle {data_store.cycle_count}: "
                  f"Fault={fault_info['type']}, ML={data_store.last_classification['status'] if data_store.last_classification else 'N/A'}")
        else:
            print(f"[Background Task] Completed cycle {data_store.cycle_count} (Normal)")


# ============== FastAPI Application ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - start background task and load ML model on startup."""
    global ml_service

    # Startup
    print("[Lifespan] Starting up GridSeva API...")

    # Load ML inference service
    print("[Lifespan] Loading ML fault classification model...")
    ml_service = FaultInferenceService(model_path='fault_classifier.pkl')
    model_loaded = ml_service.load_model()
    if model_loaded:
        print("[Lifespan] ML model loaded successfully!")
    else:
        print("[Lifespan] Warning: ML model not loaded. Run train_model.py first.")

    # Start background data streaming
    task = asyncio.create_task(data_streaming_task())

    yield

    # Shutdown
    print("[Lifespan] Shutting down...")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="GridSeva API",
    description="Smart Grid Anomaly Detection System - Phase 4: Autonomous Operations",
    version="4.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the dashboard frontend."""
    with open("static/index.html", "r") as f:
        return f.read()


@app.get("/api/info")
async def get_api_info():
    """API backend information."""
    global ml_service
    model_loaded = ml_service is not None and ml_service.model is not None

    return {
        "message": "Welcome to GridSeva - Smart Grid Multi-Class Fault Classification API",
        "version": "3.0.0",
        "ml_model_loaded": model_loaded,
        "fault_classes": FAULT_LABELS,
        "endpoints": {
            "/": "API information",
            "/status": "System status and current readings",
            "/classify": "POST - Classify fault from 3-phase data",
            "/classify/latest": "Get latest ML classification result",
            "/agent/summary": "Get AI Field Agent's human-friendly summary",
            "/data/latest": "Get latest power readings",
            "/data/summary": "Get data statistics summary",
            "/health": "Health check"
        }
    }


@app.get("/status", response_model=StatusResponse)
async def get_status():
    """
    Get current system status including:
    - Uptime
    - Total readings collected
    - Current cycle number
    - Latest reading
    - Faults detected
    - ML model status
    """
    global ml_service
    snapshot = await data_store.get_status_snapshot()
    model_loaded = ml_service is not None and ml_service.model is not None

    return StatusResponse(
        status="operational",
        uptime_seconds=snapshot['uptime_seconds'],
        total_readings=snapshot['total_readings'],
        current_cycle=snapshot['current_cycle'],
        latest_reading=snapshot['latest_reading'],
        faults_detected_in_cycle=snapshot['faults_detected_in_cycle'],
        ml_model_loaded=model_loaded
    )


@app.post("/classify", response_model=ClassifyResponse)
async def classify_fault(request: ClassifyRequest = None):
    """
    Classify fault type from 3-phase voltage/current data.

    Accepts sliding window data and returns:
    - status: NORMAL or FAULT
    - type: Fault type (Normal, Line-to-Ground, Line-to-Line, High-Impedance)
    - confidence: ML confidence score (0-1)
    - location_est: Estimated fault location

    Can be called with:
    - Full window data in request body
    - Or uses current sliding window from background stream if no data provided
    """
    global ml_service

    if ml_service is None or ml_service.model is None:
        return ClassifyResponse(
            status="ERROR",
            type="Model not loaded - run train_model.py first",
            fault_label=-1,
            confidence=0.0,
            all_probabilities={},
            location_est="N/A",
            timestamp=datetime.now().isoformat(),
            window_size_ms=100
        )

    # If request data provided, use it for classification
    if request and request.voltages and request.currents:
        # Build window from request data
        n_samples = len(request.voltages.get('voltage_A', []))
        if n_samples < 50:
            return {
                "status": "ERROR",
                "type": "Insufficient data",
                "fault_label": -1,
                "confidence": 0.0,
                "all_probabilities": {},
                "location_est": "N/A",
                "timestamp": datetime.now().isoformat(),
                "window_size_ms": 100
            }

        # Create window array
        window_data = np.zeros((n_samples, 6))
        window_data[:, 0] = request.voltages.get('voltage_A', [0] * n_samples)
        window_data[:, 1] = request.voltages.get('voltage_B', [0] * n_samples)
        window_data[:, 2] = request.voltages.get('voltage_C', [0] * n_samples)
        window_data[:, 3] = request.currents.get('current_A', [0] * n_samples)
        window_data[:, 4] = request.currents.get('current_B', [0] * n_samples)
        window_data[:, 5] = request.currents.get('current_C', [0] * n_samples)

        # Batch predict
        results = ml_service.batch_predict(window_data[np.newaxis, :min(100, n_samples), :])
        result = results[0] if results else {}

        return ClassifyResponse(
            status=result.get('status', 'UNKNOWN'),
            type=result.get('type', 'Unknown'),
            fault_label=result.get('fault_label', -1),
            confidence=result.get('confidence', 0.0),
            all_probabilities=result.get('all_probabilities', {}),
            location_est=result.get('location_est', 'N/A'),
            timestamp=datetime.now().isoformat(),
            window_size_ms=request.window_size_ms,
            fault_id=str(uuid.uuid4()) if result.get('status') == "FAULT" else None
        )

    # Otherwise, use current sliding window from background stream
    last_classification = await data_store.get_last_classification()

    if last_classification:
        return ClassifyResponse(**last_classification)

    return {
        "status": "WAITING",
        "type": "Buffering",
        "fault_label": -1,
        "confidence": 0.0,
        "all_probabilities": {},
        "location_est": "N/A",
        "timestamp": datetime.now().isoformat(),
        "window_size_ms": 100
    }


@app.get("/agent/summary")
async def get_agent_summary():
    """
    Get a human-friendly summary of the latest fault diagnostic using the Field Agent.
    Translates raw ML data into actionable instructions for technicians.
    """
    last_classification = await data_store.get_last_classification()

    if not last_classification:
        return {
            "status": "WAITING",
            "summary": "System is buffering data. No diagnostics available yet."
        }

    # Use the Field Agent to generate the summary
    summary = FieldAgent.get_summary(last_classification)

    return {
        "status": last_classification["status"],
        "type": last_classification["type"],
        "summary": summary,
        "timestamp": last_classification["timestamp"],
        "location_est": last_classification["location_est"],
        "fault_id": last_classification.get("fault_id")
    }


@app.post("/agent/feedback")
async def submit_feedback(feedback: FaultFeedback):
    """
    Submit technician feedback from the field.
    Stores the result in MongoDB to create a Ground Truth dataset.
    """
    try:
        # Prepare the document for MongoDB
        feedback_doc = feedback.dict()
        
        # Save to database
        db_id = await db_manager.save_feedback(feedback_doc)
        
        print(f"[Feedback] Received feedback for fault {feedback.fault_id}. Saved to DB with ID: {db_id}")
        
        return {
            "status": "success",
            "message": "Feedback recorded. Thank you for contributing to Ground Truth data.",
            "db_id": db_id
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to save feedback: {str(e)}"
        }


@app.get("/agent/ground-truth")
async def get_ground_truth_stats(limit: int = 20):
    """Retrieve recent ground truth records."""
    try:
        data = await db_manager.get_ground_truth(limit)
        return {
            "count": len(data),
            "records": data
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/agent/ask")
async def ask_agent(query: UserQuestion):
    """
    Ask the Grid Consultant a natural language question about system health or status.
    Uses an agentic workflow with tool usage to retrieve real-time data.
    """
    try:
        response = GridConsultant.ask(query.question)
        return {
            "question": query.question,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Query Agent failed: {str(e)}"
        }


@app.get("/classify/latest")
async def get_latest_classification():
    """Get the latest ML classification result from the streaming data."""
    last_classification = await data_store.get_last_classification()

    if last_classification:
        return last_classification

    return {
        "status": "WAITING",
        "type": "Buffering",
        "message": "No classification yet. Waiting for sliding window to fill."
    }


@app.get("/data/latest")
async def get_latest_readings(count: int = 50):
    """
    Get the latest power readings.

    Args:
        count: Number of readings to return (default: 50, max: 1000)
    """
    count = min(max(count, 1), 1000)
    readings = await data_store.get_recent_readings(count)
    return {
        "count": len(readings),
        "readings": readings
    }


@app.get("/data/summary", response_model=DataSummaryResponse)
async def get_data_summary():
    """
    Get a summary of collected data including statistics.
    """
    stats = await data_store.get_statistics()
    recent_faults = await data_store.get_recent_faults(10)
    status_snapshot = await data_store.get_status_snapshot()

    return DataSummaryResponse(
        total_readings=status_snapshot['total_readings'],
        current_cycle=status_snapshot['current_cycle'],
        voltage_stats=stats['voltage'],
        current_stats=stats['current'],
        recent_faults=recent_faults
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    status_snapshot = await data_store.get_status_snapshot()
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "readings_stored": status_snapshot['total_readings']
    }


# ============== Main Entry Point ==============

if __name__ == "__main__":
    import uvicorn
    print("Starting GridSeva API Server...")
    print("Visit: http://localhost:8000/status")
    uvicorn.run(app, host="0.0.0.0", port=8000)
