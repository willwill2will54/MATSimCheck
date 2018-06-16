def tester(table, MAT, algorithm=['geormsd', 'wgt', '500'], number=None, testing=False):
    from collections import Counter
    from tinydb import TinyDB, Query
    from pprint import pprint
    import defaults as defs
    import numpy as np

    MATs = TinyDB('./dbs/MATS.json')
    core = TinyDB('./dbs/Core.json')
    tab = MATs.table(table)
    cand = tab.all()
    tested = tab.get(Query()['Trust name'] == MAT)
    algorithm2 = []
    for a, b, c, d in zip(algorithm[:-3:4], algorithm[1:-2:4], algorithm[2:-1:4], algorithm[3::4]):
        algorithm2 += [a + b, c, d]
    algorithm = algorithm2
    try:
        assert all(x in ['wgt', 'is', 'isnot'] or x.endswith('gets') for x in algorithm[1:-1:3])
    except AssertionError:
        raise
    try:
        assert 'wgt' in algorithm[1:-1:3]
    except AssertionError:
        raise
    crits = list(zip(algorithm[:-2:3], algorithm[1:-1:3], algorithm[2::3]))
    cand = list([x for x in cand if x['Trust name'] not in (tested['Trust name'], '')])
    for x in cand:
        x['sims'] = 0
    for key, method, value in crits:
        try:
            if method == 'is':
                if value is 'same':
                    value = tested[key]
                cand[:] = [x for x in cand if str(x[key]) == str(value)]
            elif method == 'isnot':
                if value is 'same':
                    value = tested[key]
                cand[:] = [x for x in cand if str(x[key]) != str(value)]
            elif method.endswith('notgets'):
                method = method[:-7]
                if method is 'same':
                    method = tested[key]
                for x in cand:
                    try:
                        if str(x[key]) != str(method):
                            x['sims'] += float(value)
                    except Exception as e:
                        print(x, flush=True)
                        pprint(cand)
                        raise e
            elif method.endswith('gets'):
                method = method[:-4]
                if method is 'same':
                    method = tested[key]
                for x in cand:
                    try:
                        if str(x[key]) == str(method):
                            x['sims'] += float(value)
                    except Exception as e:
                        print(x, flush=True)
                        pprint(cand)
                        raise e
            elif method == 'wgt':
                donecand = []
                errorcount = 0
                if not any(key in x.keys() for x in cand):
                    print('{} has not been calculated. Purge and recompile, \
then try again if you want to use this variable.'.format(key))
                    continue
                elif key not in tested.keys():
                    print('{} has not been calculated for the tested MAT. Purge and recompile, \
then try again if you want to use this variable.'.format(key), flush=True)
                    continue
                for x in cand:
                    try:
                        x['sims'] += (abs((float(tested[key]) - float(x[key])) /
                                          float(tested[key]))) * float(value) * 100
                    except ZeroDivisionError:
                        pass
                    except KeyError as e:
                        x['sims'] += float(value)
                        errorcount += 1
                        print('Weight exception: {} not found ({}/{})'.format(e, errorcount, len(cand)), flush=True)
                    donecand.append(dict(x))
                cand = donecand[:]

        except KeyError:
            print(x, tested, key, flush=True)
            raise
    MATs.close()
    for x in cand:
        x['sims'] *= 1000
    simsmax = max([x['sims'] for x in cand])
    simsmin = min([x['sims'] for x in cand])
    counterpack = list(cand)
    for x in counterpack:
        x['sims'] = simsmax - x['sims']
    counter = Counter({x['Trust name']: x['sims'] for x in counterpack})
    finlist = [(a, int((b / (simsmax + 1)) * 100)) for a, b in counter.most_common()]
    if testing:
        lastthing = finlist
    else:
        dict1 = {x: [] for x in defs.ProgressScoreHeaders}
        dict2 = dict(dict1)
        for x in finlist[:number]:
            for ID in next(item for item in counterpack if item['Trust name'] == x[0])['IDs']:
                school = core.get(doc_id=ID)
                for y, z in school.items():
                    if y in defs.ProgressScoreHeaders:
                        dict1[y].append(float(z))
        for ID in tested['IDs']:
            school = core.get(doc_id=ID)
            for y, z in school.items():
                if y in defs.ProgressScoreHeaders:
                    dict2[y].append(float(z))
        resultavg = {}
        subjectavg = {}
        for x, y in dict1.items():
            if len(y) > 0:
                resultavg['Average ' + x] = round(np.average(np.array(y)), 2)
            else:
                resultavg['Average ' + x] = 'NaN'
        for x, y in dict2.items():
            if len(y) > 0:
                subjectavg['Subject ' + x] = round(np.average(np.array(y)), 2)
            else:
                subjectavg['Subject ' + x] = 'NaN'
        lastthing = (subjectavg, resultavg)

    return (['{} (Score: {}%)'.format(a, b) for a, b in finlist[:number]], lastthing, MAT)
    """for x in cand:
        if x['sims'] == simsmin:
            return x"""
