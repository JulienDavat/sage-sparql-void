# min.py
# Author: Thomas MINIER - MIT License 2017-2019
from abc import abstractmethod

from sage.query_engine.iterators.aggregates.partial_agg import PartialAggregator


class MinMaxAggregator(PartialAggregator):
    """A generic class for implementing Min/Max aggregations"""

    def __init__(self, variable, binds_to='?m'):
        super(MinMaxAggregator, self).__init__(variable, binds_to)
        self._groups = dict()
        self._size = 0

    def update(self, group_key, bindings):
        """Update the aggregator with a new value for a group of bindings"""
        if self._variable in bindings:
            if group_key not in self._groups:
                self._groups[group_key] = bindings[self._variable]
                self._size += 1
            elif self.is_new_local(self._groups[group_key], bindings[self._variable]):
                self._groups[group_key] = bindings[self._variable]

    def done(self, group_key):
        """Complete the aggregation for a group and return the result"""
        return self._groups[group_key]

    def size(self):
        return self._size

    @abstractmethod
    def is_new_local(self, old, value):
        pass


class MinAggregator(MinMaxAggregator):
    """A MinAggregator computes a minimum aggregation"""

    def get_type(self):
        """Return the name of the aggregator (used for serialization)"""
        return 'min'

    def is_new_local(self, old, value):
        return value < old

    def __repr__(self):
        return "<Aggregator(MIN({}) AS {})>".format(self._variable, self._binds_to)


class MaxAggregator(MinMaxAggregator):
    """A MaxAggregator computes a maximum aggregation"""

    def get_type(self):
        """Return the name of the aggregator (used for serialization)"""
        return 'max'

    def is_new_local(self, old, value):
        return value > old

    def __repr__(self):
        return "<Aggregator(MAX({}) AS {})>".format(self._variable, self._binds_to)
