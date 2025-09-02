"""init modeule for app package"""

from app.get_dashboard_data import get_dashboard_ids
from app.prewarm_superset import main

__all__ = ["get_dashboard_ids", "main"]
