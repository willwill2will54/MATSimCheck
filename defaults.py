import multiprocess

algorithm = [
    'trust', 'size', 'wgt', '3',
    'geo', 'rmsd', 'wgt', '2',
    'houseprice', 'avg', 'wgt', '1']
CoreDirectory = './Core'
NonCoreDirectory = './non_Core'
MatNameKey = 'Trusts (name)'
# Heading of the postcode field in the data
PostCodeKey = 'Postcode'
# URL of the postcodes.io API
ApiURL = 'http://postcodes.io/postcodes/'


threadcount = multiprocess.cpu_count()

# List of tuples, the whose constituents' permutations will be submitted as the parameter to TestAlgorithmMaker
TestAlgorithmVariables = (range(4), ) * 5


# Possible members of you algorithm with the weight being an itemp of the parameter
def TestAlgorithmMaker(variables):
    algorithm = [
        'trust', 'size', 'wgt', str(variables[0]),
        'geo', 'rmsd', 'wgt', str(variables[1]),
        'houseprice', 'avg', 'wgt', str(variables[2]),
        'StatutoryLowAge', 'avg', 'wgt', str(variables[3]),
        'StatutoryLowAge', 'rmsd', 'wgt', str(variables[4]),
        'StatutoryHighAge', 'avg', 'wgt', str(variables[3]),
        'StatutoryHighAge', 'rmsd', 'wgt', str(variables[4])]
    return algorithm


ProgressScoreHeaders = ['School level reading progress score', 'School level writing progress score',
                        'School level maths progress score', 'School level progress 8 score']
