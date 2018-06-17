def ALREADYIMPORT(a):
    print('This version of {} has already been imported. Skipping...'.format(a), flush=True)


def SEP():
    num = 80
    print("".join(['-' * num, '\n', '*' * num, '\n', '-' * num]), flush=True)


def IMPORT(a):
    print('Importing {} files...'.format(a), flush=True)


def WORKING(a, b, c):
    print('Working on {}--{}/{}'.format(a, b, c), flush=True)


def PURGE():
    print("Purging all databases...", flush=True)


def DONE():
    print("Done!", flush=True)


def TRY(a):
    print('\nTry {}'.format(a), flush=True)


def WebTrouble():
    print('There appears to be a problem with your internet connection.\nTrying again...', flush=True)


def PARGS():
    print("Processing arguments...", flush=True)


def PARG(y, x):
    return "Finding {} of {}...".format(x, y)


def PARGTRY(y, x):
    print("The {} of {} has already been found. Skipping...".format(y, x), flush=True)


def PCDIST():
    return "Finding geographic dispersion of postcodes..."


def KeyNotDone(k):
    print('{} has not been calculated. Purge and recompile,\
 then try again if you want to use this variable.'.format(k), flush=True)


def COMPILE():
    print('Table not found: compiling', flush=True)


def TABLESTRING(tablestring):
    print('(tablestring: {})'.format(tablestring), flush=True)


def PROGRESS(thing, pc):
    print('{} is {}% done'.format(thing, pc), flush=True)


def ALERT():
    print('\a', flush=True)
