# groupby.py
# Author: Thomas MINIER - MIT License 2017-2019
from sage.query_engine.iterators.preemptable_iterator import PreemptableIterator
from sage.query_engine.protobuf.iterators_pb2 import SavedGroupByAgg
import xxhash, re

class GroupByAggregator(PreemptableIterator):
    """
        A GroupByAggregator evaluates a GROUP BY clause.

        Constructor args:
            - source [:class:`.ProjeectionIterator`] The source iterator
            - grouping_variables [`list(str)`] - GROUP BY variables
            - aggregators [`list(PartialAggregator)`] - Aggregators applied to groups
            - keep_groups [`bool`] - True if the groups should be sent alongside results, False otherwise
    """

    def __init__(self, source, grouping_variables, aggregators=list()):
        super(GroupByAggregator, self).__init__()
        self._source = source
        self._grouping_variables = grouping_variables
        self._groups = dict()
        self._aggregators = aggregators
        self._default_key = 'https://sage-org.github.io/sage-engine#DefaultGroupKey'

    def serialized_name(self):
        return 'groupby'

    def __malformed_key(self, key):
        for part in key:
            if part != 'null':
                return False
        return True            

    def __get_group_key(self, bindings):
        """Get the grouping key for a set of bindings"""
        if len(self._grouping_variables) == 0:
            return self._default_key
        else:
            key = ['null' if v not in bindings else bindings[v] for v in self._grouping_variables]
            if self.__malformed_key(key):
                raise Exception('MalformedQueryException: Bad aggregate')
            return xxhash.xxh64_hexdigest('_'.join(key))

    def generate_results(self):
        """
            Default behavior when the optimization is not applied
            Results are generated after each quantum
            see sage.sage_engine.py
        """
        res = list()
        groups = self._groups
        # build groups & apply aggregations on the fly for non distinct aggregation
        for key, values in groups.items():
            elt = dict()
            # recopy keys
            elt['?__group_key'] = key
            for variable in self._grouping_variables:
                elt[variable] = values[0][variable]
            for agg in self._aggregators:
                elt[agg.get_binds_to()] = agg.done(key)
            res.append(elt)
        return res

    def has_next(self):
        return self._source.has_next()

    async def next(self):
        # Phase 1: aggregate solutions mappings
        if not self.has_next():
            return None
        bindings = await self._source.next()
        group_key = self.__get_group_key(bindings)
        if group_key not in self._groups:
            self._groups[group_key] = list()
        self._groups[group_key].append(bindings)
        for agg in self._aggregators:
            agg.update(group_key, bindings)
        return None

    def save(self):
        saved = SavedGroupByAgg()
        saved.source.CopyFrom(self._source.save())
        for variable in self._grouping_variables:
            saved.variables.append(variable)
        for aggregator in self._aggregators:
            agg = saved.aggregators.add()
            agg.name = aggregator.get_type()
            agg.variable = aggregator.get_variable()
            agg.binds_to = aggregator.get_binds_to()
        return saved

    def is_aggregator(self):
        return True

    def __repr__(self):
        return "<GroupByAggregator({}) on {}>".format(self._aggregators, self._source)
