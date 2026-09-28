import os
import unittest

from app.llm import enabled


class OptionalModelIntegrationTest(unittest.TestCase):
    """Runs as a smoke check locally and can call a real provider in CI."""

    @unittest.skipUnless(os.getenv("RUN_LLM_TESTS") == "1", "set RUN_LLM_TESTS=1 to run provider tests")
    def test_provider_is_configured(self):
        self.assertTrue(enabled(), "MODEL_PROVIDER and API_KEY must be configured")


if __name__ == "__main__":
    unittest.main()
