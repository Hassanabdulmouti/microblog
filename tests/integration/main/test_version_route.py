"""
Test the /version route
"""

def test_version_route(client):
    """
    Test that /version returns 200 and a version key in JSON
    """
    response = client.get("/version")
    assert response.status_code == 200
    data = response.get_json()
    assert "version" in data
    assert isinstance(data["version"], str)
    assert len(data["version"]) > 0
