import itertools
import re
import math
import time
from contextlib import closing, contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Generator, Union

from pyswip import Prolog

from learning.util import Algorithm, Examples, Dataset, Example, AlgorithmRegistry

from logging import getLogger

logger = getLogger(__name__)


class FOILLearningError(RuntimeError):
    """The supported greedy hypothesis search cannot separate the examples."""


class FOILBudgetExceeded(FOILLearningError):
    """A declared time or search budget was exhausted, without a valid result."""


class FOILQueryError(FOILLearningError):
    """A Prolog query failed instead of returning a logical false answer."""


class FOILCleanupError(FOILLearningError):
    """One or more cleanup operations failed after all were attempted."""


_VARIABLE = re.compile(r"[A-Z][A-Za-z0-9_]*\Z")
_ATOM = re.compile(r"[a-z][A-Za-z0-9_]*\Z")


def _ground_term(value):
    """Serialize the intentionally small supported example-value schema."""
    if isinstance(value, str) and _ATOM.fullmatch(value):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, int) or math.isfinite(value):
            return str(value)
    raise ValueError("Example values must be unquoted lowercase Prolog atoms or finite numbers; "
                     f"received {value!r}.")


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
        if self.predicate.arity == 0:
            return self.predicate.name
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
    if '(' not in text:
        return Predicate(text.strip(), 0)
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
        return f"{str(self.head)} :- {' , '.join(str(e) for e in self.body.expressions) or 'true'}"


def get_args(text: str) -> List[str]:
    """
    Returns the arguments of a text that is assumed to be a single literal in prolog representation.

    Args:
        text: Text to extract the arguments from. Must be valid prolog representation of a single literal.

    Returns:
        All arguments that appear in that literal.

    """
    return [x.strip() for x in re.findall(r"\(.*\)", str(text))[0][1:-1].split(",")]

def validate_foil_dataset(dataset):
    """Validate the supported flat relation schema without consulting Prolog."""
    return _FOIL._validate_dataset(dataset)


# Register the FOIL algorithm under the name 'foil' for dynamic use in the system
@AlgorithmRegistry.register('foil')
@contextmanager
def FOIL(dataset: Dataset, recursive=False, *, max_seconds=60.0,
         query_timeout_seconds=2.0, max_candidate_evaluations=20000,
         max_prolog_queries=1000000, max_clauses=128, max_literals_per_clause=16, lookahead=0):
    # create an internal FOIL object (the actual implementation is in _FOIL class)
    f = _FOIL(dataset, recursive, max_seconds=max_seconds,
              query_timeout_seconds=query_timeout_seconds,
              max_candidate_evaluations=max_candidate_evaluations,
              max_prolog_queries=max_prolog_queries, max_clauses=max_clauses,
              max_literals_per_clause=max_literals_per_clause, lookahead=lookahead)
    body_error = None
    try:
        # yield the FOIL object to the user (with 'with' statement)
        yield f
    except BaseException as exc:
        body_error = exc
        raise
    finally:
        # clean up by removing all asserted predicates from the Prolog engine
        try:
            f.abolish()
        except Exception as cleanup_error:
            if body_error is None:
                raise
            if hasattr(body_error, "add_note"):
                body_error.add_note(f"FOIL cleanup also failed: {cleanup_error}")
            logger.error("FOIL cleanup failed while preserving the original exception: %s", cleanup_error)


class _FOIL(Algorithm):
    # type hint: this class will use SWI-Prolog through the PySWIP interface
    prolog: Prolog

    def __init__(self, dataset: Dataset, recursive=False, *, max_seconds=60.0,
                 query_timeout_seconds=2.0, max_candidate_evaluations=20000,
                 max_prolog_queries=1000000, max_clauses=128, max_literals_per_clause=16, lookahead=0):
        # call the base Algorithm constructor with the dataset
        super().__init__(dataset)
        self._target_literal = self._validate_dataset(dataset)
        self.max_seconds = self._positive_budget("max_seconds", max_seconds)
        self.query_timeout_seconds = self._positive_budget("query_timeout_seconds", query_timeout_seconds)
        if isinstance(lookahead, bool) or lookahead not in (0, 2):
            raise ValueError("lookahead must be 0 (original greedy search) or 2 (bounded zero-gain bridge search).")
        self.lookahead = lookahead
        self.search_trace_ = []
        for name, value in (("max_candidate_evaluations", max_candidate_evaluations),
                            ("max_prolog_queries", max_prolog_queries),
                            ("max_clauses", max_clauses),
                            ("max_literals_per_clause", max_literals_per_clause)):
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ValueError(f"{name} must be a positive integer.")
            setattr(self, name, value)
        self.stats_ = {"candidate_evaluations": 0, "prolog_queries": 0,
                       "clauses": 0, "literals": 0, "fit_seconds": 0.0}
        self._deadline = None
        self._closed = False
        self._target_initialized = False
        self._owned_predicates = []
        # log creation of the Prolog engine
        logger.info("Creating prolog...")
        # initialize the Prolog engine
        self.prolog = Prolog()
        # Collect a finite answer batch under SWI's standard time-limit helper.
        # Its alarm is removed before any answer is yielded back to Python.
        # The private helper contains no dataset facts or learned clauses.
        if not list(self.prolog.query("current_predicate(foil_runtime:bounded_query/2)")):
            self.prolog.assertz(
                "foil_runtime:(bounded_query(Seconds, Goal) :- "
                "term_variables(Goal, Vars), "
                "call_with_time_limit(Seconds, findall(Vars, limit(100001, Goal), Answers)), "
                "length(Answers, Count), (Count=<100000 -> member(Vars, Answers); "
                "throw(error(resource_error(foil_query_solutions), _))))")
        if not list(self.prolog.query("current_predicate(foil_runtime:clause_covers/3)")):
            # A database clause reference is an opaque SWI resource. Keep it
            # local to Prolog instead of returning a soon-erased reference in
            # PySwip's Python result bindings.
            self.prolog.assertz(
                "foil_runtime:(clause_covers(Clause, Goal, Reset) :- "
                "setup_call_cleanup((assertz(user:Clause, Ref), call(Reset)), "
                "once(Goal), (erase(Ref), call(Reset))))")
        # store whether recursive rules should be allowed in hypothesis generation
        self.recursive = recursive
        self.kb_path = Path(dataset.kb).resolve() if dataset.kb else None
        self._prolog_kb_path = None

        self._target = self._target_literal.predicate
        try:
            escaped_path = self.kb_path.as_posix().replace("'", "''")
            # Resolve the canonical source identity before consulting so that
            # even a partially failed consult can be unloaded on initialization.
            self._prolog_kb_path = self._query_all(
                f"absolute_file_name('{escaped_path}', Canonical)")[0]['Canonical']
            self._query_all(f"consult('{escaped_path}')")
            self._owned_predicates = self.get_predicates()
            if self._target in self._owned_predicates:
                raise ValueError("The target predicate must not already be defined in the knowledge base.")
        except BaseException as exc:
            try:
                self.abolish()
            except Exception as cleanup_error:
                if hasattr(exc, "add_note"):
                    exc.add_note(f"Initialization cleanup also failed: {cleanup_error}")
            raise

    @staticmethod
    def _positive_budget(name, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be a positive finite number.")
        return float(value)

    def _ensure_target_runtime(self):
        # Merely inspecting candidates or a KB does not need a target table.
        # Declare it only when a real proof/training operation will use it.
        if self.recursive and not self._target_initialized:
            indicator = f"{self._target.name}/{self._target.arity}"
            self._query_all(f"dynamic({indicator})")
            self._query_all(f"table({indicator})")
            self._target_initialized = True

    @staticmethod
    def _validate_dataset(dataset):
        if not isinstance(dataset.target, str):
            raise ValueError("FOIL requires a target such as reachable(X,Y).")
        match = re.fullmatch(r"\s*([a-z][A-Za-z0-9_]*)\(([^()]*)\)\s*\.?\s*", dataset.target)
        if not match:
            raise ValueError("FOIL target must be a flat predicate with named variables, such as reachable(X,Y).")
        variables = [part.strip() for part in match.group(2).split(',')]
        if not variables or any(not _VARIABLE.fullmatch(variable) for variable in variables) or len(set(variables)) != len(variables):
            raise ValueError("Target arguments must be distinct named uppercase variables.")
        if not dataset.kb or not Path(dataset.kb).is_file():
            raise ValueError("FOIL requires an existing Prolog knowledge-base file.")
        expected_keys = set(variables)
        for example in dataset.examples:
            if not isinstance(example, dict) or set(example) != expected_keys:
                raise ValueError(f"Each example must contain exactly the target variables {variables}.")
            for value in example.values():
                _ground_term(value)
        positive = dataset.positive_examples
        negative = dataset.negative_examples
        if positive is not None and negative is not None:
            positive_keys = {tuple(example[name] for name in variables) for example in positive}
            negative_keys = {tuple(example[name] for name in variables) for example in negative}
            if positive_keys & negative_keys:
                raise ValueError("Positive and negative examples contain contradictory bindings.")
        return Literal(Predicate(match.group(1), len(variables)), variables)

    def _check_deadline(self):
        if self._closed:
            raise FOILLearningError("This FOIL context has closed; prediction and training must stay inside it.")
        if self._deadline is not None and time.perf_counter() >= self._deadline:
            raise FOILBudgetExceeded(f"FOIL exceeded max_seconds={self.max_seconds:g}.")

    def _query(self, goal):
        self._check_deadline()
        if self.stats_["prolog_queries"] >= self.max_prolog_queries:
            raise FOILBudgetExceeded(f"FOIL exceeded max_prolog_queries={self.max_prolog_queries}.")
        self.stats_["prolog_queries"] += 1
        limit = self.query_timeout_seconds
        if self._deadline is not None:
            limit = min(limit, max(0.000001, self._deadline - time.perf_counter()))
        goal = goal.rstrip().rstrip('.')
        try:
            # call_with_time_limit/2 commits to the first solution; collecting
            # the bounded answer batch inside it preserves every substitution.
            timed_goal = f"foil_runtime:bounded_query({limit!r}, user:({goal}))"
            with closing(self.prolog.query(timed_goal)) as query:
                for result in query:
                    self._check_deadline()
                    yield result
        except FOILLearningError:
            raise
        except Exception as exc:
            if "time_limit_exceeded" in str(exc):
                raise FOILBudgetExceeded(f"Prolog query exceeded its {limit:g}-second limit.") from exc
            if "foil_query_solutions" in str(exc):
                raise FOILBudgetExceeded("Prolog query exceeded its 100000-answer limit.") from exc
            raise FOILQueryError(f"Prolog query failed: {goal[:160]}: {exc}") from exc

    def _query_all(self, goal):
        return list(self._query(goal))

    def _query_once(self, goal):
        with closing(self._query(goal)) as query:
            return next(query, None) is not None

    def fit(self):
        self._check_deadline()
        if self.dataset.positive_examples is None or self.dataset.negative_examples is None:
            raise ValueError("FOIL fit requires separate positive_examples and negative_examples.")
        if getattr(self, "_fit_attempted", False):
            raise FOILLearningError("Create a new FOIL context for each fit; repeated fitting is unsupported.")
        self._fit_attempted = True
        self.stats_ = {"candidate_evaluations": 0, "prolog_queries": 0,
                       "clauses": 0, "literals": 0, "fit_seconds": 0.0}
        self._var_counter = 0
        start = time.perf_counter()
        self._deadline = start + self.max_seconds
        try:
            super().fit()
        except BaseException as exc:
            # A failed fit must not leave a partially learned target available
            # as though it were a successful classifier, even if its caller
            # catches the exception before leaving the context.
            try:
                arguments = ','.join('_' for _ in range(self._target.arity))
                goals = [f"retractall({self._target.name}({arguments}))"]
                if self.recursive:
                    goals.append(f"abolish_table_subgoals({self._target.name}({arguments}))")
                with closing(self.prolog.query(
                        f"call_with_time_limit({self.query_timeout_seconds!r}, ({', '.join(goals)}))")) as query:
                    list(query)
            except Exception as cleanup_error:
                if hasattr(exc, "add_note"):
                    exc.add_note(f"Failed-fit cleanup also failed: {cleanup_error}")
            raise
        finally:
            self.stats_["fit_seconds"] = time.perf_counter() - start
            self._deadline = None

    def _invalidate_target_table(self):
        # Ordinary tables do not track asserted/retracted clauses. Clear only
        # this learner's target tables after changing its hypothesis.
        if self.recursive and self._target_initialized:
            arguments = ','.join('_' for _ in range(self._target.arity))
            self._query_all(f"abolish_table_subgoals({self._target.name}({arguments}))")

    def abolish(self):
        # PySwip queries are lazy, so consume each cleanup query to make sure
        # SWI-Prolog actually removes the predicate before the next learner is
        # created in the same Python process.
        # Learned clauses are asserted dynamically and therefore have no
        # source-file property. Add the target explicitly so those clauses do
        # not leak into the next test or training run.
        if self._closed:
            return
        errors = []
        # Cleanup deliberately bypasses exhausted fit/query budgets. Every
        # operation has its own finite timeout, and later operations are still
        # attempted if an earlier operation fails.
        def cleanup(goal):
            try:
                with closing(self.prolog.query(
                        f"call_with_time_limit({self.query_timeout_seconds!r}, ({goal}))")) as query:
                    list(query)
            except Exception as exc:
                errors.append(f"{goal}: {exc}")

        predicates = set(self._owned_predicates)
        predicates.add(self._target)
        if self.recursive and self._target_initialized:
            arguments = ','.join('_' for _ in range(self._target.arity))
            cleanup(f"abolish_table_subgoals({self._target.name}({arguments}))")
            cleanup(f"untable({self._target.name}/{self._target.arity})")
        for predicate in sorted(predicates, key=lambda item: (item.name, item.arity)):
            cleanup(f"abolish({predicate.name}/{predicate.arity})")
        if self._prolog_kb_path:
            escaped_path = self._prolog_kb_path.replace("'", "''")
            cleanup(f"unload_file('{escaped_path}')")
        self._closed = True
        if errors:
            raise FOILCleanupError("FOIL cleanup could not complete all operations: " + "; ".join(errors))

    def predict(self, example: Example) -> bool:
        # checks whether any learned clause (in the current hypothesis) covers the given example
        # 'covers' means the clause can prove the example using the current knowledge base
        if not hasattr(self, "hypothesis"):
            raise FOILLearningError("Call fit before prediction.")
        return self._query_once(self._bound_target(example))

    def _bound_target(self, example):
        variables = self._target_literal.arguments
        if not isinstance(example, dict) or set(example) != set(variables):
            raise ValueError(f"Prediction requires exactly the target variables {variables}.")
        return f"{self._target.name}({','.join(_ground_term(example[name]) for name in variables)})"

    def predict_with_trace(self, example):
        """Return matching clause bodies, not an exhaustive Prolog proof tree."""
        prediction = self.predict(example)
        matching = []
        if prediction:
            bound_target = self._bound_target(example)
            for index, clause in enumerate(self.hypothesis.expressions):
                body = repr(clause.body) or "true"
                if self._query_once(f"({clause.head} = {bound_target}), ({body})"):
                    matching.append({"clause_index": index, "clause": repr(clause),
                                     "bindings": dict(example)})
        return {"prediction": prediction, "matching_clauses": matching,
                "scope": "Matching learned clause bodies; not a complete Prolog proof tree."}
        
    def get_predicates(self) -> List[Predicate]:
        # initialize an empty set to store unique predicates
        predicate_set = set()

        # query the Prolog engine for all predicates that have an associated file
        # this will return a list of dictionaries with keys 'P' (predicate) and 'F' (file path)
        for result in self._query("predicate_property(P, file(F))"):
            # extract the string representation of the predicate
            pred_str = result["P"]  
            # extract the file path in which the predicate is defined
            file_path = result["F"]

            # check if the predicate comes from the target knowledge base
            if Path(str(file_path)).resolve() == self.kb_path:
                # convert the Prolog predicate string into a Predicate object (with name and arity)
                predicate = get_predicate(pred_str)
                # add it to the set to avoid duplicates
                predicate_set.add(predicate)
        # return the unique predicates as a list
        return sorted(predicate_set, key=lambda predicate: (predicate.name, predicate.arity))

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
        if not predicates:
            raise FOILLearningError("The knowledge base contains no supported source predicates.")
        # run the FOIL algorithm to generate a list of Horn clauses covering the target relation
        clauses = self.foil(positive_examples, negative_examples, predicates, target)
        # Adding a recursive clause changes the closure of every target query.
        # Validate the final asserted hypothesis, not just its local extension
        # counts, before exposing it as a successfully fitted classifier.
        if any(not self._query_once(self._bound_target(example)) for example in positive_examples):
            raise FOILLearningError("The final learned hypothesis does not cover every training positive.")
        if any(self._query_once(self._bound_target(example)) for example in negative_examples):
            raise FOILLearningError("The final learned recursive closure still covers training negatives.")
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
            self._check_deadline()
            if len(clauses) >= self.max_clauses:
                raise FOILBudgetExceeded(f"FOIL exceeded max_clauses={self.max_clauses}.")
            # (optional) if recursive mode is enabled and this is the second clause,
            # allow the target predicate to be used in the body (i.e., allow recursion)
            if self.recursive and target.predicate not in predicates and len(clauses) == 1:
                predicates.append(target.predicate)
            
            # learn one clause that covers as many of the uncovered positive examples as possible
            clause = self.new_clause(uncovered_pos, negative_examples, predicates, target)
            remaining = [example for example in uncovered_pos if not self.covers(clause, example)]
            if len(remaining) >= len(uncovered_pos):
                raise FOILLearningError("A learned clause covered no remaining positive examples; search made no progress.")
            # add the new clause to the list of learned clauses
            clauses.append(clause)
            # assert the clause into Prolog so it can be used during further reasoning (e.g., recursion)
            self._query_all(f"assertz(({clause!r}))")
            self._invalidate_target_table()
            # remove all positive examples that are now covered by the new clause
            uncovered_pos = remaining
            self.stats_["clauses"] = len(clauses)
            self.stats_["literals"] = sum(len(item.body.expressions) for item in clauses)
        # return the complete list of learned clauses
        return clauses

    def covers(self, clause: HornClause, example: Example) -> bool:
        self._ensure_target_runtime()
        # convert the HornClause object to a Prolog-compatible string
        clause_str = repr(clause)

        # substitute variable names in the clause head with actual values from the example
        # if the argument exists in the example, use the value; otherwise keep the original variable
        substituted_args = [_ground_term(example[arg]) if arg in example else arg
                            for arg in clause.head.arguments]
        # create a new Literal with substituted arguments
        substituted_head = Literal(clause.head.predicate, substituted_args)
        # convert the substituted head literal into a Prolog query string
        query_str = repr(substituted_head)
        reset = "true"
        if self.recursive:
            arguments = ','.join('_' for _ in range(self._target.arity))
            reset = f"abolish_table_subgoals({self._target.name}({arguments}))"
        # SWI cleanup executes even when the proof raises or its time limit is
        # interrupted. Erase the exact temporary clause reference, preserving
        # any identical permanent clause. Query errors are never logical False.
        return self._query_once(
            f"foil_runtime:clause_covers(({clause_str}), user:({query_str}), user:({reset}))")


    def new_clause(self, positive_examples: Examples, negative_examples: Examples, predicates: List[Predicate],
                    target: Literal) -> HornClause:
        # create an initial clause with the given target as the head and an empty body
        clause = HornClause(head=target, body=Conjunction([]))
        # copy the examples so we can manipulate them during learning
        pos = positive_examples[:]
        neg = negative_examples[:]
        
        # continue specializing the clause until all negative examples are ruled out
        while neg:
            self._check_deadline()
            if len(clause.body.expressions) >= self.max_literals_per_clause:
                raise FOILBudgetExceeded(
                    f"FOIL exceeded max_literals_per_clause={self.max_literals_per_clause} "
                    f"while {len(neg)} negative bindings remained.")
            best_literal = None
            best_gain = 0.0
            zero_gain_candidates = []
            # filter candidates based on FOIL constraints and information gain
            for lit in self.generate_candidates(clause, predicates):
                # if recursion is not allowed, skip using the target predicate in body
                if not self.recursive and lit.predicate.name == target.predicate.name:
                    continue
                
                # if recursion is allowed, enforce that the first argument matches the head's first argument
                # this ensures recursion proceeds in a forward direction (e.g., grandparent(X,Y) :- parent(X,Z), grandparent(Z,Y))
                if (
                    self.recursive
                    # only applies to the first literal
                    and clause.body.expressions == []
                    and lit.arguments
                    and lit.arguments[0] != target.arguments[0]
                ):
                    continue 
                # compute FOIL information gain for this literal
                if lit in clause.body.expressions:
                    continue
                if self.stats_["candidate_evaluations"] >= self.max_candidate_evaluations:
                    raise FOILBudgetExceeded(
                        f"FOIL exceeded max_candidate_evaluations={self.max_candidate_evaluations}.")
                self.stats_["candidate_evaluations"] += 1
                gain = self.foil_information_gain(lit, pos, neg)
                # discard literals that don’t improve classification
                if gain <= 0:
                    if abs(gain) <= 1e-12:
                        zero_gain_candidates.append(lit)
                    continue
                # keep the candidate and its gain
                if gain > best_gain:
                    best_literal, best_gain = lit, gain
            
            # if no good candidate literals remain, stop refining
            selected_literals = [best_literal] if best_literal is not None else []
            if not selected_literals and self.lookahead == 2:
                if len(clause.body.expressions) + 2 > self.max_literals_per_clause:
                    raise FOILBudgetExceeded("Two-literal lookahead would exceed max_literals_per_clause.")
                selected_literals = self._lookahead_pair(clause, zero_gain_candidates, predicates, pos, neg)
            if not selected_literals:
                raise FOILLearningError(
                    "No positive-gain candidate can separate the remaining examples "
                    f"({len(pos)} positive and {len(neg)} negative bindings). "
                    "The greedy learner did not produce a valid clause within its hypothesis language.")
            # choose the literal with the highest gain
            # add the best literal to the clause body (i.e., specialize the clause)
            for selected_literal in selected_literals:
                clause.body.expressions.append(selected_literal)
                pos = list(itertools.chain.from_iterable(
                    self.extend_example(e, selected_literal) for e in pos))
                neg = list(itertools.chain.from_iterable(
                    self.extend_example(e, selected_literal) for e in neg))
            if not pos:
                raise FOILLearningError("Clause specialization removed every positive binding.")
        # return the fully constructed Horn clause
        return clause

    def _lookahead_pair(self, clause, first_candidates, predicates, pos, neg):
        """Search two literals only after ordinary positive-gain search stalls.

        The first literal must have zero gain and preserve a positive binding.
        The pair uses the original example origins when computing FOIL gain.
        All candidate, query, literal, and wall-time budgets remain in force.
        """
        best_pair, best_gain = [], 0.0
        for first in first_candidates:
            self._check_deadline()
            extended_pos = [(index, extension) for index, example in enumerate(pos)
                            for extension in self.extend_example(example, first)]
            if not extended_pos:
                continue
            extended_neg = [extension for example in neg for extension in self.extend_example(example, first)]
            trial = HornClause(clause.head, Conjunction(list(clause.body.expressions) + [first]))
            for second in self.generate_candidates(trial, predicates):
                if second in trial.body.expressions:
                    continue
                if self.stats_["candidate_evaluations"] >= self.max_candidate_evaluations:
                    raise FOILBudgetExceeded(
                        f"FOIL exceeded max_candidate_evaluations={self.max_candidate_evaluations} during lookahead.")
                self.stats_["candidate_evaluations"] += 1
                p1, origins = 0, set()
                for origin, example in extended_pos:
                    count = sum(1 for _ in self.extend_example(example, second))
                    p1 += count
                    if count:
                        origins.add(origin)
                n1 = sum(1 for example in extended_neg for _ in self.extend_example(example, second))
                gain = (len(origins) * (math.log2(p1 / (p1 + n1)) - math.log2(len(pos) / (len(pos) + len(neg))))
                        if p1 else 0.0)
                if gain > best_gain:
                    best_pair, best_gain = [first, second], gain
        if best_pair:
            self.search_trace_.append({"event": "zero_gain_bridge", "literals": [repr(item) for item in best_pair],
                                       "joint_foil_gain": best_gain})
        return best_pair

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
        
        # extend_example preserves every original binding. Count extensions
        # while retaining their originating example, instead of rediscovering
        # that relation with quadratic pairwise scans of the whole dataset.
        p1 = 0
        t = 0
        for example in pos_ex:
            count = sum(1 for _ in self.extend_example(example, candidate))
            p1 += count
            t += bool(count)
        n1 = sum(1 for example in neg_ex for _ in self.extend_example(example, candidate))

        # edge cases: prevent divide-by-zero or meaningless log2
        if p1 + n1 == 0 or p0 + n0 == 0 or p1 == 0 or p0 == 0:
            return 0.0
        
        # FOIL information gain formula
        return t * (math.log2(p1 / (p1 + n1)) - math.log2(p0 / (p0 + n0)))

    def generate_candidates(self, clause: HornClause, predicates: List[Predicate]) -> Generator[Expression, None, None]:
        # Generate candidate literals to specialize the current clause body.
        # These candidates are created using known variables and optionally new ones.

        # Extract all distinct variables used so far in the clause
        # Stable tie-breaking must not depend on Python's randomized set order.
        existing_vars = list(dict.fromkeys(clause.get_vars()))
        
        for predicate in predicates:
            # skip recursive use of the target predicate unless explicitly allowed
            if not self.recursive and predicate.name == clause.head.predicate.name:
                continue
            
            # arity defines how many arguments the predicate takes (used to generate valid literals)
            arity = predicate.arity
            
            # generate all possible literals using existing variables only
            for args in itertools.product(existing_vars, repeat=arity):
                self._check_deadline()
                # yield a new candidate literal with the current argument combination
                yield Literal(predicate, list(args))

            # Next, generate literals that introduce one new variable
            # This helps the algorithm explore more general or novel combinations
            new_var = self.unique_var()
            while new_var in existing_vars:
                new_var = self.unique_var()
            for i in range(arity):
                for old_args in itertools.product(existing_vars, repeat=max(0, arity - 1)):
                    self._check_deadline()
                    # Create an argument list where one argument is the new variable,
                    # and the others are existing ones
                    arguments = iter(old_args)
                    args = [new_var if j == i else next(arguments) for j in range(arity)]
                    # yield a candidate literal introducing a new variable
                    yield Literal(predicate, args)

    def extend_example(self, example: Example, new_expr: Expression) -> Generator[Example, None, None]:
        # Apply the literal to the example and return all matching extensions via Prolog

        # Bind known values from the example to the literal's arguments
        bound_args = [
            _ground_term(example[arg]) if isinstance(arg, str) and arg in example else arg
            for arg in new_expr.arguments
        ]
        
        # Create a new Literal with updated arguments that may include constants
        bound_literal = Literal(new_expr.predicate, bound_args)
        # Convert the Literal into a Prolog-compatible string for querying
        query_str = repr(bound_literal)

        # Execute the Prolog query to find all possible variable bindings that satisfy the literal
        for result in self._query(query_str):
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
