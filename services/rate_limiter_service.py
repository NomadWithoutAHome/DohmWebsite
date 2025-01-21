from upstash_redis import Redis
import time

class RateLimiter:
    def __init__(self):
        self.redis = Redis.from_env()
        self.window = 3600  # 1 hour window
        self.max_requests = 50  # Maximum requests per hour

    def _get_key(self, ip):
        """Generate Redis key for the IP"""
        return f"rate_limit:{ip}"

    async def is_rate_limited(self, ip):
        """Check if the IP has exceeded the rate limit"""
        key = self._get_key(ip)
        current_time = int(time.time())
        window_start = current_time - self.window

        try:
            # Clean up old requests
            self.redis.zremrangebyscore(key, 0, window_start)
            
            # Count requests in current window
            request_count = self.redis.zcount(key, window_start, current_time)
            
            if request_count >= self.max_requests:
                return True, self._get_reset_time(key)
            
            # Add new request
            self.redis.zadd(key, {str(current_time): current_time})
            # Set expiry on the key
            self.redis.expire(key, self.window)
            
            return False, None
            
        except Exception as e:
            print(f"Rate limiter error: {e}")
            return False, None  # On error, allow the request

    def _get_reset_time(self, key):
        """Get the time when the rate limit will reset"""
        try:
            oldest_request = self.redis.zrange(key, 0, 0, withscores=True)
            if oldest_request:
                return int(oldest_request[0][1] + self.window - time.time())
        except Exception:
            pass
        return self.window  # Default to full window if error

    def get_remaining_requests(self, ip):
        """Get remaining requests for an IP"""
        key = self._get_key(ip)
        current_time = int(time.time())
        window_start = current_time - self.window

        try:
            # Clean up old requests
            self.redis.zremrangebyscore(key, 0, window_start)
            
            # Count requests in current window
            request_count = self.redis.zcount(key, window_start, current_time)
            
            return max(0, self.max_requests - request_count)
        except Exception:
            return self.max_requests  # On error, return max requests 