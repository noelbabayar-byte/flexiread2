import time
from app.utils.rate_limiter import rate_limiter

def test_rate_limiter_logic():
    """
    Test rate limiter logic with a short window to keep CI fast.
    """
    key = "test_user_limit"
    max_req = 2
    window = 1  # Using 1s instead of 5s to keep CI build fast and efficient
    
    rate_limiter.reset(key)
    
    # First two requests should be allowed
    assert rate_limiter.is_allowed(key, max_req, window) is True
    assert rate_limiter.is_allowed(key, max_req, window) is True
    
    # Third request should be blocked
    assert rate_limiter.is_allowed(key, max_req, window) is False
    
    # Wait safely past the 1-second window expiry
    time.sleep(window + 0.5)
    
    # Should be allowed again after expiry
    assert rate_limiter.is_allowed(key, max_req, window) is True
