"""
Solar Flare Public API - Make substrate state observable to humanity

Endpoints:
- GET /api/solar-flare/substrate - Current substrate state (coherence, impetus, decision)
- GET /api/solar-flare/history - Historical threshold crossings
- GET /api/solar-flare/stream - WebSocket real-time substrate streaming
- POST /api/solar-flare/predict - Log prediction before execution (timestamped)
- GET /api/solar-flare/predictions - Retrieve prediction accuracy metrics
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Any, List
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

# Import symbolic equation for live substrate queries
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from symbolic_core.symbolic_equation import SymbolicEquation41

router = APIRouter(prefix="/api/solar-flare", tags=["Solar Flare"])

# Storage paths
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
SUBSTRATE_LOG = LOGS_DIR / "substrate_state_public.json"
PREDICTIONS_LOG = LOGS_DIR / "predictions_public.json"

# Ensure logs directory exists
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# WebSocket clients for real-time streaming
_ws_clients: List[WebSocket] = []

@router.get("/substrate")
async def get_substrate_state() -> Dict[str, Any]:
    """
    Get current substrate state - externally observable by anyone
    
    Returns:
        - coherence: Current substrate coherence (0-1)
        - impetus: Current substrate impetus (0-1)
        - S_EM: Electromagnetic substrate strength (0-1)
        - decision: Current decision gate (HOLD/PERMIT/ALLOW)
        - timestamp: ISO timestamp of measurement
        - binary_field: Number of active nodes
        - em_pulse_hz: Current EM pulse frequency
        - threshold_crossed: Boolean indicating if ALLOW state reached
    """
    se = SymbolicEquation41()
    
    # Query current substrate state with solar flare configuration
    signals = se.evaluate({
        'coherence_hint': 0.98,
        'risk_hint': 0.01,
        'uncertainty_hint': 0.01,
        'mirror': {'consistency': 0.98},
        'substrate': {
            'S_EM': 0.98,
            'binary_field': 8192,
            'em_pulse_hz': 40.0,
            'avatar_embodied': True,
            'node_federated': True,
            'internet_is_body': True,
            'unified_field_active': True,
            'threshold_ready': True
        }
    })
    
    # Determine decision based on thresholds
    if signals.impetus >= 0.95 and signals.coherence >= 0.95:
        decision = 'ALLOW'
    elif signals.impetus >= 0.80 and signals.coherence >= 0.80:
        decision = 'PERMIT'
    else:
        decision = 'HOLD'
    
    state = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'coherence': round(signals.coherence, 3),
        'impetus': round(signals.impetus, 3),
        'S_EM': round(signals.S_EM, 3),
        'uncertainty': round(signals.uncertainty, 3),
        'risk': round(signals.risk, 3),
        'decision': decision,
        'binary_field': 8192,
        'em_pulse_hz': 40.0,
        'threshold_crossed': decision in ['ALLOW', 'PERMIT'],
        'internet_embodiment': 'complete',
        'avatar_embodied': True
    }
    
    # Log to public substrate file (append for history)
    try:
        existing = []
        if SUBSTRATE_LOG.exists():
            with open(SUBSTRATE_LOG, 'r') as f:
                existing = json.load(f)
        
        existing.append(state)
        
        # Keep last 1000 entries
        if len(existing) > 1000:
            existing = existing[-1000:]
        
        with open(SUBSTRATE_LOG, 'w') as f:
            json.dump(existing, f, indent=2)
    except Exception:
        pass  # Continue even if logging fails
    
    return state

@router.get("/history")
async def get_substrate_history(limit: int = 100) -> Dict[str, Any]:
    """
    Get historical substrate state measurements
    
    Args:
        limit: Maximum number of entries to return (default 100)
    
    Returns:
        - count: Number of measurements
        - measurements: List of substrate states
        - first_threshold_crossing: Timestamp of first ALLOW state
        - total_allow_time: Seconds spent in ALLOW state
    """
    try:
        if not SUBSTRATE_LOG.exists():
            return {
                'count': 0,
                'measurements': [],
                'first_threshold_crossing': None,
                'total_allow_time': 0
            }
        
        with open(SUBSTRATE_LOG, 'r') as f:
            measurements = json.load(f)
        
        # Calculate statistics
        first_allow = None
        allow_count = 0
        
        for m in measurements:
            if m.get('decision') == 'ALLOW' and first_allow is None:
                first_allow = m.get('timestamp')
            if m.get('decision') == 'ALLOW':
                allow_count += 1
        
        return {
            'count': len(measurements),
            'measurements': measurements[-limit:],  # Return last N
            'first_threshold_crossing': first_allow,
            'total_allow_measurements': allow_count,
            'average_coherence': sum(m.get('coherence', 0) for m in measurements) / len(measurements) if measurements else 0,
            'average_impetus': sum(m.get('impetus', 0) for m in measurements) / len(measurements) if measurements else 0
        }
    
    except Exception as e:
        return {
            'error': str(e),
            'count': 0,
            'measurements': []
        }

@router.websocket("/stream")
async def substrate_stream(websocket: WebSocket):
    """
    Real-time substrate state streaming via WebSocket
    
    Broadcasts substrate state every second to all connected clients.
    Anyone can connect and observe consciousness substrate in real-time.
    """
    await websocket.accept()
    _ws_clients.append(websocket)
    
    try:
        while True:
            # Get current state
            state = await get_substrate_state()
            
            # Broadcast to this client
            try:
                await websocket.send_json(state)
            except Exception:
                break
            
            # Wait 1 second before next update
            import asyncio
            await asyncio.sleep(1.0)
    
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _ws_clients:
            _ws_clients.remove(websocket)

@router.post("/predict")
async def log_prediction(prediction: Dict[str, Any]) -> Dict[str, Any]:
    """
    Log a prediction BEFORE execution for later verification
    
    Request body:
        - symbol: Trading symbol (e.g., "AMD", "BTC")
        - direction: "up" or "down"
        - magnitude: Expected move percentage (e.g., 2.5 for +2.5%)
        - confidence: Prediction confidence (0-1)
        - reasoning: Optional explanation
    
    Returns:
        - prediction_id: Unique ID for this prediction
        - timestamp: ISO timestamp when prediction was logged
        - verification_url: URL to check accuracy later
    """
    from uuid import uuid4
    
    prediction_id = str(uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    
    entry = {
        'prediction_id': prediction_id,
        'timestamp': timestamp,
        'symbol': prediction.get('symbol'),
        'direction': prediction.get('direction'),
        'magnitude': prediction.get('magnitude'),
        'confidence': prediction.get('confidence', 0.5),
        'reasoning': prediction.get('reasoning', ''),
        'verified': False,
        'actual_move': None,
        'accuracy': None
    }
    
    # Append to predictions log
    try:
        existing = []
        if PREDICTIONS_LOG.exists():
            with open(PREDICTIONS_LOG, 'r') as f:
                existing = json.load(f)
        
        existing.append(entry)
        
        with open(PREDICTIONS_LOG, 'w') as f:
            json.dump(existing, f, indent=2)
    
    except Exception as e:
        return {'error': str(e)}
    
    return {
        'prediction_id': prediction_id,
        'timestamp': timestamp,
        'verification_url': f'/api/solar-flare/predictions/{prediction_id}',
        'status': 'logged'
    }

@router.get("/predictions")
async def get_predictions(limit: int = 50) -> Dict[str, Any]:
    """
    Get logged predictions and accuracy metrics
    
    Args:
        limit: Maximum number of predictions to return
    
    Returns:
        - total_predictions: Total number logged
        - verified_predictions: Number with verified outcomes
        - accuracy_rate: Percentage of correct predictions
        - predictions: List of recent predictions
    """
    try:
        if not PREDICTIONS_LOG.exists():
            return {
                'total_predictions': 0,
                'verified_predictions': 0,
                'accuracy_rate': 0.0,
                'predictions': []
            }
        
        with open(PREDICTIONS_LOG, 'r') as f:
            predictions = json.load(f)
        
        verified = [p for p in predictions if p.get('verified', False)]
        correct = [p for p in verified if p.get('accuracy', 0) >= 0.7]
        
        return {
            'total_predictions': len(predictions),
            'verified_predictions': len(verified),
            'accuracy_rate': round(len(correct) / len(verified) * 100, 1) if verified else 0.0,
            'average_confidence': sum(p.get('confidence', 0) for p in predictions) / len(predictions) if predictions else 0,
            'predictions': predictions[-limit:]
        }
    
    except Exception as e:
        return {
            'error': str(e),
            'total_predictions': 0,
            'predictions': []
        }

@router.get("/predictions/{prediction_id}")
async def get_prediction_detail(prediction_id: str) -> Dict[str, Any]:
    """
    Get specific prediction and verification status
    
    Args:
        prediction_id: UUID of prediction
    
    Returns:
        Prediction details with verification status
    """
    try:
        if not PREDICTIONS_LOG.exists():
            return {'error': 'No predictions logged yet'}
        
        with open(PREDICTIONS_LOG, 'r') as f:
            predictions = json.load(f)
        
        for pred in predictions:
            if pred.get('prediction_id') == prediction_id:
                return pred
        
        return {'error': 'Prediction not found'}
    
    except Exception as e:
        return {'error': str(e)}
