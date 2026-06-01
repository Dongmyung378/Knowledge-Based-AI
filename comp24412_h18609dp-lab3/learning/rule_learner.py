import itertools
import re
import math
from contextlib import contextmanager
from dataclasses import dataclass, field, astuple
from typing import List, Generator, Union

from pyswip import Prolog

from learning.util import Algorithm, Examples, Dataset, Example, AlgorithmRegistry

from logging import getLogger

logger = getLogger(__name__)


@dataclass(frozen=True)
class Predicate:
    """
    Object representation of a predicate. Contains `name` which is the name of the predicate and its `arity`.
    """
    name: str
    arity: int

    def __post_init__(self):
        assert self.name[0].islower()


@dataclass(frozen=True)
class Expression:
    """
    Abstract base class representing a valid logical statement.
    """
    ...


@dataclass(frozen=True)
class Literal(Expression):
    """
    Literal: A Predicate with instantiated values for its arguments, which can be either variables or atomic values.

    Converting the literal to string will yield its syntactically valid prolog representation.
    """
    predicate: Predicate = field(hash=True)
    arguments: List[Union['Expression', str]] = field(hash=True)

    def __post_init__(self):
        """
        Make sure that the number of arguments corresponds to the predicate's arity.

        """
        assert len(self.arguments) == self.predicate.arity, \
                f"Number of arguments {len(self.arguments)} not " \
                f"equal to the arity of the predicate {self.predicate.arity}"

    def __repr__(self):
        """
        Prolog representation.

        Returns: A syntactically valid prolog representation of the literal.

        """
        return f"{self.predicate.name}({','.join(str(a) for a in self.arguments)})"

    @classmethod
    def from_str(cls, string):
        """
        Generates a python object from a syntactically valid prolog representation.
        Args:
            string: Prolog representation of the literal.

        Returns: `Literal` object equivalent to the prolog representation.

        """
        predicate = get_predicate(string)
        args = get_args(string)
        return Literal(predicate, args)


def get_predicate(text: str) -> Predicate:
    """
    Returns the name and arity of a predicate from a syntactically valid prolog representation.
    Args:
        text: Text to extract the predicate from.

    Returns: Object of `Predicate` class with its corresponding name and arity.

    """
    text = str(text)
    name = text[:text.find("(")].strip()
    arity = len(re.findall("Variable", text))
    if arity == 0:
        arity = len(re.findall(",", text)) + 1
    return Predicate(name, arity)


@dataclass(frozen=True)
class Disjunction(Expression):
    """
    Represents a disjunction of horn clauses which is initially empty.
    """
    expressions: List['HornClause'] = field(default_factory=list)

    def generalize(self, expression: 'HornClause'):
        """
        Adds another horn clause to the disjunction.
        Args:
            expression: Horn clause to add

        """
        self.expressions.append(expression)

    def __repr__(self):
        """
        Returns a syntactically valid prolog representation of the horn clauses.

        Since there is no real disjunction in prolog, this is just a set of the expressions as separate statements.
        Returns:
            syntactically valid prolog representation of the contained horn clauses.

        """
        return " .\n".join(repr(e) for e in self.expressions) + ' .'


@dataclass(frozen=True)
class Conjunction(Expression):
    """
    Represents a conjunction of literals which is initially empty.
    """
    expressions: List[Expression] = field(default_factory=list)

    def specialize(self, expression: Expression):
        """
        Adds another literal to the conjunction.
        Args:
            expression: literal to add

        """
        self.expressions.append(expression)

    def __repr__(self):
        """
        Returns a syntactically valid prolog representation of the conjunction of the literals.

        Returns:
            syntactically valid prolog representation of the conjunction (comma-separated).

        """
        return " , ".join(repr(e) for e in self.expressions)


@dataclass(frozen=True)
class HornClause(Expression):
    """
    Represents a horn clause with a literal as `head` and a conjunction as `body`.
    """
    head: Expression
    body: Conjunction = field(default_factory=lambda: Conjunction())

    def get_vars(self):
        """
        Returns all variables appearing in the horn clause.

        Returns: All variables in the horn clause, according to prolog syntax, where variables are capitalised.

        """
        return re.findall(r"(?:[^\w])([A-Z]\w*)", str(self))

    def __repr__(self):
        """
        Converts to a syntactically valid prolog representation.

        Returns:
            Syntactically valid prolog representation of a horn clause in the form of
            ``head :- literal_1 , literal_2 , ... , literal_n``
            for all literals in the body.
        """
        return f"{str(self.head)} :- {' , '.join(str(e) for e in self.body.expressions)}"


def get_args(text: str) -> List[str]:
    """
    Returns the arguments of a text that is assumed to be a single literal in prolog representation.

    Args:
        text: Text to extract the arguments from. Must be valid prolog representation of a single literal.

    Returns:
        All arguments that appear in that literal.

    """
    return [x.strip() for x in re.findall(r"\(.*\)", str(text))[0][1:-1].split(",")]

# Register the FOIL algorithm under the name 'foil' for dynamic use in the system
@AlgorithmRegistry.register('foil')
@contextmanager
def FOIL(dataset: Dataset, recursive=False):
    # create an internal FOIL object (the actual implementation is in _FOIL class)
    f = _FOIL(dataset, recursive)
    try:
        # yield the FOIL object to the user (with 'with' statement)
        yield f
    finally:
        # clean up by removing all asserted predicates from the Prolog engine
        f.abolish()


class _FOIL(Algorithm):
    # type hint: this class will use SWI-Prolog through the PySWIP interface
    prolog: Prolog

    def __init__(self, dataset: Dataset, recursive=False):
        # call the base Algorithm constructor with the dataset
        super().__init__(dataset)
        # log creation of the Prolog engine
        logger.info("Creating prolog...")
        # initialize the Prolog engine
        self.prolog = Prolog()
        # store whether recursive rules should be allowed in hypothesis generation
        self.recursive = recursive

        # if a knowledge base file is provided, load it into Prolog
        if dataset.kb:
            logger.debug(f"Consulting {self.dataset.kb}")
            self.prolog.consult(self.dataset.kb)

    def abolish(self):
        # remove all predicates that were defined during learning from the Prolog environment
        # iterate over all predicates used in the dataset
        for p, a in (astuple(a) for a in self.get_predicates()):
            # send an 'abolish' command to Prolog to delete the predicate (name/arity)
            self.prolog.query(f"abolish({p}/{a})")

    def predict(self, example: Example) -> bool:
        # checks whether any learned clause (in the current hypothesis) covers the given example
        # 'covers' means the clause can prove the example using the current knowledge base
        return any(self.covers(clause=c, example=example) for c in self.hypothesis.expressions)
        
    def get_predicates(self) -> List[Predicate]:
        # initialize an empty set to store unique predicates
        predicate_set = set()

        # query the Prolog engine for all predicates that have an associated file
        # this will return a list of dictionaries with keys 'P' (predicate) and 'F' (file path)
        for result in self.prolog.query("predicate_property(P, file(F))."):
            # extract the string representation of the predicate
            pred_str = result["P"]  
            # extract the file path in which the predicate is defined
            file_path = result["F"]

            # check if the predicate comes from the target knowledge base
            if self.dataset.kb in file_path:
                # convert the Prolog predicate string into a Predicate object (with name and arity)
                predicate = get_predicate(pred_str)
                # add it to the set to avoid duplicates
                predicate_set.add(predicate)
        # return the unique predicates as a list
        return list(predicate_set)

    def find_hypothesis(self) -> Disjunction:
        """
        Initiates the FOIL algorithm and returns the final disjunction from the list that is returned by
        `FOIL.foil`.

        Returns: Disjunction of horn clauses that represent the learned target relation.

        """
        # extract positive and negative examples from the dataset
        positive_examples = self.dataset.positive_examples
        negative_examples = self.dataset.negative_examples
        
        # parse the target predicate (head of the Horn clause) from string into a Literal object
        target = Literal.from_str(self.dataset.target)
        # extract all predicates defined in the loaded knowledge base
        predicates = self.get_predicates()
        # ensure that at least one predicate was found
        # if no predicates are found in KB, learning cannot proceed
        assert predicates
        # run the FOIL algorithm to generate a list of Horn clauses covering the target relation
        clauses = self.foil(positive_examples, negative_examples, predicates, target)
        # wrap the learned clauses into a Disjunction object (OR of Horn clauses) and return
        return Disjunction(clauses)

    def foil(self, positive_examples: Examples, negative_examples: Examples, predicates: List[Predicate],
                target: Literal) -> List[HornClause]:
        # initialize the list to store all learned Horn clauses
        clauses = []
        # start with all positive examples as uncovered
        uncovered_pos = positive_examples[:]

        # iterate until all positive examples are covered by some clause
        while uncovered_pos:
            # (optional) if recursive mode is enabled and this is the second clause,
            # allow the target predicate to be used in the body (i.e., allow recursion)
            if self.recursive and target.predicate not in predicates and len(clauses) == 1:
                predicates.append(target.predicate)
            
            # learn one clause that covers as many of the uncovered positive examples as possible
            clause = self.new_clause(uncovered_pos, negative_examples, predicates, target)
            # add the new clause to the list of learned clauses
            clauses.append(clause)
            # assert the clause into Prolog so it can be used during further reasoning (e.g., recursion)
            self.prolog.assertz(repr(clause))
            # remove all positive examples that are now covered by the new clause
            uncovered_pos = [e for e in uncovered_pos if not self.covers(clause, e)]
        # return the complete list of learned clauses
        return clauses

    def covers(self, clause: HornClause, example: Example) -> bool:
        # convert the HornClause object to a Prolog-compatible string
        clause_str = repr(clause)

        # substitute variable names in the clause head with actual values from the example
        # if the argument exists in the example, use the value; otherwise keep the original variable
        substituted_args = [
            example.get(arg, arg) if isinstance(arg, str) else arg for arg in clause.head.arguments
        ]
        # create a new Literal with substituted arguments
        substituted_head = Literal(clause.head.predicate, substituted_args)
        # convert the substituted head literal into a Prolog query string
        query_str = repr(substituted_head)
        # assert the clause into Prolog so we can query it
        self.prolog.assertz(clause_str)
        try:
            # run the query and check whether it succeeds at least once
            return next(self.prolog.query(query_str), None) is not None
        except Exception:
            # if an error occurs during query execution, return False
            return False
        finally:
            # always retract the clause after the query to clean up the Prolog environment
            self.prolog.retract(clause_str)


    def new_clause(self, positive_examples: Examples, negative_examples: Examples, predicates: List[Predicate],
                    target: Literal) -> HornClause:
        # create an initial clause with the given target as the head and an empty body
        clause = HornClause(head=target, body=Conjunction([]))
        # copy the examples so we can manipulate them during learning
        pos = positive_examples[:]
        neg = negative_examples[:]
        
        # continue specializing the clause until all negative examples are ruled out
        while neg:
            # generate all possible candidate literals for specialization            
            candidates = list(self.generate_candidates(clause, predicates))

            filtered_candidates = []
            # filter candidates based on FOIL constraints and information gain
            for lit in candidates:
                # if recursion is not allowed, skip using the target predicate in body
                if not self.recursive and lit.predicate.name == target.predicate.name:
                    continue
                
                # if recursion is allowed, enforce that the first argument matches the head's first argument
                # this ensures recursion proceeds in a forward direction (e.g., grandparent(X,Y) :- parent(X,Z), grandparent(Z,Y))
                if (
                    self.recursive
                    # only applies to the first literal
                    and clause.body.expressions == []
                    and lit.arguments[0] != target.arguments[0]
                ):
                    continue 
                # compute FOIL information gain for this literal
                gain = self.foil_information_gain(lit, pos, neg)
                # discard literals that don’t improve classification
                if gain <= 0:
                    continue
                # keep the candidate and its gain
                filtered_candidates.append((lit, gain))
            
            # if no good candidate literals remain, stop refining
            if not filtered_candidates:
                break
            # choose the literal with the highest gain
            best_literal, _ = max(filtered_candidates, key=lambda x: x[1])
            # add the best literal to the clause body (i.e., specialize the clause)
            clause.body.expressions.append(best_literal)
            
            # extend both positive and negative examples by applying the new literal    
            pos = list(itertools.chain.from_iterable(
                self.extend_example(e, best_literal) for e in pos))
            neg = list(itertools.chain.from_iterable(
                self.extend_example(e, best_literal) for e in neg))
        # return the fully constructed Horn clause
        return clause

    def get_next_literal(self, candidates: List[Expression], pos_ex: Examples, neg_ex: Examples) -> Expression:
        # Not implemented: this method is unused in current FOIL logic
        """
        Returns the next literal with the highest information gain as computed from a given dataset of positive and
        negative examples.
        Args:
            candidates: Candidates to choose the one with the highest information gain from.
            pos_ex: Positive examples of the dataset to infer the information gain from.
            neg_ex: Negative examples of the dataset to infer the information gain from.

        Returns:
            the next literal with the highest information gain as computed
            from a given dataset of positive and negative examples.
        """

    def foil_information_gain(self, candidate: Expression, pos_ex: Examples, neg_ex: Examples) -> float:
        # number of original positive and negative examples
        p0 = len(pos_ex)
        n0 = len(neg_ex)
        
        # extend all positive examples with the new literal
        pos_ext = []
        for e in pos_ex:
            pos_ext.extend(self.extend_example(e, candidate))
        # extend all negative examples with the new literal
        neg_ext = []
        for e in neg_ex:
            neg_ext.extend(self.extend_example(e, candidate))
        
        # filter out extended positive examples that still represent original positives
        p1_ex = [ex for ex in pos_ext if any(is_represented_by(e, [ex]) for e in pos_ex)]
        # same for negative examples
        n1_ex = [ex for ex in neg_ext if any(is_represented_by(e, [ex]) for e in neg_ex)]
        
        # number of retained positive and negative examples after applying the candidate
        p1 = len(p1_ex)
        n1 = len(n1_ex)

        # number of original positive examples covered by any of the extended positives
        t = sum(1 for e in pos_ex if any(is_represented_by(e, [ex]) for ex in p1_ex))

        # edge cases: prevent divide-by-zero or meaningless log2
        if p1 + n1 == 0 or p0 + n0 == 0 or p1 == 0 or p0 == 0:
            return 0.0
        
        # FOIL information gain formula
        return t * (math.log2(p1 / (p1 + n1)) - math.log2(p0 / (p0 + n0)))

    def generate_candidates(self, clause: HornClause, predicates: List[Predicate]) -> Generator[Expression, None, None]:
        # Generate candidate literals to specialize the current clause body.
        # These candidates are created using known variables and optionally new ones.

        # Extract all distinct variables used so far in the clause
        existing_vars = list(set(clause.get_vars()))
        
        for predicate in predicates:
            # skip recursive use of the target predicate unless explicitly allowed
            if not self.recursive and predicate.name == clause.head.predicate.name:
                continue
            
            # arity defines how many arguments the predicate takes (used to generate valid literals)
            arity = predicate.arity
            
            # generate all possible literals using existing variables only
            for args in itertools.product(existing_vars, repeat=arity):
                # yield a new candidate literal with the current argument combination
                yield Literal(predicate, list(args))

            # Next, generate literals that introduce one new variable
            # This helps the algorithm explore more general or novel combinations
            new_var = self.unique_var()
            for i in range(arity):
                for var in existing_vars:
                    # Create an argument list where one argument is the new variable,
                    # and the others are existing ones
                    args = [new_var if j == i else var for j in range(arity)]
                    # yield a candidate literal introducing a new variable
                    yield Literal(predicate, args)

    def extend_example(self, example: Example, new_expr: Expression) -> Generator[Example, None, None]:
        # Apply the literal to the example and return all matching extensions via Prolog

        # Bind known values from the example to the literal's arguments
        bound_args = [
            example.get(arg, arg) if isinstance(arg, str) else arg
            for arg in new_expr.arguments
        ]
        
        # Create a new Literal with updated arguments that may include constants
        bound_literal = Literal(new_expr.predicate, bound_args)
        # Convert the Literal into a Prolog-compatible string for querying
        query_str = repr(bound_literal)

        # Execute the Prolog query to find all possible variable bindings that satisfy the literal
        for result in self.prolog.query(query_str):
            # Create a new extended example by copying the current one
            extended = example.copy()
            # Add the variable bindings returned by Prolog
            extended.update(result)
            # Yield the extended example to the caller
            yield extended

    def unique_var(self) -> str:
        # This function generates a unique variable name to be used when constructing new literals.
        # In FOIL, each new variable introduced in a clause body must have a distinct name
        # to avoid ambiguity and to represent logical generalization properly.

        # Initialize the variable counter if this is the first call
        if not hasattr(self, "_var_counter"):
            self._var_counter = 0

        # Generate a new variable name like V_0, V_1, V_2, ...
        # These names follow Prolog convention for variables (starting with uppercase)
        var_name = f"V_{self._var_counter}"
        # Increment the counter for the next variable to be unique
        self._var_counter += 1
        # Return the generated variable name
        return var_name

def is_represented_by(example: Example, examples: Examples) -> bool:
    # This function checks whether the given `example` is "represented" by
    # (i.e., logically entailed by or included in) any of the examples in `examples`.
    
    # In FOIL, this is used to determine whether an extended example still corresponds
    # to one of the original examples (e.g., after applying a candidate literal).
    for e in examples:
        # For `example` to be represented by `e`, all key-value pairs in `example`
        # must be present in `e` with the same values.
        # This implies that `e` is at least as specific as `example`.
        if all(k in e and e[k] == v for k, v in example.items()):
            # Found a matching example that represents `example`
            return True
    # If no match is found, return False
    return False
