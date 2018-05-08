def ALREADYIMPORT(a):
    print('This version of {} has already been imported. Skipping...'.format(a))


def IMPORT(a):
    print('Importing {} files...'.format(a))


def WORKING(a, b, c):
    print('Working on {}--{}/{}'.format(a, b, c))


def TRY(a):
    # print('Trying {}...'.format(a), end='\r')
    pass


def WebTrouble():
    print('There appears to be a problem with your internet connection.\nTrying again...')


def OpDeclare(y, x):
    print('Finding {} of {}...'.format(y, x))


def PARGS():
    print("Processing arguments...")


def PARG(y, x):
    print("Finding {} of {}...".format(y, x))


def PARGTRY(y, x):
    print("The {} of {} has already been found. Skipping...".format(y, x))


def PCDIST():
    print("Finding geographic dispersion of postcodes")
