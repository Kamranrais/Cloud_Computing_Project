import unittest
from app.analytics import TweetAnalyticsEngine

class TestTweetAnalytics(unittest.TestCase):
    def setUp(self):
        self.engine = TweetAnalyticsEngine(redis_host="localhost", redis_port=6379)

    def test_sentiment_classification(self):
        pos = self.engine._simple_sentiment("This breakthrough technology is amazing and great!")
        neg = self.engine._simple_sentiment("The server is broken, worst crash ever and fail.")
        neu = self.engine._simple_sentiment("This is a standard deployment document.")
        self.assertEqual(pos, "positive")
        self.assertEqual(neg, "negative")
        self.assertEqual(neu, "neutral")

    def test_hashtag_extraction(self):
        tags = self.engine._extract_hashtags("Loving the new #CloudComputing and #Kubernetes features! #DevOps")
        self.assertIn("CloudComputing", tags)
        self.assertIn("Kubernetes", tags)
        self.assertIn("DevOps", tags)

    def test_tweet_ingestion_and_trends(self):
        self.engine.ingest_tweet("test_dev", "Excited for #AI and #CloudComputing innovations!", ["AI"])
        trends = self.engine.get_trends(limit=5)
        self.assertGreater(trends["total_tweets_analyzed"], 0)
        tag_names = [t["tag"] for t in trends["trends"]]
        self.assertTrue(any("Cloud" in t or "Ai" in t or "AI" in t for t in tag_names))

if __name__ == "__main__":
    unittest.main()
