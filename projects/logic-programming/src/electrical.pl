% Copy code from database.

component(antenna).
component(transponder).
component(radar).
component(spectrometer).
component(imu).
component(camera).
component(cpu).
component(ram).

safe_with(radar,cpu).
safe_with(cpu,radar).
safe_with(radar,imu).
safe_with(imu,radar).
safe_with(imu,camera).
safe_with(camera,imu).
safe_with(imu,cpu).
safe_with(cpu,imu).
safe_with(imu,ram).
safe_with(ram,imu).
safe_with(ram,cpu).
safe_with(cpu,ram).
safe_with(ram,camera).
safe_with(camera,ram).
safe_with(camera,transponder).
safe_with(transponder,camera).
safe_with(camera,cpu).
safe_with(cpu,camera).
safe_with(cpu,spectrometer).
safe_with(spectrometer,cpu).
safe_with(cpu,antenna).
safe_with(antenna,cpu).
safe_with(antenna,spectrometer).
safe_with(spectrometer,antenna).
safe_with(antenna,transponder).
safe_with(transponder,antenna).
safe_with(transponder,spectrometer).
safe_with(spectrometer,transponder).

% safe_list/1: Checks if all components in the list are safe with each other.

safe_list([]).
safe_list([X]) :- component(X).
safe_list([X, Y]) :- component(X), component(Y), safe_with(X, Y).
safe_list([X, Y, Z|Rest]) :- component(X), component(Y), safe_with(X, Y), safe_list([X, Z|Rest]), safe_list([Y, Z|Rest]).

% safe_design/1: Checks if the design is safe.

safe_design(Design) :-  extract_parts(Design, Parts), safe_list(Parts).

% extract_parts/2: Extracts all parts from the design.

extract_parts([], []).
extract_parts([part(C)|Rest], [C|Parts]) :- component(C), extract_parts(Rest, Parts).
extract_parts([shield(L)|Rest], Parts) :- L = [part(C)|_], component(C), safe_design(L), extract_parts(Rest, Parts).

% count_shields/2: Counts the number of shields used in the design.

count_shields(Design, Count) :- count_shields_helper(Design, 0, Count).

% count_shields_helper/3: Helper function for counting shields.

count_shields_helper([], Acc, Acc).
count_shields_helper([part(_)|Rest], Acc, Count) :- count_shields_helper(Rest, Acc, Count).
count_shields_helper([shield(L)|Rest], Acc, Count) :- Acc1 is Acc + 1, count_shields_helper(L, Acc1, Acc2), count_shields_helper(Rest, Acc2, Count).

% split_list/3: Splits a list into two sublists.

split_list([], [], []).
split_list([H|T], [H|X], Y) :- split_list(T, X, Y).
split_list([H|T], X, [H|Y]) :- split_list(T, X, Y).

% design_uses/2: Checks if the design uses each component in the list exactly once.
/* 
In the design_uses there are two arguments(Design, Components). Firstly, extracting all parts from Design
then comparing length of AllParts and length of Components
*/

design_uses(Design, Components) :- 
    extract_all_parts(Design, AllParts, Components),
    length(AllParts, PLen),
    length(Components, CLen),
    PLen = CLen.

% extract_all_parts/3: Extracts all parts from the design while preventing duplicates.
/*
An empty design returns an empty list.

part(C): When part(C) is encountered, select C, update the remaining list, and process the rest of the design.

shield(L): When shield(L) is encountered, recursively process the inner design (L) to extract parts. 
Use subtract/3 to ensure components used inside the shield are not reused outside. 
Process the remaining design and combine the results to return.
*/

extract_all_parts([], [], _).
extract_all_parts([part(C)|Rest], [C|Parts], Components) :- 
    select(C, Components, Remaining),
    extract_all_parts(Rest, Parts, Remaining).

extract_all_parts([shield(L)|Rest], Parts, Components) :- 
    L = [part(_)|_],
    extract_all_parts(L, InnerParts, Components),
    subtract(Components, InnerParts, RemainingComponents),
    extract_all_parts(Rest, RestParts, RemainingComponents),
    append(InnerParts, RestParts, Parts).
