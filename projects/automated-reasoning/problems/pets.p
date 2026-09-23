fof(distinct_rooms, axiom, $distinct(r1, r2, r3, r4, r5, r6)).
fof(finite_domain, axiom, ! [X] : (X = r1 | X = r2 | X = r3 | X = r4 | X = r5 | X = r6)).

fof(next, axiom, ! [X, Y] : ( next(X, Y) <=> ( (X = r1 & Y = r2) | (X = r2 & Y = r3) | (X = r3 & Y = r4) | (X = r4 & Y = r5) | (X = r5 & Y = r6) ))).

fof(hamster, axiom, ! [X] : ((X = r6) => hamster(X))).
fof(hamster_never_nervous, axiom, ! [X] : (hamster(X) => ~nervous(X))).

fof(animals_r1_5, axiom, ! [X] : ((X = r1 | X = r2 | X = r3 | X = r4 | X = r5) => (dog(X) | cat(X)))).
fof(unique_animal, axiom, ! [X] : ~((dog(X) & cat(X)) | (dog(X) & hamster(X)) | (cat(X) & hamster(X)))).

fof(light, axiom, ! [X] : ((nervous(X) => lit(X)) & (~nervous(X) => ~lit(X)))).

fof(dog_nervous, axiom, ! [X] : (dog(X) => (nervous(X) <=> ( ? [Y, Z] : ( next(Y, X) & next(X, Z) & dog(Y) & dog(Z) ) )))).
fof(cat_nervous, axiom, ! [X] : (cat(X) => (nervous(X) <=> ( ? [Y] : ( (next(Y, X) | next(X, Y)) & cat(Y) ) )))).

fof(at_least_one_lit, axiom, ? [X] : lit(X)).
fof(only_one_lit, axiom, ! [X, Y] : ((lit(X) & lit(Y)) => (X = Y))).
