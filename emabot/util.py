from decimal import Decimal

def huf(f: Decimal):
    return '{:,.2f}'.format(f)

def pdiff(old, new):
    return ((Decimal(new) - Decimal(old)) / Decimal(old)) * Decimal('100.0')

def import_class(cl: str):
    """Import a class by name"""
    d = cl.rfind(".")
    classname = cl[d+1:len(cl)]
    m = __import__(cl[0:d], globals(), locals(), [classname])
    return getattr(m, classname)
