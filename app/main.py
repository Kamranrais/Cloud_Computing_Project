"""
FastAPI Cloud Web Application for Twitter Trending Tagline Analytics.
Exposes endpoints for analytics, simulated tweet stream, CPU stress load test,
and Kubernetes readiness/liveness health probes.
"""

import os
import math
import time
import socket
from typing import Optional, List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.analytics import TweetAnalyticsEngine

app = FastAPI(
    title="Twitter TrendPulse - Cloud Analytics Platform",
    description="Real-time Twitter Trending Tagline & Hashtag Analyzer with Kubernetes & Redis support",
    version="1.0.0"
)

# Template and static configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))
static_dir = os.path.join(BASE_DIR, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Analytics Engine Instance
engine = TweetAnalyticsEngine()

# Host and Environment Identification for Multi-Cluster / Hybrid Cloud demonstration
POD_HOSTNAME = os.getenv("HOSTNAME", socket.gethostname())
CLUSTER_ENV = os.getenv("CLUSTER_ENV", "local-development")
DEPLOYMENT_TIER = os.getenv("DEPLOYMENT_TIER", "primary")

class TweetCreateRequest(BaseModel):
    author: Optional[str] = "CloudUser"
    text: str
    hashtags: Optional[List[str]] = None

class StressRequest(BaseModel):
    intensity: int = 500000

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Renders the main trending analytics cloud dashboard."""
    trends_data = engine.get_trends(limit=10)
    recent_stream = engine.get_recent_stream(limit=8)
    redis_status = engine.is_redis_connected()

    context = {
        "request": request,
        "pod_name": POD_HOSTNAME,
        "cluster_env": CLUSTER_ENV,
        "deployment_tier": DEPLOYMENT_TIER,
        "redis_connected": redis_status,
        "trends": trends_data["trends"],
        "total_tweets": trends_data["total_tweets_analyzed"],
        "backend": trends_data["storage_backend"],
        "recent_stream": recent_stream
    }
    return templates.TemplateResponse("index.html", context)

@app.get("/api/trends")
async def api_get_trends(limit: int = 10):
    """Returns trending taglines with post counts, reach, and sentiment."""
    return engine.get_trends(limit=limit)

@app.get("/api/trends/{tag_key}")
async def api_get_tag_detail(tag_key: str):
    """Returns deep analytics for a specific hashtag."""
    detail = engine.get_tag_detail(tag_key)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Tag #{tag_key} not found")
    return detail

@app.get("/api/stream")
async def api_get_stream(limit: int = 15):
    """Returns the most recent analyzed tweets."""
    return engine.get_recent_stream(limit=limit)

@app.post("/api/tweets")
async def api_post_tweet(tweet: TweetCreateRequest):
    """Ingests a new tweet and updates analytics."""
    if not tweet.text.strip():
        raise HTTPException(status_code=400, detail="Tweet text cannot be empty")
    created = engine.ingest_tweet(tweet.author, tweet.text, tweet.hashtags)
    return {"status": "success", "tweet": created}

@app.post("/api/simulate")
async def api_simulate_tweets(count: int = 10):
    """Simulates a burst of real-time tweets across various trending taglines."""
    import random
    sample_tags = [
        ("Kubernetes", ["#Kubernetes", "#CloudComputing", "#DevOps"]),
        ("AI", ["#AI", "#MachineLearning", "#TechTrends"]),
        ("CloudComputing", ["#CloudComputing", "#AWS", "#Azure"]),
        ("DevOps", ["#DevOps", "#CI_CD", "#Docker"]),
        ("Python", ["#Python", "#FastAPI", "#Coding"]),
        ("CyberSecurity", ["#CyberSecurity", "#ZeroTrust", "#CloudSecurity"]),
        ("BigData", ["#BigData", "#DataAnalytics", "#Streaming"])
    ]
    authors = ["cloud_architect", "dev_dan", "data_sarah", "sarah_sre", "alex_code", "ai_researcher", "ops_guru"]
    sentiments_templates = [
        "Incredible results deploying with {t}! Scalability is top-tier and flawless.",
        "Experiencing great performance improvements using {t} in our hybrid cloud infrastructure.",
        "Testing new microservices integration on {t}. Everything is smooth so far.",
        "Is anyone else noticing high latency with {t} today? Hoping for a quick patch.",
        "Loving the cost optimization results from right-sizing {t} instances this week!"
    ]

    generated = []
    for _ in range(max(1, min(count, 50))):
        topic, tags = random.choice(sample_tags)
        text_template = random.choice(sentiments_templates)
        text = text_template.format(t=f"#{topic}") + " " + " ".join(tags)
        author = random.choice(authors)
        t = engine.ingest_tweet(author, text, tags)
        generated.append(t)

    return {"status": "success", "simulated_count": len(generated)}

@app.post("/api/stress")
async def api_cpu_stress(stress: StressRequest):
    """
    CPU-intensive task designed to increase pod CPU utilization
    to demonstrate Horizontal Pod Autoscaler (HPA) triggering.
    """
    start = time.time()
    # Compute intensive prime calculations
    primes_count = 0
    limit = min(stress.intensity, 1500000)
    for i in range(2, limit):
        is_prime = True
        for d in range(2, int(math.isqrt(i)) + 1):
            if i % d == 0:
                is_prime = False
                break
        if is_prime:
            primes_count += 1

    duration = time.time() - start
    return {
        "status": "completed",
        "pod": POD_HOSTNAME,
        "primes_calculated": primes_count,
        "computation_time_seconds": round(duration, 4),
        "cpu_burned": True
    }

@app.get("/api/system-info")
async def api_system_info():
    """Cluster and Pod runtime diagnostic telemetry."""
    return {
        "pod_name": POD_HOSTNAME,
        "cluster_env": CLUSTER_ENV,
        "deployment_tier": DEPLOYMENT_TIER,
        "redis_connected": engine.is_redis_connected(),
        "timestamp": time.time()
    }

@app.get("/healthz")
async def healthz():
    """Kubernetes liveness probe: returns 200 if the process is alive."""
    return {"status": "healthy", "pod": POD_HOSTNAME}

@app.get("/ready")
async def ready():
    """
    Kubernetes readiness probe: confirms application is ready to receive traffic.
    Verifies memory store or Redis state.
    """
    return {
        "status": "ready",
        "pod": POD_HOSTNAME,
        "cluster_env": CLUSTER_ENV,
        "redis_healthy": engine.is_redis_connected()
    }
