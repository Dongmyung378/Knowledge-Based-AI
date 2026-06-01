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
    # if no positive paths were found, return a disjunction with an empty conjunction
    return Disjunction(conjunctions=conjunctions) if conjunctions else Disjunction(conjunctions=[Conjunction(attribute_confs={})])

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
