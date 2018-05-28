def importer(extras, testing=False):
    import lib.messages as Messages
    from tinydb import TinyDB, Query
    import numpy as np
    from lib.misc import getpostcodes
    import defaults as defs
    from collections import Counter
    from os import listdir
    import multiprocessing
    import queue as q
    np.seterr(all='raise')

    Manager = multiprocessing.Manager()

    def submitchanged(thang):
        table.update(thang, doc_ids=[thang.doc_id, ])

    corelock = Manager.Lock()
    matlock = Manager.Lock()
    weblock = Manager.Lock()
    countylock = Manager.Lock()
    locks = Manager.dict()
    queue = Manager.Queue()

    noncore = TinyDB('./dbs/non_Core.json',)
    MATs = TinyDB('./dbs/MATS.json')
    core = TinyDB('./dbs/Core.json')
    counties = TinyDB('./dbs/Counties.json')

    locks = {'matlock': matlock, 'weblock': weblock, 'countylock': countylock, 'corelock': corelock}
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
    dbs = {'noncore': noncore, 'MATs': MATs, 'core': core, 'counties': counties, 'table': table}
    extras2 = extras + ['URN', ] + defs.ProgressScoreHeaders
    extras1 = extras
    import csv
    urns = []
    len1 = len([each for each in listdir(coredir) if each.endswith('.csv')])
    Messages.IMPORT('core')
    for num, file in enumerate([each for each in listdir(coredir) if each.endswith('.csv')]):
        Messages.WORKING(file, num + 1, len1)
        lastpc = 0
        for encoding in ['utf-8', 'utf-16', 'Windows-1252']:
            try:
                openfile = open(coredir + '/' + file, encoding=encoding)
                openfile.read
                openfile.close()
                with open(coredir + '/' + file, 'r', encoding=encoding) as openfile:
                    raw = csv.DictReader(openfile, delimiter=',')
                    dicts = [dict(row) for row in raw]
                    maxthing = len(dicts) ** 2
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
                        pc = int((((i + 1) ** 2) / maxthing) * 100)
                        if pc != lastpc:
                            Messages.PROGRESS('This', pc)
                            lastpc = pc
                    break
            except UnicodeError:
                pass
        Messages.PROGRESS('This', 100)
    len2 = len([each for each in listdir(noncoredir) if each.endswith('.csv')])
    Messages.IMPORT('non-core')
    for num, file in enumerate([each for each in listdir(noncoredir) if each.endswith('.csv')]):
        Messages.WORKING(file, num + 1, len2)
        lastpc = 0
        for encoding in ['utf-8', 'utf-16', 'Windows-1252']:
            try:
                openfile = open('./non_Core/' + file, encoding=encoding)
                openfile.close()
                with open(noncoredir + '/' + file, encoding=encoding) as openfile:
                    raw = csv.DictReader(openfile, delimiter=',')
                    dicts = [dict(row) for row in raw]
                    keys = set()
                    for i, x in enumerate(dicts):
                        urn = x['URN']
                        keys.update(set(x.keys()))
                        if urn in urns:
                            to_delete = set(x.keys()).difference(extras2)
                            for d in to_delete:
                                del x[d]
                            noncore.upsert(x, Query().URN == urn)
                            core.update(x, Query().URN == urn)
                        pc = int((((i + 1) ** 2) / maxthing) * 100)
                        if pc != lastpc:
                            Messages.PROGRESS('This', pc)
                            lastpc = pc
                        break
            except UnicodeError:
                pass
        Messages.PROGRESS('This', 100)
    with open('./special/HousePrices.csv') as openfile:
        raw = csv.DictReader(openfile, delimiter=',')
        dicts = [dict(row) for row in raw]
        counties.purge()
        counties.insert_multiple(dicts)

    threads = []

    class ThreadedProccessor(multiprocessing.Process):
        def __init__(self, function, name, queue):
            multiprocessing.Process.__init__(self)
            self.function = function
            self.name = name
            self.dbs = dbs
            self.q = queue

        def _debugprint(self, where):
            if self.name == 'Finding avg of houseprice...':
                print(where)

        def run(self):
            self._debugprint('running')
            locks['matlock'].acquire()
            self._debugprint('acquired')
            mats = self.dbs['table'].all()
            self._debugprint('got')
            locks['matlock'].release()
            self._debugprint('let go')
            for i, x in enumerate(mats):
                self.q.put(self.function(x, self.dbs, locks))
                self._debugprint('going')

    def lentest(t):
        return len(t) == 1

    table.remove(Query().IDs.test(lentest))
    Messages.PARGS()

    def pricecheck(x, dbs, locks):

        countieslist, nums, cords, postcodes = [], [], [], []
        for ID in x['IDs']:
            locks['corelock'].acquire()
            y = dbs['core'].get(doc_id=ID)
            locks['corelock'].release()
            if 'cord' in y:
                cords.append(y['cord'])
            else:
                postcodes.append(y[defs.PostCodeKey])
        cords2 = None
        if postcodes != []:
            locks['weblock'].acquire()
            while True:
                try:
                    cords2 = getpostcodes(postcodes)
                    assert cords2 is not None
                    break
                except Exception as e:
                    print(e)
                    Messages.WebTrouble()
            locks['weblock'].release()
        if cords2 is not None:
                locks['corelock'].acquire()
                for cord in cords2:
                    dbs['core'].update({'cord': cord}, Query()[defs.PostCodeKey] == cord['postcode'])
                locks['corelock'].release()
                cords += cords2
        for y in cords:
            countieslist.append(y['codes']['admin_county'])
        for y in countieslist:
            try:
                locks['countylock'].acquire()
                z = dbs['counties'].get(Query().CountyCode == y)
                nums.append(int(z['MedianHousePrice']))
                locks['countylock'].release()
            except TypeError:
                pass
        try:
            x['housepriceavg'] = np.average(np.array(nums))
        except Exception:
            pass
        return x

    def sizecheck(x, dbs, locks):
            if 'trustsize' in x:
                return x
            x['trustsize'] = len(x['IDs'])
            return x

    def PCdist(x, dbs, locks):
            if 'geormsd' in x:
                return x
            IDs = x['IDs']
            Postcodes = []
            cords2 = []
            for ID in IDs:
                try:
                    try:
                        locks['corelock'].acquire()
                        IDData = dbs['core'].get(doc_id=ID)
                        locks['corelock'].release()
                    except TypeError:
                        print(ID, flush=True)
                        raise
                    if 'cord' in IDData:
                        cords2.append(IDData['cord'])
                    Postcodes.append((ID, IDData[defs.PostCodeKey]))
                except KeyError:
                    raise
            if Postcodes != []:
                locks['weblock'].acquire()
                while True:
                    try:
                        cords3 = getpostcodes(Postcodes)
                        assert cords3 is not None
                        break
                    except Exception as e:
                        print(e)
                        Messages.WebTrouble()
                locks['weblock'].release()
            if cords3 is not None:
                locks['corelock'].acquire()
                for cord in cords3:
                    dbs['core'].update({'cord': cord}, Query()[defs.PostCodeKey] == cord['postcode'])
                locks['corelock'].release()
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
            def avg(x, key, dbs, locks):
                if key + 'avg' in x:
                    return x
                nums = []
                locks['corelock'].acquire()
                for ID in x['IDs']:
                    nums.append(float(dbs['core'].get(doc_id=ID)[key]))
                locks['corelock'].release()
                try:
                    x[key + 'avg'] = np.average(np.array(nums))
                except Exception:
                    pass
                return x
            func = lambda t, dbs, locks: avg(t, key, dbs, locks)
        elif operation == 'rmsd':
            def rmsd(x, key, dbs, locks):
                if key + 'rmsd' in x:
                    return x
                array = np.array([])
                nums = []
                locks['corelock'].acquire()
                for ID in x['IDs']:
                    nums.append(float(dbs['core'].get(doc_id=ID)[key]))
                locks['corelock'].release()
                array = np.append(array, nums)
                try:
                    x[key + 'rmsd'] = np.std(array)
                except Exception:
                    pass
                return x
            func = lambda t, dbs, locks: rmsd(t, key, dbs, locks)
        elif operation == 'mode':
            def mode(x, key, dbs, locks):
                if key + 'mode' in x:
                    return x
                locks['corelock'].acquire()
                stuff = [dbs['core'].get(doc_id=ID)[key] for ID in x['IDs']]
                locks['corelock'].release()
                x[key + 'mode'] = Counter(stuff).most_common(1)[0][0]
                return x
            func = lambda t, dbs, locks: mode(t, key, dbs, locks)
        elif operation == 'rng':
            def rng(x, key, dbs, locks):
                if key + 'rng' in x:
                    return x
                locks['corelock'].acquire()
                stuff = [dbs['core'].get(doc_id=ID)[key] for ID in x['IDs']]
                locks['corelock'].release()
                x[key + 'rng'] = max(stuff) - min(stuff)
                return x
            func = lambda t, dbs, locks: rng(t, key, dbs, locks)
        elif operation == 'med':
            def med(x, key, dbs, locks):
                try:
                    if key + 'med' in x:
                        return x
                    nums = []
                    locks['corelock'].acquire()
                    for ID in x['IDs']:
                        nums.append(float(dbs['core'].get(doc_id=ID)[key]))
                    locks['corelock'].release()
                    try:
                        x[key + 'med'] = np.median(np.array(nums))
                    except Exception:
                        pass
                except Exception:
                    pass
                return x
            func = lambda t, dbs, locks: med(t, key, dbs, locks)
        return func
    process = []
    ops = ['avg', 'rmsd', 'med', 'rng', 'mode', 'size']
    for y, z in zip(extras1[:-1:], extras1[1::]):
        if z in ops:
            process.append((y, z))
    for x, y in process:
        if (x, y) == ('geo', 'rmsd'):
            threads.append(ThreadedProccessor(PCdist, Messages.PCDIST(), queue))
            continue
        Message = Messages.PARG(x, y)
        if (x, y) == ('trust', 'size'):
            threads.append(ThreadedProccessor(sizecheck, Message, queue))
        elif (x, y) == ('houseprice', 'avg'):
            threads.append(ThreadedProccessor(pricecheck, Message, queue))
        else:
            threads.append(ThreadedProccessor(operator(x, y), Message, queue))
    taskpcfactor = 100 / (len(threads) * len(table.all()))
    for thread in threads:
        thread.start()
    done = 0
    inserted = 0
    oldpc = 100
    while done < 2:
        if all(not thread.is_alive() for thread in threads):
            done += 1
        try:
            thang = queue.get(timeout=2)
        except q.Empty as e:
            continue
        locks['matlock'].acquire()
        submitchanged(thang)
        locks['matlock'].release()
        inserted += 1
        pc = int(taskpcfactor * inserted)
        if pc != oldpc:
            Messages.PROGRESS('Compiling Variables', pc)
        oldpc = pc
        if sum(thread.is_alive() for thread in threads) == 1:
            print('Hanging on', [thread.name for thread in threads if thread.is_alive()][0], flush=True)
    print('shutting up shop')
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
