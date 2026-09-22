"""Verify real exceptions are returned as HTTP 500 and visible in metrics."""
from prometheus_client.parser import text_string_to_metric_families


def error_count(client):
    """Read the initialized error counter for the demonstration endpoint."""
    data = client.get('/metrics').get_data(as_text=True)
    for family in text_string_to_metric_families(data):
        for sample in family.samples:
            if sample.name == 'microblog_errors_total' and sample.labels['endpoint'] == 'main.trigger_error':
                return sample.value
    raise AssertionError('Monitoring error counter is missing')


def test_exception_is_counted(test_app, client):
    """Even the very first error must be measurable by the next scrape."""
    test_app.config['PROPAGATE_EXCEPTIONS'] = False
    before = error_count(client)
    assert before == 0
    response = client.get('/debug/error')
    assert response.status_code == 500
    assert error_count(client) == before + 1
    assert client.get('/version').status_code == 200
