from fastapi import Request


def get_audit_graph(request: Request):
    """Return the application-wide invoice audit graph."""
    return request.app.state.audit_graph