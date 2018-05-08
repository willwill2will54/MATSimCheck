def tester(MAT, table, algorithm=['geormsd', 'wgt', '500'], number=None, testing=False):
    from collections import Counter
    from tinydb import TinyDB, Query
    from pprint import pprint
    MATs = TinyDB('./dbs/MATS.json')
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
    cand = list([x for x in cand if x['Trust name'] != tested['Trust name']])
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
            elif method.endswith('gets'):
                method = method[:-4]
                if method is 'same':
                    method = tested[key]
                for x in cand:
                    try:
                        if str(x[key]) == str(method):
                            x['sims'] += float(value)
                    except Exception as e:
                        print(x)
                        pprint(cand)
                        raise e
            elif method == 'wgt':
                donecand = []
                for x in cand:
                    try:
                        x['sims'] += (abs((float(tested[key]) - float(x[key])) / float(tested[key]))) * float(value) * 100
                    except ZeroDivisionError:
                        pass
                    except Exception as e:
                        x['sims'] += float(value)
                        print('Weight exception:', e)
                    donecand.append(dict(x))
                cand = donecand[:]

        except KeyError:
            print(x, tested, key)
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
    return (['{} (Score: {}%)'.format(a, b) for a, b in finlist[:number]], finlist)
    """for x in cand:
        if x['sims'] == simsmin:
            return x"""
