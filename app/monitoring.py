"""Application metrics with stable labels and an isolated registry per app."""
from prometheus_client import CollectorRegistry, Counter
from prometheus_flask_exporter import PrometheusMetrics


def init_monitoring(app):
    """Record HTTP metrics and initialize error counters before the first error."""
    registry = CollectorRegistry()
    PrometheusMetrics(app, registry=registry, group_by='endpoint', excluded_paths=[r'^/health$'])
    errors = Counter('microblog_errors_total', 'Unhandled application errors',
                     ['endpoint'], registry=registry)
    for endpoint in [*app.view_functions, 'unknown']:
        errors.labels(endpoint=endpoint)
    app.extensions['monitoring_errors'] = errors
