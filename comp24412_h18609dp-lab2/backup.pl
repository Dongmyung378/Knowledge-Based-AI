:- [database].

# type1
safe_list([]).
safe_list([X]) :- component(X).
safe_list([X, Y]) :- component(X), component(Y), safe_with(X, Y).
safe_list([X, Y, Z|Rest]) :- component(X), component(Y), safe_with(X, Y), safe_list([X, Z|Rest]), safe_list([Y, Z|Rest]).


# type2
safe_list(D) :- findall(C, component(C), AllComponents), safe_list_helper(D, AllComponents).

safe_list_helper([], _Remaining).
safe_list_helper([X|Rest], Remaining) :- select(X, Remaining, NewRemaining), safe_list_helper(Rest, NewRemaining), check_pairs(X, Rest).

check_pairs(_, []).
check_pairs(X, [Y|Rest]) :- safe_with(X, Y), check_pairs(X, Rest).

# -------------------------------------------------------------------------------------------------------

safe_design(Design) :-  extract_parts(Design, Parts), safe_list(Parts), check_shields(Design).

extract_parts([], []).
extract_parts([part(C)|Rest], [C|Parts]) :- component(C), extract_parts(Rest, Parts).
extract_parts([shield(_)|Rest], Parts) :- extract_parts(Rest, Parts).

check_shields([]).
check_shields([part(C)|Rest]) :- component(C), check_shields(Rest).
check_shields([shield(L)|Rest]) :- L = [part(C)|_], component(C), safe_design(L), check_shields(Rest).

# -------------------------------------------------------------------------------------------------------

count_shields(Design, Count) :- count_shields_helper(Design, 0, Count).
count_shields_helper([], Acc, Acc).
count_shields_helper([part(_)|Rest], Acc, Count) :- count_shields_helper(Rest, Acc, Count).
count_shields_helper([shield(L)|Rest], Acc, Count) :- Acc1 is Acc + 1, count_shields_helper(L, Acc1, Acc2), count_shields_helper(Rest, Acc2, Count).

# -------------------------------------------------------------------------------------------------------

split_list([], [], []).
split_list([H|T], [H|X], Y) :- split_list(T, X, Y).
split_list([H|T], X, [H|Y]) :- split_list(T, X, Y).

# -------------------------------------------------------------------------------------------------------

design_uses(Design, Components) :- 
    Components \= [], 
    forall(member(C, Components), component(C)),
    extract_all_parts(Design, AllParts, Components),
    length(AllParts, PLen),
    length(Components, CLen),
    PLen = CLen.

extract_all_parts([], [], _).
extract_all_parts([part(C)|Rest], [C|Parts], Components) :- 
    Components \= [],
    select(C, Components, Remaining),
    extract_all_parts(Rest, Parts, Remaining).

extract_all_parts([shield(L)|Rest], Parts, Components) :- 
    Components \= [],
    select(C, Components, Comp1),
    L = [part(C)|Tail],
    extract_all_parts(Tail, InnerTail, Comp1),
    append([part(C)], InnerTail, InnerParts),
    extract_all_parts(Rest, RestParts, Comp1),
    append(InnerParts, RestParts, Parts).
