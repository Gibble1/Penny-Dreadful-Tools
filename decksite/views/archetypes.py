from decksite.view import View


# pylint: disable=no-self-use
class Archetypes(View):
    def __init__(self, archetypes) -> None:
        super().__init__()
        self.archetypes = archetypes
        self.decks = []
        self.roots = [a for a in self.archetypes if a.is_root]
        self.show_seasons = True

    def page_title(self):
        return 'Archetypes'
