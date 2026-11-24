"""
Analytics engine for Twitter Trending Taglines and Hashtags.
Handles tweet ingestion, hashtag tracking, frequency counts, sentiment estimation,
and Redis caching with graceful in-memory fallback.
"""

import os
import re
import time
import json
from collections import defaultdict
from typing import List, Dict, Any, Optional

try:
    import redis
except ImportError:
    redis = None

class TweetAnalyticsEngine:
    def __init__(self, redis_host: str = "redis", redis_port: int = 6379, redis_password: Optional[str] = None):
        self.redis_host = os.getenv("REDIS_HOST", redis_host)
        self.redis_port = int(os.getenv("REDIS_PORT", str(redis_port)))
        self.redis_password = os.getenv("REDIS_PASSWORD", redis_password)
        self.redis_client = None
        self._warned_redis = False
        self.in_memory_tags = defaultdict(int)
        self.in_memory_tweets = []
        self.in_memory_sentiment = defaultdict(lambda: {"positive": 0, "neutral": 0, "negative": 0})
        self.in_memory_timeline = defaultdict(lambda: defaultdict(int))
        self._init_redis()
        self._seed_sample_data()

    def _init_redis(self):
        """Attempts connection to Redis; falls back cleanly if unavailable."""
        if not redis:
            if not self._warned_redis:
                print("[INFO] Redis python library not installed, using high-speed in-memory mode")
                self._warned_redis = True
            return
        try:
            client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                decode_responses=True,
                socket_connect_timeout=2.0,
                socket_timeout=2.0
            )
            client.ping()
            self.redis_client = client
            print(f"[INFO] Connected to Redis at {self.redis_host}:{self.redis_port}")
        except Exception as e:
            if not self._warned_redis:
                print(f"[INFO] Redis connection failed ({e}). Operating in memory mode.")
                self._warned_redis = True
            self.redis_client = None

    def is_redis_connected(self) -> bool:
        if not self.redis_client:
            # Retry connection once in case Redis just came online
            self._init_redis()
        if not self.redis_client:
            return False
        try:
            return self.redis_client.ping()
        except Exception:
            self.redis_client = None
            return False

    def _simple_sentiment(self, text: str) -> str:
        """Lightweight rule-based sentiment classifier for quick analytics."""
        text_lower = text.lower()
        positive_keywords = ["love", "great", "awesome", "breakthrough", "amazing", "good", "best", "leading", "success", "innovative", "fast", "future"]
        negative_keywords = ["bad", "fail", "broken", "slow", "down", "bug", "crash", "worst", "hate", "terrible", "issue", "risk", "outage"]
        
        pos_hits = sum(1 for w in positive_keywords if re.search(r'\b' + re.escape(w) + r'\b', text_lower))
        neg_hits = sum(1 for w in negative_keywords if re.search(r'\b' + re.escape(w) + r'\b', text_lower))

        if pos_hits > neg_hits:
            return "positive"
        elif neg_hits > pos_hits:
            return "negative"
        return "neutral"

    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags and normalize to lowercase without '#', but preserve display."""
        raw_tags = re.findall(r'#(\w+)', text)
        return [tag.strip() for tag in raw_tags if tag.strip()]

    def ingest_tweet(self, author: str, text: str, hashtags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Ingests a new tweet, updates counters, sentiment, and trend leaderboard."""
        extracted = self._extract_hashtags(text)
        if hashtags:
            for h in hashtags:
                clean = h.replace("#", "").strip()
                if clean and clean not in extracted:
                    extracted.append(clean)
        
        if not extracted:
            # Default fallback tag if none found
            extracted = ["GeneralTech"]

        sentiment = self._simple_sentiment(text)
        timestamp = int(time.time())
        minute_bucket = time.strftime("%H:%M", time.localtime(timestamp))

        tweet_record = {
            "id": f"tw_{timestamp}_{int(time.time() * 1000) % 10000}",
            "author": author or "AnonymousUser",
            "text": text,
            "hashtags": extracted,
            "sentiment": sentiment,
            "timestamp": timestamp,
            "time_str": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
        }

        # Redis storage
        if self.is_redis_connected():
            try:
                pipe = self.redis_client.pipeline()
                pipe.incr("stats:total_tweets")
                pipe.lpush("stream:recent_tweets", json.dumps(tweet_record))
                pipe.ltrim("stream:recent_tweets", 0, 99) # keep last 100

                for tag in extracted:
                    norm_tag = tag.lower()
                    pipe.zincrby("leaderboard:hashtags", 1, norm_tag)
                    pipe.hset(f"tag:meta:{norm_tag}", "display", tag)
                    pipe.hincrby(f"tag:stats:{norm_tag}", "total_posts", 1)
                    pipe.hincrby(f"tag:stats:{norm_tag}", f"sentiment_{sentiment}", 1)
                    pipe.hincrby(f"tag:timeline:{norm_tag}", minute_bucket, 1)

                pipe.execute()
                return tweet_record
            except Exception as e:
                print(f"[WARN] Error writing to Redis: {e}, falling back to memory")

        # Fallback in-memory
        self.in_memory_tweets.insert(0, tweet_record)
        if len(self.in_memory_tweets) > 100:
            self.in_memory_tweets.pop()

        for tag in extracted:
            norm_tag = tag.lower()
            self.in_memory_tags[norm_tag] += 1
            self.in_memory_sentiment[norm_tag][sentiment] += 1
            self.in_memory_timeline[norm_tag][minute_bucket] += 1

        return tweet_record

    def get_trends(self, limit: int = 10) -> Dict[str, Any]:
        """Returns the top trending taglines, total tweet volume, and sentiment breakdown."""
        redis_ok = self.is_redis_connected()
        total_tweets = 0
        trends = []

        if redis_ok:
            try:
                total_tweets = int(self.redis_client.get("stats:total_tweets") or 0)
                # Redis ZREVRANGE to get top hashtags
                top_items = self.redis_client.zrevrange("leaderboard:hashtags", 0, limit - 1, withscores=True)
                for norm_tag, count in top_items:
                    display = self.redis_client.hget(f"tag:meta:{norm_tag}", "display") or norm_tag
                    stats = self.redis_client.hgetall(f"tag:stats:{norm_tag}") or {}
                    pos = int(stats.get("sentiment_positive", 0))
                    neu = int(stats.get("sentiment_neutral", 0))
                    neg = int(stats.get("sentiment_negative", 0))
                    tot = int(count)

                    trends.append({
                        "tag": f"#{display}",
                        "key": norm_tag,
                        "post_count": tot,
                        "sentiment": {
                            "positive": pos,
                            "neutral": neu,
                            "negative": neg,
                            "positive_pct": round((pos / tot * 100), 1) if tot > 0 else 0
                        },
                        "reach_estimate": tot * 1420,
                        "velocity_per_min": max(1, tot // 5)
                    })
            except Exception as e:
                print(f"[WARN] Redis get_trends failed: {e}")
                redis_ok = False

        if not redis_ok:
            total_tweets = len(self.in_memory_tweets) + sum(self.in_memory_tags.values()) // max(1, len(self.in_memory_tags) or 1)
            sorted_tags = sorted(self.in_memory_tags.items(), key=lambda x: x[1], reverse=True)[:limit]
            for norm_tag, count in sorted_tags:
                pos = self.in_memory_sentiment[norm_tag]["positive"]
                neu = self.in_memory_sentiment[norm_tag]["neutral"]
                neg = self.in_memory_sentiment[norm_tag]["negative"]
                trends.append({
                    "tag": f"#{norm_tag.capitalize()}",
                    "key": norm_tag,
                    "post_count": count,
                    "sentiment": {
                        "positive": pos,
                        "neutral": neu,
                        "negative": neg,
                        "positive_pct": round((pos / count * 100), 1) if count > 0 else 0
                    },
                    "reach_estimate": count * 1420,
                    "velocity_per_min": max(1, count // 5)
                })

        return {
            "total_tweets_analyzed": total_tweets,
            "tracked_tags_count": len(trends),
            "trends": trends,
            "storage_backend": "Redis In-Memory Cache" if redis_ok else "Local Process Memory (Fallback)"
        }

    def get_tag_detail(self, tag_key: str) -> Optional[Dict[str, Any]]:
        """Returns deep-dive analytics for a single trending hashtag."""
        norm_tag = tag_key.lower().replace("#", "")
        redis_ok = self.is_redis_connected()

        if redis_ok:
            try:
                score = self.redis_client.zscore("leaderboard:hashtags", norm_tag)
                if score is None:
                    return None
                display = self.redis_client.hget(f"tag:meta:{norm_tag}", "display") or norm_tag
                stats = self.redis_client.hgetall(f"tag:stats:{norm_tag}") or {}
                timeline = self.redis_client.hgetall(f"tag:timeline:{norm_tag}") or {}
                pos = int(stats.get("sentiment_positive", 0))
                neu = int(stats.get("sentiment_neutral", 0))
                neg = int(stats.get("sentiment_negative", 0))
                tot = int(score)

                # Fetch sample tweets matching this tag from recent tweets
                recent = self.redis_client.lrange("stream:recent_tweets", 0, 50)
                samples = []
                for item in recent:
                    try:
                        tw = json.loads(item)
                        if any(t.lower() == norm_tag for t in tw.get("hashtags", [])):
                            samples.append(tw)
                    except Exception:
                        pass

                return {
                    "tag": f"#{display}",
                    "key": norm_tag,
                    "total_posts": tot,
                    "sentiment": {"positive": pos, "neutral": neu, "negative": neg},
                    "timeline": timeline,
                    "sample_tweets": samples[:5]
                }
            except Exception as e:
                print(f"[WARN] Redis get_tag_detail error: {e}")

        # In-memory detail
        if norm_tag in self.in_memory_tags:
            tot = self.in_memory_tags[norm_tag]
            samples = [tw for tw in self.in_memory_tweets if any(t.lower() == norm_tag for t in tw.get("hashtags", []))]
            return {
                "tag": f"#{norm_tag.capitalize()}",
                "key": norm_tag,
                "total_posts": tot,
                "sentiment": self.in_memory_sentiment[norm_tag],
                "timeline": dict(self.in_memory_timeline[norm_tag]),
                "sample_tweets": samples[:5]
            }

        return None

    def get_recent_stream(self, limit: int = 15) -> List[Dict[str, Any]]:
        """Returns the most recent tweets processed."""
        if self.is_redis_connected():
            try:
                raw_items = self.redis_client.lrange("stream:recent_tweets", 0, limit - 1)
                return [json.loads(item) for item in raw_items]
            except Exception as e:
                print(f"[WARN] Redis stream read error: {e}")
        return self.in_memory_tweets[:limit]

    def _seed_sample_data(self):
        """Pre-seeds realistic trending tech/cloud hashtags and tweets."""
        seeds = [
            ("dev_cloud", "Deploying our microservices on #Kubernetes with zero downtime! Best cloud architecture.", ["Kubernetes", "CloudComputing"]),
            ("ai_insider", "The new generative models are mind-blowing. #AI innovation is moving so fast!", ["AI", "TechTrends"]),
            ("sre_lead", "Redis cache hit ratio jumped to 98.4% after query optimization. Huge latency drop! #DevOps #Redis", ["DevOps", "Redis", "CloudComputing"]),
            ("tech_daily", "Why multi-cloud and hybrid-cloud are the top priorities for enterprises in 2026. #CloudComputing #HybridCloud", ["CloudComputing", "HybridCloud"]),
            ("python_fan", "Building scalable cloud microservices with FastAPI and async Python. #Python #DevOps", ["Python", "DevOps"]),
            ("cyber_watch", "Ensure your container images are scanned for vulnerabilities before pushing. #CyberSecurity #DevOps", ["CyberSecurity", "DevOps"]),
            ("data_geek", "Analyzing petabytes of streaming data with distributed pipelines. #BigData #CloudComputing", ["BigData", "CloudComputing"]),
            ("kube_wizard", "Demonstrating pod self-healing on Kubernetes! Delete a pod and watch it respawn instantly. #Kubernetes", ["Kubernetes"]),
            ("cost_optimizer", "Right-sizing container CPU requests cut our AWS bill by 42%! Cost optimization is crucial. #CloudComputing #FinOps", ["CloudComputing", "FinOps"]),
            ("open_coder", "Open source tools make modern cloud native development accessible to everyone. #OpenSource #TechTrends", ["OpenSource", "TechTrends"])
        ]
        for author, text, tags in seeds:
            self.ingest_tweet(author, text, tags)
