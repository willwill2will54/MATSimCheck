algorithm = [
    'trust', 'size', 'wgt', '1',
    'geo', 'rmsd', 'wgt', '1',
    'houseprice', 'avg', 'wgt', '1',
    'StatutoryLowAge', 'avg', 'wgt', '1',
    'StatutoryLowAge', 'rmsd', 'wgt', '1',
    'StatutoryHighAge', 'avg', 'wgt', '1',
    'StatutoryHighAge', 'rmsd', 'wgt', '1']
CoreDirectory = './Core'
NonCoreDirectory = './non_Core'
MatNameKey = 'Trusts (name)'
# Heading of the postcode field in the data
PostCodeKey = 'Postcode'
# URL of the postcodes.io API
ApiURL = 'http://api.postcodes.io/postcodes/'


TestAlgorithmVariables = (range(4), ) * 5


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
