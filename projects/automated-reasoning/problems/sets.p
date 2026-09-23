include('SET001-0.ax').
fof(dirimg_def, axiom, ! [Y, A] : (member(Y, dirimg(A)) <=> (? [X] : (member(X, A) & role(X, Y))))).
fof(valres_def, axiom, ! [X, B] : (member(X, valres(B)) <=> (! [Y] : (role(X, Y) => member(Y, B))))).
fof(conjecture, conjecture, ! [A, B] : (subset(dirimg(A), B) <=> subset(A, valres(B)))). 
