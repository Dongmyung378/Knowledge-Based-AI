from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Dict

from learning.util import Algorithm, AlgorithmRegistry

from math import log2

Example = Dict[str, Any]
Examples = List[Example]

from logging import getLogger

logger = getLogger(__name__)


@dataclass(frozen=True)
class AttrLogicExpression(ABC):
    """
    Abstract base class representing a logic expression.
    """
    ...

    @abstractmethod
    def __call__(self, *args, **kwargs):
        ...


@dataclass(frozen=True)
class Conjunction(AttrLogicExpression):
    """
    A configuration of attribute names and the values the attributes should take for this conjunction to evaluate
    to true.

    `attribute_confs` is a map from attribute names to their values.
    """
    attribute_confs: Dict[str, Any]

    def __post_init__(self):
        assert 'target' not in self.attribute_confs, "Nice try, but 'target' cannot be part of the hypothesis."

    def __call__(self, example: Example):
        """
        Evaluates whether the conjunction applies to an example or not. Returns true if it does, false otherwise.


        Args:
            example: Example to check if the conjunction applies.

        Returns:
            True if the values of *all* attributes mentioned in the conjunction and appearing in example are equal,
            false otherwise.


        """
        return all(self.attribute_confs[k] == example[k] for k in set(self.attribute_confs).intersection(example))

    def __repr__(self):
        return " AND ".join(f"{k} = {v}" for k, v in self.attribute_confs.items())


@dataclass(frozen=True)
class Disjunction(AttrLogicExpression):
    """
    Disjunction of conjunctions.
    """
    conjunctions: List[Conjunction]

    def __call__(self, example: Example):
        """
        Evaluates whether the disjunction applies to a given example.

        Args:
            example: Example to check if the disjunction applies.

        Returns: True if any of its conjunctions returns true, and false if none evaluates to true.

        """
        return any(c(example) for c in self.conjunctions)

    def __repr__(self):
        return " " + "\nOR\n ".join(f"{v}" for v in self.conjunctions)


class Tree(ABC):
    """
    This is an abstract base class representing a leaf or a node in a tree.
    """
    ...


@dataclass
class Leaf(Tree):
    """
    This is a leaf in the tree. It's value is the (binary) classification, either True or False.
    """
    target: bool


@dataclass
class Node(Tree):
    """
    This is a node in the tree. It contains the attribute `attr_name` which the node is splitting on and a dictionary
    `branches` that represents the children of the node and maps from attribute values to their corresponding subtrees.
    """
    attr_name: str
    branches: Dict[Any, Tree] = field(default_factory=dict)


def same_target(examples: Examples) -> bool:
    # check if the list of examples is empty
    if not examples:
        # raise an error since we cannot determine sameness from nothing
        raise ValueError("same_target called with empty example set.")
    # get the target value of the first example in the list
    first_target = examples[0]["target"]
    # check if every example in the list has the same target value as the first one
    # returns True only if all targets match
    return all(example["target"] == first_target for example in examples)

def plurality_value(examples: Examples) -> bool:
    # check if the list of examples is empty
    if not examples:
        # raise an error since we cannot determine the majority class
        raise ValueError("plurality_value called with empty example set.")
    #count how many examples have True as their target value
    true_count = sum(1 for ex in examples if ex["target"])
    # compare the number of True values to the number of False values
    # if True values are greater than or equal to False values, return True
    # this resolves ties by favoring True
    return true_count >= (len(examples) - true_count)


def binary_entropy(examples: Examples) -> float:
    # check if the example list is empty
    if not examples:
        # return 0 entropy since there's no data to measure uncertainty from
        return 0.0
    
    # calculate the proportion of examples where target is True
    p = sum(1 for ex in examples if ex["target"]) / len(examples)
    
    # if all targets are True or all are False (pure), entropy is 0
    if p == 0 or p == 1:
        # if the dataset is perfectly pure (no uncertainty), entropy is zero
        return 0.0
    
    # apply the binary entropy formula: -p*log2(p) - (1-p)*log2(1-p)
    # this measures the impurity or uncertainty in the classification
    return -p * log2(p) - (1 - p) * log2(1 - p)

def to_logic_expression(tree: Tree) -> AttrLogicExpression:
    # define a helper function to recursively collect all paths to positive leaves
    def traverse(node: Tree, current_attrs: List[tuple[str, Any]]) -> List[Conjunction]:
        # check if the current node is a Leaf node
        if isinstance(node, Leaf):
            # include only the paths that end in a positive classification
            if node.target:
                # build a dictionary of attribute-value pairs collected along the path
                attr_dict = {}
                for attr_name, attr_value in current_attrs:
                    attr_dict[attr_name] = attr_value
                # wrap the path as a Conjunction object
                return [Conjunction(attribute_confs=attr_dict)]
            # if the leaf is negative, return an empty list (no hypothesis added)
            return []
        
        # check if the current node is a decision node
        if isinstance(node, Node):
            result = []
            # for each possible value of the node's attribute
            for value, child in node.branches.items():
                # add this attribute-value pair to the current path
                new_attrs = current_attrs + [(node.attr_name, value)]
                # recursively traverse the child node
                result.extend(traverse(child, new_attrs))
            # return all valid conjunctions gathered from children
            return result
    
    # start the traversal from the root of the tree with an empty path
    conjunctions = traverse(tree, [])
    # wrap all gathered conjunctions in a Disjunction (OR of ANDs)
    # No positive leaves means a constant False expression. A positive root leaf
    # already produces an empty conjunction, which correctly represents True.
    return Disjunction(conjunctions=conjunctions)

# Register this learner under the name "dtl" for dynamic use
@AlgorithmRegistry.register("dtl")
class DecisionTreeLearner(Algorithm):
    """
    This is the decision tree learning algorithm.
    """

    def find_hypothesis(self) -> AttrLogicExpression:
        # initiate the decision tree learning algorithm
        # pass the training examples and attributes from the dataset
        # parent_examples is initially empty since this is the top-level call
        tree = self.decision_tree_learning(examples=self.dataset.examples, attributes=self.dataset.attributes,
                                            parent_examples=[])
        # once the tree is learned, convert it into a logical expression (Disjunction of Conjunctions)
        return to_logic_expression(tree)

    def decision_tree_learning(self, examples: Examples, attributes: List[str], parent_examples: Examples) -> Tree:
        # if the current example set is empty (no data to learn from)
        if not examples:
            # if even the parent examples are empty, learning cannot proceed
            if not parent_examples:
                raise ValueError("Cannot determine plurality value: both current and parent examples are empty.")
            # otherwise, fallback to majority classification of the parent set
            return Leaf(target=plurality_value(parent_examples))
        
        # if all examples have the same classification, create a leaf node with that value
        if same_target(examples):
            return Leaf(target=examples[0]["target"])
        
        # if there are no attributes left to split on, return the majority target value
        if not attributes:
            return Leaf(target=plurality_value(examples))
        
        # select the attribute that provides the highest information gain for splitting
        best_attr = self.get_most_important_attribute(attributes, examples)
        
        # prepare to build branches of the decision tree for each value of the selected attribute
        children = {}
        # for each unique value that the best attribute can take in the dataset
        for val in set(ex[best_attr] for ex in examples):
            # create a subset of examples where best_attr == val
            subset = [ex for ex in examples if ex[best_attr] == val]
            # create a list of remaining attributes after removing the one just split on
            remaining_attrs = [a for a in attributes if a != best_attr]
            # recursively learn the subtree for this attribute value
            children[val] = self.decision_tree_learning(subset, remaining_attrs, examples)
        # return a decision node that splits on best_attr and has learned child branches
        return Node(attr_name=best_attr, branches=children)

    def get_most_important_attribute(self, attributes: List[str], examples: Examples) -> str:
        # check if the list of attributes is empty
        if not attributes:
            # raise an error since we cannot choose an attribute from nothing
            raise ValueError("get_most_important_attribute called with empty attribute list.")
        # check if the dataset is empty
        if not examples:
            # raise an error since we cannot evaluate any attribute without examples
            raise ValueError("get_most_important_attribute called with empty example list.")
        
        # compute the information gain for each attribute in the list
        gains = {attr: self.information_gain(examples, attr) for attr in attributes}
        # return the attribute with the highest information gain
        return max(gains, key=gains.get)

    def information_gain(self, examples: Examples, attribute: str) -> float:
        # if there are no examples, return 0 gain (no information to learn from)
        if not examples:
            return 0.0
        
        # calculate the entropy of the full dataset (before any split)
        total_entropy = binary_entropy(examples)
        
        # create a dictionary to group examples by their value for the given attribute
        value_groups = {}
        for ex in examples:
            val = ex[attribute]
            # group examples by the value of the current attribute (used to compute splits)
            value_groups.setdefault(val, []).append(ex)
        
        # initialize the weighted sum of entropies after the split
        weighted_entropy = 0.0
        # total number of examples
        total_size = len(examples)
        # for each group of examples (split by a specific value of the attribute)
        for group in value_groups.values():
            # compute the weight
            weight = len(group) / total_size
            # add the group's contribution to the weighted entropy
            weighted_entropy += weight * binary_entropy(group)
        # information gain = entropy before split - weighted entropy after split
        return total_entropy - weighted_entropy

# Register this learner under the name "my-dtl" for dynamic use
@AlgorithmRegistry.register("my-dtl")
class MyDecisionTreeLearner(Algorithm):
    """
    Improved Decision Tree Learner:
    - Introduces maximum depth limit to prevent overfitting
    - Uses information gain ratio instead of plain information gain for attribute selection
    """
    
    def find_hypothesis(self):
        # get the number of training examples in the dataset
        n = len(self.dataset.examples)
        # set the maximum allowed tree depth based on log2(n)
        # ensures the tree doesn't grow too deep (regularization)
        self.max_depth = int(log2(n)) if n > 0 else 1
        # initialize current recursion depth to 0
        self.depth = 0

        # start learning the tree from the full dataset and attribute list
        tree = self.decision_tree_learning(
            examples=self.dataset.examples,
            attributes=self.dataset.attributes,
            parent_examples=[]
        )
        # convert the learned decision tree into an equivalent logical expression
        # expressed as a Disjunction of Conjunctions
        return to_logic_expression(tree)
    
    def decision_tree_learning(self, examples: Examples, attributes: List[str], parent_examples: Examples) -> Tree:
        # base case: no examples to learn from
        if not examples:
            # if no parent examples either, we can't determine majority class
            if not parent_examples:
                raise ValueError("Cannot determine plurality value: both current and parent examples are empty.")
            # use majority class of parent set
            return Leaf(target=plurality_value(parent_examples))
        
        # base case: all examples have the same classification
        if same_target(examples):
            return Leaf(target=examples[0]["target"])
        # base case: no attributes left to split on, or max depth reached
        if not attributes or self.depth >= self.max_depth:
            return Leaf(target=plurality_value(examples))

        # select the attribute that gives the best gain ratio
        best_attr = self.get_most_important_attribute(attributes, examples)

        # prepare branches for each unique value of the best attribute
        children = {}
        for val in set(ex[best_attr] for ex in examples):
            # filter examples where best_attr equals current value
            subset = [ex for ex in examples if ex[best_attr] == val]
            # create a list of remaining attributes after removing the one just split on
            remaining_attrs = [a for a in attributes if a != best_attr]
            # recursively learn subtree for the value subset
            children[val] = self.decision_tree_learning(subset, remaining_attrs, examples)
        # increase depth counter after building all child nodes
        # note: this affects subsequent recursive calls
        self.depth += 1

        # return a decision node that splits on best_attr with learned branches
        return Node(attr_name=best_attr, branches=children)
    
    def get_most_important_attribute(self, attributes: List[str], examples: Examples) -> str:
        # ensure attributes list is not empty
        if not attributes:
            raise ValueError("get_most_important_attribute called with empty attribute list.")
        # ensure examples are available for evaluation
        if not examples:
            raise ValueError("get_most_important_attribute called with empty example list.")
        # calculate the gain ratio for each attribute
        gains = {attr: self.information_gain(examples, attr) for attr in attributes}
        # return the attribute with the highest gain ratio
        return max(gains, key=gains.get)
    
    def information_gain(self, examples: Examples, attribute: str) -> float:
        # calculate the entropy of the entire dataset before any split
        total_entropy = binary_entropy(examples)
        # initialize a dictionary to group examples by their value for the given attribute
        value_groups = {}
        for ex in examples:
            val = ex[attribute]
            # group examples by the value of the current attribute (used to compute splits)
            value_groups.setdefault(val, []).append(ex)

        # initialize accumulators for weighted entropy and split info
        weighted_entropy = 0.0
        split_info = 0.0
        # total number of examples
        total_size = len(examples)
        # iterate over each group of examples for each unique value of the attribute
        for group in value_groups.values():
            # total number of group
            group_size = len(group)
            # weight is the proportion of examples in this group relative to the full dataset
            # used both in weighted entropy and in calculating split information
            weight = group_size / total_size
            # accumulate weighted entropy after split
            weighted_entropy += weight * binary_entropy(group)
            # accumulate split info (measure of how evenly the split divides the dataset)
            split_info -= weight * log2(weight) if weight > 0 else 0

        # if split info is zero (e.g., attribute has only one value), return zero gain
        if split_info == 0:
            return 0
        # calculate actual information gain from the split
        info_gain = total_entropy - weighted_entropy
        # return gain ratio = information gain / split info
        return info_gain / split_info


# The original learners above remain available under their original names.
# These variants keep their fitted tree and use a path-local depth bound.
from collections.abc import Mapping
from math import isfinite


def _validate_categorical_example(example, domains):
    """Validate a complete example without treating missing values as wildcards."""
    if not isinstance(example, Mapping):
        raise ValueError("An example must be a mapping of attribute names to values.")
    for name, values in domains:
        if name not in example:
            raise ValueError(f"Missing required attribute: {name!r}.")
        value = example[name]
        if not any(type(value) is type(known) and value == known for known in values):
            raise ValueError(f"Unseen category for attribute {name!r}: {value!r}.")


@dataclass(frozen=True, repr=False)
class _ValidatedDisjunction(Disjunction):
    """A DNF with the same explicit input contract as its fitted tree."""

    domains: tuple

    def __call__(self, example):
        _validate_categorical_example(example, self.domains)
        return super().__call__(example)

    def __repr__(self):
        if not self.conjunctions:
            return "FALSE"
        if any(not conjunction.attribute_confs for conjunction in self.conjunctions):
            return "TRUE"
        return super().__repr__()


@AlgorithmRegistry.register("corrected-dtl")
class CorrectedDecisionTreeLearner(Algorithm):
    """Categorical binary DTL with deterministic ties and optional regularisation.

    Labels must be booleans. Categories may be bool, int, finite float, str,
    or None; None is an explicit category, not an absent attribute. All training
    rows must have the same feature names. Predictions require every training
    feature and reject categories absent from training. Values observed in the
    full training set but absent at a particular node use that node's training
    majority through an explicit fallback leaf. Majority ties favour True.

    ``max_depth`` counts edges from the root, so zero fits a single leaf.
    ``min_samples_leaf`` applies to nonempty training partitions, not synthetic
    fallback branches. Zero-gain splits remain eligible, allowing XOR learning.
    Training and validation dictionaries are never modified.
    """

    use_gain_ratio = False
    use_default_depth = False
    use_pruning = False

    def __init__(self, dataset, max_depth=None, min_samples_leaf=1, validation_dataset=None):
        super().__init__(dataset)
        if max_depth is not None and (type(max_depth) is not int or max_depth < 0):
            raise ValueError("max_depth must be a nonnegative integer or None.")
        if type(min_samples_leaf) is not int or min_samples_leaf < 1:
            raise ValueError("min_samples_leaf must be a positive integer.")
        if validation_dataset is not None and not self.use_pruning:
            raise ValueError("validation_dataset is only used by pruned-dtl.")
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.validation_dataset = validation_dataset

    @staticmethod
    def _category_key(value):
        if type(value) not in (bool, int, float, str, type(None)):
            raise ValueError("Categories must be bool, int, finite float, str, or None.")
        if type(value) is float and not isfinite(value):
            raise ValueError("Float categories must be finite.")
        return type(value).__name__, repr(value)

    def _training_schema(self, examples):
        if not examples:
            raise ValueError("Training data must contain at least one example.")
        if not all(isinstance(example, Mapping) for example in examples):
            raise ValueError("Training examples must be mappings.")
        names = [name for name in examples[0] if name != "target"]
        if any(type(name) is not str for name in names):
            raise ValueError("Attribute names must be strings.")
        names.sort()
        expected = set(names) | {"target"}
        for example in examples:
            if set(example) != expected:
                raise ValueError("Training rows must have identical attributes and a target.")
            if type(example["target"]) is not bool:
                raise ValueError("Training targets must be booleans.")
        domains = []
        for name in names:
            values_by_key = {}
            for example in examples:
                value = example[name]
                key = self._category_key(value)
                values_by_key[key] = value
            values = tuple(values_by_key[key] for key in sorted(values_by_key))
            # Python dictionary branches equate True, 1, and 1.0. Reject mixed
            # numeric aliases rather than silently merging distinct categories.
            if len(set(values)) != len(values):
                raise ValueError(f"Ambiguous equal-valued categories for attribute {name!r}.")
            domains.append((name, values))
        return tuple(domains)

    def find_hypothesis(self):
        self.domains_ = self._training_schema(self.dataset.examples)
        examples = [dict(example) for example in self.dataset.examples]
        self.max_depth_ = self.max_depth
        if self.max_depth_ is None and self.use_default_depth:
            self.max_depth_ = int(log2(len(examples)))
        self._node_majorities = {}
        self._domains_by_name = dict(self.domains_)
        self.tree_ = self._grow(examples, [name for name, _ in self.domains_], depth=0)
        self.pruning_summary_ = None
        if self.use_pruning:
            if self.validation_dataset is None or not self.validation_dataset.examples:
                raise ValueError("pruned-dtl requires nonempty, separately supplied validation data.")
            if not all(isinstance(example, Mapping) for example in self.validation_dataset.examples):
                raise ValueError("Validation examples must be mappings.")
            validation = [dict(example) for example in self.validation_dataset.examples]
            for example in validation:
                _validate_categorical_example(example, self.domains_)
                if type(example.get("target")) is not bool:
                    raise ValueError("Validation targets must be booleans.")
            before_nodes = self._measure_tree(self.tree_)["nodes"]
            before_correct = self._correct(self.tree_, validation)
            self._pruning_replacements = 0
            self.tree_ = self._prune(self.tree_, validation)
            self.pruning_summary_ = {
                "validation_samples": len(validation),
                "validation_correct_before": before_correct,
                "validation_correct_after": self._correct(self.tree_, validation),
                "replacement_count": self._pruning_replacements,
                "nodes_removed": before_nodes - self._measure_tree(self.tree_)["nodes"],
            }
        expression = to_logic_expression(self.tree_)
        return _ValidatedDisjunction(expression.conjunctions, self.domains_)

    def fit(self):
        # A failed refit must not expose a new tree with an old DNF hypothesis.
        # Removing fitted state also ensures a second fit has no shared depth
        # counter or pruning residue from its predecessor.
        fitted_names = ("hypothesis", "tree_", "domains_", "max_depth_", "pruning_summary_",
                        "_node_majorities", "_domains_by_name", "_pruning_replacements")
        for name in fitted_names:
            self.__dict__.pop(name, None)
        try:
            self.hypothesis = self.find_hypothesis()
        except Exception:
            for name in fitted_names:
                self.__dict__.pop(name, None)
            raise

    def predict(self, example):
        self._require_fitted()
        # Keep the DNF as an inspectable equivalent hypothesis, while evaluating
        # the retained tree along one path for routine inference.
        return self.predict_tree(example)

    def _grow(self, examples, attributes, depth):
        majority = plurality_value(examples)
        if (same_target(examples) or not attributes
                or (self.max_depth_ is not None and depth >= self.max_depth_)):
            return Leaf(majority)
        best_name, best_groups, best_score = None, None, None
        entropy = binary_entropy(examples)
        for name in attributes:
            groups = {}
            for example in examples:
                groups.setdefault(example[name], []).append(example)
            if len(groups) < 2 or any(len(group) < self.min_samples_leaf for group in groups.values()):
                continue
            weighted_entropy = sum(len(group) / len(examples) * binary_entropy(group)
                                   for group in groups.values())
            score = max(0.0, entropy - weighted_entropy)
            if self.use_gain_ratio:
                split_info = -sum(len(group) / len(examples) * log2(len(group) / len(examples))
                                  for group in groups.values())
                score /= split_info
            # Attribute names are sorted, and close scores retain the first.
            if best_score is None or score > best_score + 1e-12:
                best_name, best_groups, best_score = name, groups, score
        if best_name is None:
            return Leaf(majority)
        node = Node(best_name)
        self._node_majorities[id(node)] = majority
        remaining = [name for name in attributes if name != best_name]
        for value in self._domains_by_name[best_name]:
            subset = best_groups.get(value)
            node.branches[value] = (self._grow(subset, remaining, depth + 1)
                                    if subset else Leaf(majority))
        return node

    @staticmethod
    def _tree_prediction(tree, example):
        while isinstance(tree, Node):
            tree = tree.branches[example[tree.attr_name]]
        return tree.target

    def _correct(self, tree, examples):
        return sum(self._tree_prediction(tree, example) == example["target"] for example in examples)

    def _prune(self, tree, validation):
        if isinstance(tree, Leaf):
            return tree
        for value, child in tree.branches.items():
            routed = [example for example in validation if example[tree.attr_name] == value]
            tree.branches[value] = self._prune(child, routed)
        majority = self._node_majorities[id(tree)]
        leaf_correct = sum(example["target"] == majority for example in validation)
        # Ties prefer the smaller tree, including subtrees with no validation
        # observations. The majority is learned from training data only.
        if leaf_correct >= self._correct(tree, validation):
            self._pruning_replacements += 1
            return Leaf(majority)
        return tree

    def _require_fitted(self):
        if not hasattr(self, "hypothesis"):
            raise ValueError("Call fit() before prediction, tracing, or tree metrics.")

    def predict_tree(self, example):
        """Evaluate the retained tree, using the same contract as the DNF."""
        self._require_fitted()
        _validate_categorical_example(example, self.domains_)
        return self._tree_prediction(self.tree_, example)

    def trace(self, example):
        """Return the traversed attribute/value decisions and final prediction."""
        self._require_fitted()
        _validate_categorical_example(example, self.domains_)
        path, tree = [], self.tree_
        while isinstance(tree, Node):
            value = example[tree.attr_name]
            path.append({"attribute": tree.attr_name, "value": value})
            tree = tree.branches[value]
        return {"path": path, "prediction": tree.target}

    @staticmethod
    def _measure_tree(tree):
        metrics = {"depth": 0, "nodes": 0, "leaves": 0, "positive_rules": 0, "literals": 0}
        pending = [(tree, 0)]
        while pending:
            current, depth = pending.pop()
            metrics["nodes"] += 1
            metrics["depth"] = max(metrics["depth"], depth)
            if isinstance(current, Leaf):
                metrics["leaves"] += 1
                if current.target:
                    metrics["positive_rules"] += 1
                    metrics["literals"] += depth
            else:
                pending.extend((child, depth + 1) for child in current.branches.values())
        return metrics

    def tree_metrics(self):
        """Return edge depth, total nodes, leaves, positive rules, and literals."""
        self._require_fitted()
        return self._measure_tree(self.tree_)


@AlgorithmRegistry.register("gain-ratio")
class GainRatioTreeLearner(CorrectedDecisionTreeLearner):
    """Gain-ratio DTL without an automatic depth limit."""

    use_gain_ratio = True


@AlgorithmRegistry.register("depth-limited")
class DepthLimitedTreeLearner(CorrectedDecisionTreeLearner):
    """Information-gain DTL with a path-local depth limit."""

    use_default_depth = True


@AlgorithmRegistry.register("gain-depth")
class GainDepthTreeLearner(CorrectedDecisionTreeLearner):
    """Gain-ratio DTL with a path-local depth limit."""

    use_gain_ratio = True
    use_default_depth = True


@AlgorithmRegistry.register("pruned-dtl")
class PrunedDecisionTreeLearner(CorrectedDecisionTreeLearner):
    """Information-gain DTL with bottom-up reduced-error validation pruning."""

    use_pruning = True
