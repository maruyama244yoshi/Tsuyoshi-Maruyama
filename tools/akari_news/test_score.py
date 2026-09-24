import unittest
from tools.akari_news.score import judge, news_score


class Score(unittest.TestCase):
    def test_full(self):
        self.assertEqual(news_score({k: 1 for k in ("landlord_impact", "market_impact", "urgency", "data_reliability", "search_demand", "video_fit")}), 100)

    def test_bands(self):
        self.assertEqual(judge(49)[0], "archive_only")
        self.assertEqual(judge(50)[0], "news_candidate")
        self.assertEqual(judge(70)[0], "video_candidate")
        self.assertEqual(judge(84)[0], "video_candidate")
        self.assertEqual(judge(85)[0], "breaking_candidate")

    def test_missing(self):
        with self.assertRaises(ValueError):
            news_score({"landlord_impact": 1})


if __name__ == "__main__":
    unittest.main()
