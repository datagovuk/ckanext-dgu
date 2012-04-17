import pylons

class Basket(object):
    """
    A Basket is a collection of things.  Things are categorised, and allowed
    categories are set up front.
    """

    categories = ('dataset',)

    def __init__(self, categories=None):
        if categories is None:
            categories = Basket.categories
        self.categories = categories[:]

    def add(self, item, category):
        """
        Add the given item to the given category
        """
        if category not in self.categories:
            raise ValueError('Unrecognized category %s' % category)
        items = pylons.session.get(category, [])
        if item not in items:
            items.append(item)
        pylons.session[category] = items
        pylons.session.save()

    def remove(self, item, category):
        """
        Remove the given item.

        Assumes item exists in basket at most once.
        """
        if category not in self.categories:
            raise ValueError('Unrecognized category %s' % category)
        items = pylons.session.get(category, [])
        try:
            items.remove(item)
        except ValueError:
            pass
        pylons.session[category] = items
        pylons.session.save()

    def clear(self, category):
        """
        Clear the basket.
        """
        if category not in self.categories:
            raise ValueError('Unrecognized category %s' % category)
        pylons.session.pop(category, None)
        pylons.session.save()

    def contents(self, category=None):
        """
        Returns a representation of the Basket.
        """
        if category is None:
            return pylons.session
        elif category in self.categories:
            return pylons.session.get(category,[])
        else:
            raise ValueError('Unrecognized category %s' % category)
            

