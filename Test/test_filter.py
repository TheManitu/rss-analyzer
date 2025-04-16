import unittest
from rss_analyzer.filter import filter_content_by_keywords, extract_relevant_passages, filter_article_by_topic

class TestFilterFunctions(unittest.TestCase):
    def setUp(self):
        self.content = ("Microsoft hat kürzlich Updates für Windows 11 veröffentlicht.\n"
                        "Auch das neue iPhone 17 wurde vorgestellt.\n"
                        "Ein Update zu ChatGPT wurde ebenfalls bekannt gegeben.")
        self.query_windows = "Was gibt es Neues zu Windows?"
        self.query_chatgpt = "Was gibt es Neues zu ChatGPT?"

    def test_filter_content_by_keywords(self):
        keywords = ["windows", "microsoft"]
        filtered = filter_content_by_keywords(self.content, keywords)
        self.assertIn("Windows 11", filtered)
        self.assertNotIn("iPhone 17", filtered)
    
    def test_extract_relevant_passages(self):
        passages = extract_relevant_passages(self.content, self.query_windows, top_n=1, threshold=0.6)
        self.assertIn("Windows 11", passages)
        self.assertNotIn("iPhone 17", passages)
    
    def test_filter_article_by_topic_windows(self):
        article = {"title": "Windows 11 Update", "content": self.content}
        result = filter_article_by_topic(article, self.query_windows)
        self.assertTrue(result)
        # Für ChatGPT-Spezifische Anfrage sollte Windows-Artikel hier nicht passen.
        result_chat = filter_article_by_topic(article, self.query_chatgpt)
        self.assertFalse(result_chat)

if __name__ == "__main__":
    unittest.main()
