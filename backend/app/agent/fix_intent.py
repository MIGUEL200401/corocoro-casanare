import unicodedata, re
def normalize(t):
    t=t.lower()
    t=''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')
    return t
