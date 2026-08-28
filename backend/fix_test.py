import unicodedata
def norm(s): return ''.join(c for c in unicodedata.normalize('NFD', s.lower()) if unicodedata.category(c) != 'Mn')
tests=["quiero ir a un rio","quiero ir a un río","quiero ir al rio cusiana","que puedo hacer diferente en casanare","quiero turismo de naturaleza","quiero hacer algo distinto hoy","donde puedo bañarme en rio"]
for t in tests:
    nt=norm(t)
    hit = any(k in nt for k in ["visitar","lugar","turismo","conocer","finca","hato","safari","rio","naturaleza","paseo","diferente","distinto","banarme"])
    print(t, "->", nt, "hit", hit)
