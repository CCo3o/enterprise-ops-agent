import unittest

from app.agent import analyze, choose_tools
from app.tools import search_docs


class AgentTest(unittest.TestCase):
    def test_incident_selects_all_diagnostic_tools(self):
        tools = choose_tools("订单接口返回 500，日志有 connection timeout")
        self.assertEqual(tools, ["search_docs", "search_logs", "get_metric_snapshot"])

    def test_report_contains_evidence(self):
        result = analyze("为什么订单接口返回 500？")
        self.assertIn("连接池耗尽", result.findings[0])
        self.assertTrue(any(item["type"] == "log" for item in result.evidence))
        self.assertTrue(any(item["type"] == "metric" for item in result.evidence))

    def test_follow_up_is_not_duplicate_conclusion(self):
        result = analyze("为什么订单接口返回 500？\n那我应该先检查什么？")
        self.assertIn("先确认连接池", result.findings[0])

    def test_vector_search_returns_relevant_document(self):
        hits = search_docs("数据库连接池耗尽")
        self.assertTrue(hits)
        self.assertEqual(hits[0]["source"], "order-api.md")


if __name__ == "__main__":
    unittest.main()
