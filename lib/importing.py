def importer(extras, testing=False):
    import lib.messages as Messages
    from tinydb import TinyDB, Query
    import progressbar as pbar
    import numpy as np
    from random import randint
    from lib.misc import getpostcodes
    import defaults as defs
    from collections import Counter
    from os import listdir
    import threading
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
        Messages.COMPILE()
        Messages.TABLESTRING(tablestring)

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
                            Mat_in = core.upsert(x, Query().URN == urn)
                            if type(Mat_in) == int:
                                Mat_in = [Mat_in, ]
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

    threads = []

    corelock = threading.Lock()
    matlock = threading.Lock()
    weblock = threading.Lock()
    comlocktable = []

    def submitchanged(changed):
        for thang in changed:
            table.update(thang, doc_ids=[thang.doc_id, ])
        return []

    class ThreadedProccessor(threading.Thread):
        def __init__(self, function, name):
            threading.Thread.__init__(self)
            self.function = function
            self.name = name
            self.id = len(comlocktable)
            comlocktable.append([threading.Lock(), name, 0])

        def run(self):
            matlock.acquire()
            mats = table.all()
            matlock.release()
            changed = []
            matlen = len(mats)
            for i, x in enumerate(mats):
                changed.append(self.function(x))
                comlocktable[self.id][0].acquire()
                comlocktable[self.id][2] = int(i * 100 / matlen)
                comlocktable[self.id][0].release()
                if matlock.acquire(blocking=False):
                    changed = submitchanged(changed)
                    matlock.release()
            if changed != []:
                matlock.acquire()
                submitchanged(changed)
                matlock.release()
                print('{} is 100% done'.format(self.name), flush=True)

    class ThreadedMessage(threading.Thread):
        def __init__(self):
            threading.Thread.__init__(self)

        def run(self):
            from time import sleep
            while all(x.is_alive() for x in threads):
                prints = []
                for x in comlocktable:
                    x[0].acquire()
                    name = x[1]
                    pc = x[2]
                    x[0].release()
                    prints.append('{} is {}% done'.format(name, pc))
                for x in prints:
                    print(x, flush=True)
                sleep(2)
            prints = []
            for x in comlocktable:
                name = x[1]
                prints.append('{} is {}% done'.format(name, 100))
            for x in prints:
                print(x, flush=True)

    def lentest(t):
        return len(t) == 1

    table.remove(Query().IDs.test(lentest))
    Messages.PARGS()

    def pricecheck(x):
        countieslist, nums, cords, postcodes = [], [], [], []
        for ID in x['IDs']:
            corelock.acquire()
            y = core.get(doc_id=ID)
            corelock.release()
            if 'cord' in y:
                cords.append(y['cord'])
            else:
                postcodes.append(y[defs.PostCodeKey])
        cords2 = None
        if postcodes != []:
                weblock.acquire()
                while True:
                    try:
                        cords2 = getpostcodes(postcodes)
                        assert cords2 is not None
                        break
                    except Exception:
                        Messages.WebTrouble()
                weblock.release()
        if cords2 is not None:
                corelock.acquire()
                for cord in cords2:
                    core.update({'cord': cord}, Query()[defs.PostCodeKey] == cord['postcode'])
                corelock.release()
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
            if 'trustsize' in x:
                return x
            x['trustsize'] = len(x['IDs'])
            return x

    def PCdist(x):
            if 'geormsd' in x:
                return x
            IDs = x['IDs']
            Postcodes = []
            cords2 = []
            for ID in IDs:
                try:
                    try:
                        corelock.acquire()
                        IDData = core.get(doc_id=ID)
                        corelock.release()
                    except TypeError:
                        print(ID, flush=True)
                        raise
                    if 'cord' in IDData:
                        cords2.append(IDData['cord'])
                    Postcodes.append((ID, IDData[defs.PostCodeKey]))
                except KeyError:
                    raise
            if Postcodes != []:
                weblock.acquire()
                while True:
                    try:
                        cords3 = getpostcodes(Postcodes)
                        assert cords3 is not None
                        break
                    except Exception:
                        Messages.WebTrouble()
                weblock.release()
            if cords3 is not None:
                corelock.acquire()
                for cord in cords3:
                    core.update({'cord': cord}, Query()[defs.PostCodeKey] == cord['postcode'])
                corelock.release()
                cords2 += cords3
            cords = [(x['northings'], x['eastings']) for x in cords2]
            cordsa = np.array(cords)
            try:
                rmsd = np.std(cordsa)
                x['geormsd'] = rmsd
            except OverflowError:
                pass
            except Exception:
                pass
            return x

    def operator(key, operation):
        if operation == 'avg':
            def avg(x, key):
                if key + 'avg' in x:
                    return x
                nums = []
                corelock.acquire()
                for ID in x['IDs']:
                    nums.append(float(core.get(doc_id=ID)[key]))
                corelock.release()
                try:
                    x[key + 'avg'] = np.average(np.array(nums))
                except Exception:
                    pass
                return x
            func = lambda t: avg(t, key)
        elif operation == 'rmsd':
            def rmsd(x, key):
                if key + 'rmsd' in x:
                    return x
                array = np.array([])
                nums = []
                corelock.acquire()
                for ID in x['IDs']:
                    nums.append(float(core.get(doc_id=ID)[key]))
                corelock.release()
                array = np.append(array, nums)
                try:
                    x[key + 'rmsd'] = np.std(array)
                except Exception:
                    pass
                return x
            func = lambda t: rmsd(t, key)
        elif operation == 'mode':
            def mode(x, key):
                if key + 'mode' in x:
                    return x
                corelock.acquire()
                stuff = [core.get(doc_id=ID)[key] for ID in x['IDs']]
                corelock.release()
                x[key + 'mode'] = Counter(stuff).most_common(1)[0][0]
                return x
            func = lambda t: mode(t, key)
        elif operation == 'rng':
            def rng(x, key):
                if key + 'rng' in x:
                    return x
                corelock.acquire()
                stuff = [core.get(doc_id=ID)[key] for ID in x['IDs']]
                corelock.release()
                x[key + 'rng'] = max(stuff) - min(stuff)
                return x
            func = lambda t: rng(t, key)
        elif operation == 'med':
            def med(x, key):
                try:
                    if key + 'med' in x:
                        return x
                    nums = []
                    corelock.acquire()
                    for ID in x['IDs']:
                        nums.append(float(core.get(doc_id=ID)[key]))
                    corelock.release()
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
        if (x, y) == ('geo', 'rmsd'):
            threads.append(ThreadedProccessor(PCdist, Messages.PCDIST()))
            continue
        Message = Messages.PARG(x, y)
        if (x, y) == ('trust', 'size'):
            threads.append(ThreadedProccessor(sizecheck, Message))
        elif (x, y) == ('houseprice', 'avg'):
            threads.append(ThreadedProccessor(pricecheck, Message))
        else:
            threads.append(ThreadedProccessor(operator(x, y), Message))
    Messageing = ThreadedMessage()
    for thread in threads:
        thread.start()
    Messageing.start()
    for thread in threads:
        thread.join()
    Messageing.join()
    for x in [noncore, MATs, core, counties]:
        x.close()
    print('\a', flush=True)
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
