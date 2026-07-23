from dataclasses import dataclass


@dataclass
class WebRTCSignal:
    type: str
    sdp: str = ""
    candidate: str = ""
    session_id: str = ""
