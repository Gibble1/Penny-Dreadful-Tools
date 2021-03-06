import unittest

import pytest

from decksite.main import APP
from shared_web.smoke import SmokeTester


class DecksiteSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tester: SmokeTester = SmokeTester(APP)

    @pytest.mark.functional
    def test_home(self) -> None:
        self.tester.data_test('/', '<h1><string>Latest Decks</string></h1>')

    @pytest.mark.functional
    def test_some_pages(self) -> None:
        for path in ['/', '/people/', '/cards/', '/cards/Unsummon/', '/competitions/', '/competitions/', '/tournaments/', '/resources/', '/bugs/', '/signup/', '/report/']:
            self.tester.response_test(path, 200)
