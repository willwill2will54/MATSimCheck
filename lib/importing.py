def importer(extras, testing=False):
    import lib.messages as Messages
    from tinydb import TinyDB, Query
    import progressbar as pbar
    import numpy as np
    from random import shuffle
    from lib.misc import getpostcodes
    import defaults as defs
    from collections import Counter
    from os import listdir
    widgets = [
        pbar.AnimatedMarker(markers='⣯⣟⡿⢿⣻⣽⣾⣷'),
        ' [', pbar.Percentage(), '] ',
        pbar.Bar(marker='■', fill='□', left='[', right=']'),
        ' (', pbar.AdaptiveETA(), ') ', ]
    np.seterr(all='raise')
    noncore = TinyDB('./dbs/non_Core.json',)
    MATs = TinyDB('./dbs/MATS.json')
    core = TinyDB('./dbs/Core.json')
    counties = TinyDB('./dbs/Counties.json')
    tablestring = '|'.join(x for x in extras)
    if testing:
        tablestring += '**testdataset**'
        coredir = 'special/test/'
    else:
        coredir = defs.CoreDirectory
    noncoredir = defs.NonCoreDirectory
    if tablestring in MATs.tables():
        return (tablestring, True)
    else:
        print('Table not found: compiling')
        print('(tablestring: {})'.format(tablestring))

    table = MATs.table(tablestring)
    extras2 = extras + ['URN', ] + defs.ProgressScoreHeaders
    extras1 = extras
    import csv
    urns = []
    len1 = len([each for each in listdir(coredir) if each.endswith('.csv')])
    Messages.IMPORT('core')
    for num, file in enumerate([each for each in listdir(coredir) if each.endswith('.csv')]):
        Messages.WORKING(file, num + 1, len1)
        for encoding in ['utf-8', 'utf-16', 'Windows-1252']:
            try:
                Messages.TRY(encoding)
                openfile = open(coredir + '/' + file, encoding=encoding)
                openfile.read
                openfile.close()
                with open(coredir + '/' + file, 'r', encoding=encoding) as openfile:
                    raw = csv.DictReader(openfile, delimiter=',')
                    dicts = [dict(row) for row in raw]
                    with pbar.ProgressBar(max_value=len(dicts) ** 2, redirect_stdout=True, widgets=widgets) as bar:
                        for i, x in enumerate(dicts):
                            urn = x['URN']
                            urns.append(urn)
                            Mat_in = [core.upsert(x, Query().URN == urn), ]
                            try:
                                search = table.search(Query()['Trust name'] == x[defs.MatNameKey])
                                Mat_in.extend([x for x in search[0]['IDs']])
                            except Exception:
                                pass
                            table.upsert({"Trust name": x[defs.MatNameKey],
                                          "IDs": list(set(Mat_in))}, Query()['Trust name'] == x[defs.MatNameKey])
                            bar.update((i + 1) ** 2)
                        break
            except UnicodeError:
                pass
    len2 = len([each for each in listdir(noncoredir) if each.endswith('.csv')])
    Messages.IMPORT('non-core')
    for num, file in enumerate([each for each in listdir(noncoredir) if each.endswith('.csv')]):
        Messages.WORKING(file, num + 1, len2)
        for encoding in ['utf-8', 'utf-16', 'Windows-1252']:
            try:
                openfile = open('./non_Core/' + file, encoding=encoding)
                openfile.close()
                with open(noncoredir + '/' + file, encoding=encoding) as openfile:
                    raw = csv.DictReader(openfile, delimiter=',')
                    dicts = [dict(row) for row in raw]
                    keys = set()
                    with pbar.ProgressBar(max_value=len(dicts) ** 2, redirect_stdout=True, widgets=widgets) as bar:
                        for i, x in enumerate(dicts):
                            urn = x['URN']
                            keys.update(set(x.keys()))
                            if urn in urns:
                                to_delete = set(x.keys()).difference(extras2)
                                for d in to_delete:
                                    del x[d]
                                noncore.upsert(x, Query().URN == urn)
                                core.update(x, Query().URN == urn)
                            bar.update((i + 1) ** 2)
                        break
            except UnicodeError:
                pass
    with open('./special/HousePrices.csv') as openfile:
        raw = csv.DictReader(openfile, delimiter=',')
        dicts = [dict(row) for row in raw]
        counties.purge()
        counties.insert_multiple(dicts)

    def lentest(t):
        return len(t) == 1
    table.remove(Query().IDs.test(lentest))
    Messages.PARGS()
    with pbar.ProgressBar(max_value=len(table.all()) + 1, redirect_stdout=True, widgets=widgets) as bar:
        global counter
        counter = 0

        def pricecheck(x):
            global counter
            counter += 1
            bar.update(counter)
            countieslist, nums, cords, postcodes = [], [], [], []
            for ID in x['IDs']:
                y = core.get(doc_id=ID)
                if 'cord' in y:
                    cords.append(y['cord'])
                else:
                    postcodes.append(y[defs.PostCodeKey])
            cords2 = None
            if postcodes != []:
                    while True:
                        try:
                            cords2 = getpostcodes(postcodes)
                            assert cords2 is not None
                            break
                        except Exception:
                            Messages.WebTrouble()
            if cords2 is not None:
                    for cord in cords2:
                        core.update({'cord': cord}, Query()[defs.PostCodeKey] == cord['postcode'])
                    cords += cords2
            for y in cords:
                countieslist.append(y['codes']['admin_county'])
            for y in countieslist:
                try:
                    z = counties.get(Query().CountyCode == y)
                    nums.append(int(z['MedianHousePrice']))
                except TypeError:
                    pass
            try:
                x['housepriceavg'] = np.average(np.array(nums))
            except Exception:
                pass
            return x

        def sizecheck(x):
                global counter
                counter += 1
                bar.update(counter)
                if 'trustsize' in x:
                    return x
                x['trustsize'] = len(x['IDs'])
                return x

        def PCdist():
                Messages.PCDIST()
                thelist = table.all()
                shuffle(thelist)
                for i, x in enumerate(thelist):
                    if 'geormsd' in x:
                        continue
                    bar.update(i)
                    IDs = x['IDs']
                    Postcodes = []
                    cords2 = []
                    for ID in IDs:
                        try:
                            try:
                                IDData = core.get(doc_id=ID)
                            except TypeError:
                                print(ID)
                                raise
                            if 'cord' in IDData:
                                cords2.append(IDData['cord'])
                            Postcodes.append((ID, IDData[defs.PostCodeKey]))
                        except KeyError:
                            raise
                    if Postcodes != []:
                        while True:
                            try:
                                cords3 = getpostcodes(Postcodes)
                                assert cords3 is not None
                                break
                            except Exception:
                                Messages.WebTrouble()
                                bar.update(i)
                    if cords3 is not None:
                        for cord in cords3:
                            core.update({'cord': cord}, Query()[defs.PostCodeKey] == cord['postcode'])
                        cords2 += cords3
                    cords = [(x['northings'], x['eastings']) for x in cords2]
                    cordsa = np.array(cords)
                    try:
                        rmsd = np.std(cordsa)
                        table.update({'geormsd': rmsd}, doc_ids=[x.doc_id, ])
                    except OverflowError:
                        pass
                    except Exception:
                        pass

        def operator(key, operation):
            global counter
            counter = 0
            if operation == 'avg':
                def avg(x, key):
                    global counter
                    counter += 1
                    if key + 'avg' in x:
                        return x
                    bar.update(counter)
                    nums = []
                    for ID in x['IDs']:
                        nums.append(float(core.get(doc_id=ID)[key]))
                    try:
                        x[key + 'avg'] = np.average(np.array(nums))
                    except Exception:
                        pass
                    return x
                func = lambda t: avg(t, key)
            elif operation == 'rmsd':
                def rmsd(x, key):
                    global counter
                    counter += 1
                    if key + 'rmsd' in x:
                        return x
                    bar.update(counter)
                    array = np.array([])
                    nums = []
                    for ID in x['IDs']:
                        nums.append(float(core.get(doc_id=ID)[key]))
                    array = np.append(array, nums)
                    try:
                        x[key + 'rmsd'] = np.std(array)
                    except Exception:
                        pass
                    return x
                func = lambda t: rmsd(t, key)
            elif operation == 'mode':
                def mode(x, key):
                    global counter
                    counter += 1
                    if key + 'mode' in x:
                        return x
                    bar.update(counter)
                    stuff = [core.get(doc_id=ID)[key] for ID in x['IDs']]
                    x[key + 'mode'] = Counter(stuff).most_common(1)[0][0]
                    return x
                func = lambda t: mode(t, key)
            elif operation == 'rng':
                def rng(x, key):
                    global counter
                    counter += 1
                    if key + 'rng' in x:
                        return x
                    bar.update(counter)
                    stuff = [core.get(doc_id=ID)[key] for ID in x['IDs']]
                    x[key + 'rng'] = max(stuff) - min(stuff)
                    return x
                func = lambda t: rng(t, key)
            elif operation == 'med':
                def med(x, key):
                    try:
                        global counter
                        counter += 1
                        if key + 'med' in x:
                            return x
                        bar.update(counter)
                        nums = []
                        for ID in x['IDs']:
                            nums.append(float(core.get(doc_id=ID)[key]))
                        try:
                            x[key + 'med'] = np.median(np.array(nums))
                        except Exception:
                            pass
                    except Exception:
                        pass
                    return x
                func = lambda t: med(t, key)
            return func
        process = []
        ops = ['avg', 'rmsd', 'med', 'rng', 'mode', 'size']
        for y, z in zip(extras1[:-1:], extras1[1::]):
            if z in ops:
                process.append((y, z))
        for x, y in process:
            counter = 0
            if (x, y) == ('geo', 'rmsd'):
                PCdist()
                continue
            Messages.OpDeclare(y, x)
            if (x, y) == ('trust', 'size'):
                table.update(sizecheck)
            elif (x, y) == ('houseprice', 'avg'):
                table.update(pricecheck)
            else:
                table.update(operator(x, y))
    for x in [noncore, MATs, core, counties]:
        x.close()
    print('\a')
    print('tablestring:', tablestring)
    return (tablestring, False)


def MATList():
    import defaults as defs
    from collections import Counter
    from os import listdir
    import csv
    for file in [each for each in listdir(defs.CoreDirectory) if each.endswith('.csv')]:
        for encoding in ['utf-8', 'utf-16', 'Windows-1252']:
            try:
                openfile = open(defs.CoreDirectory + '/' + file, encoding=encoding)
                openfile.read
                openfile.close()
                with open(defs.CoreDirectory + '/' + file, 'r', encoding=encoding) as openfile:
                    raw = csv.DictReader(openfile, delimiter=',')
                    dicts = [dict(row) for row in raw]
                    trusts = []
                    for x in dicts:
                        trust = x[defs.MatNameKey]
                        if trust.strip() is not '':
                            trusts.append(trust)
                    trusts = [x for x, y in Counter(trusts).items() if y > 1]
                    return sorted(list(set(trusts)))
            except UnicodeError:
                pass
