from mangum import Mangum

from app.main import app
from app.maintenance import handle_maintenance_event


api_handler = Mangum(app, lifespan="off")


def handler(event, context):
    if isinstance(event, dict) and event.get("stockbrief_operation"):
        return handle_maintenance_event(event)
    return api_handler(event, context)
