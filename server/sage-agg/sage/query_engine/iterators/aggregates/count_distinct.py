# count.py
# Author: Thomas MINIER - MIT License 2017-2019
import xxhash
from sage.query_engine.iterators.aggregates.partial_agg import PartialAggregator


class CountDistinctAggregator(PartialAggregator):
    """A CountDistinctAggregator evaluates a COUNT distinct aggregation"""

    def __init__(self, variable, binds_to='?c'):
        super(CountDistinctAggregator, self).__init__(variable, binds_to)
        self._groups = dict()

    def update(self, group_key, bindings):
        """Update the aggregator with a new value for a group of bindings"""
        if self._variable in bindings:
            if group_key not in self._groups:
                self._groups[group_key] = set()
            elt = xxhash.xxh64_hexdigest(bindings[self._variable])
            if not elt in self._groups[group_key]:
                self._groups[group_key].add(elt)

    def done(self, group_key):
        """Return the group for the distinct aggregation given the group key"""
        return {
            '__type__': 'count-distinct', 
            '__value__': list(self._groups[group_key])  
        }

    def get_type(self):
        """Return the name of the aggregator (used for serialization)"""
        return 'count-distinct'

    def __repr__(self):
        return "<Aggregator(COUNT(DISTINCT {}) AS {})>".format(self._variable, self._binds_to)

    def is_distinct(self):
        return True