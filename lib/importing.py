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
    from functools import partial
    from lib.operations import operator
    np.seterr(all='raise')

    Manager = multiprocessing.Manager()

    def submitchanged(thang):
        table.update(thang, doc_ids=[thang.doc_id, ])

    queue = Manager.Queue()

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
    dbs = {'noncore': noncore, 'MATs': MATs, 'core': core, 'counties': counties, 'table': table}
    extras2 = extras + ['URN', ] + defs.ProgressScoreHeaders
    extras1 = extras
    import csv
    urns = []
    len1 = len([each for each in listdir(coredir) if each.endswith('.csv')])
    Messages.IMPORT('core')
    for num, file in enumerate([each for each in listdir(coredir) if each.endswith('.csv')]):
        Messages.WORKING(file, num + 1, len1)
        lastpc = 1
        for encoding in ['utf-8', 'utf-16', 'Windows-1252']:
            try:
                openfile = open(coredir + '/' + file, encoding=encoding)
                openfile.read
                openfile.close()
                with open(coredir + '/' + file, 'r', encoding=encoding) as openfile:
                    raw = csv.DictReader(openfile, delimiter=',')
                    dicts = [dict(row) for row in raw]
                    maxthing = len(dicts)
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
                        pc = int(((i + 1) / maxthing) * 100)
                        if pc != lastpc:
                            Messages.PROGRESS('Initialising school database', pc)
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
                    maxthing = len(dicts)
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
                        pc = int(((i + 1) / maxthing) * 100)
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
            self.where = 'initialised'
            self.mats = self.dbs['table'].all()
            self.core = {str(x.doc_id): x for x in self.dbs['core'].all()}

        def broken(self):
            print(self.where, flush=True)

        def run(self):
            self.where = 'running'
            for x in self.mats:
                self.q.put(self.function(x, self.dbs, self.core))
                self.where = 'going'

    def lentest(t):
        return len(t) == 1

    table.remove(Query().IDs.test(lentest))
    Messages.PARGS()

    def pricecheck(dbs, t):

        countieslist, nums, cords, postcodes = [], [], [], []
        for ID in x['IDs']:
            y = dbs['core'][str(ID)]
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
                except Exception as e:
                    print(e, flush=True)
                    Messages.WebTrouble()
        corechanged = []
        if cords2 is not None:
                for cord in cords2:
                    corechanged.append(({'cord': cord}, cord['postcode']))
                cords += cords2
        for y in cords:
            countieslist.append(y['codes']['admin_county'])
        for y in countieslist:
            z = dbs['counties'][y]
            try:
                nums.append(int(z['MedianHousePrice']))
            except TypeError:
                pass
        try:
            x['housepriceavg'] = np.average(np.array(nums))
        except Exception:
            pass
        return (x, corechanged)

    def sizecheck(dbs, t):
            if 'trustsize' in x:
                return x
            x['trustsize'] = len(x['IDs'])
            return x

    def PCdist(dbs, t):
            if 'geormsd' in x:
                return x
            IDs = x['IDs']
            Postcodes = []
            cords2 = []
            for ID in IDs:
                try:
                    try:
                        IDData = dbs['core'][str(ID)]
                    except TypeError:
                        print(ID, flush=True)
                        raise
                    if 'cord' in IDData:
                        cords2.append(IDData['cord'])
                    Postcodes.append((ID, IDData[defs.PostCodeKey]))
                except KeyError:
                    raise
            cords3 = None
            if Postcodes != []:
                while True:
                    try:
                        cords3 = getpostcodes(Postcodes)
                        assert cords3 is not None
                        break
                    except Exception as e:
                        print(e, flush=True)
                        Messages.WebTrouble()
            corechanged = []
            if cords3 is not None:
                for cord in cords3:
                    corechanged.append(({'cord': cord}, cord['postcode']))
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
            return (x, corechanged)

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
    listofmats = dbs['table'].all()

    def running(dbs, funcs, mat):
        corechanged = []
        for func in funcs:
            mat, newchanged = func(dbs, mat)
            for changed in newchanged:
                changedkey = next(x for x, y in dbs['core'].items() if y[defs.PostCodeKey] == changed[1])
                dbs['core'][changedkey].update(changed[0])
                corechanged.append(dbs['core'][changedkey])
        return mat, corechanged

    coredict = {str(x.doc_id): x for x in dbs['core'].all()}
    countydict = {x['CountyCode']: x for x in dbs['counties'].all()}
    dictdbs = {'counties': countydict, 'core': coredict}
    listofmats = dbs['table'].all()

    with multiprocessing.pool.Pool() as p:
        funcs = []
        for x, y in process:
            if (x, y) == ('geo', 'rmsd'):
                funcs.append(PCdist)
            elif (x, y) == ('trust', 'size'):
                funcs.append(sizecheck)
            elif (x, y) == ('houseprice', 'avg'):
                funcs.append(pricecheck)
            else:
                funcs.append(operator(x, y))
        thefunction = partial(running, dictdbs)
        mapthing = p.imap_unordered(thefunction, listofmats)
        pcfactor = 100 / len(listofmats)
        for i, result, corechanged in enumerate(mapthing):
            submitchanged(result)
            for changed in corechanged:
                dbs['core'].update(changed, doc_id=changed.doc_id)
            pc = round(i * pcfactor)
            Messages.PROGRESS('Compiling Variables', pc)


    while done < 2:
        if all(not thread.is_alive() for thread in threads):
            done += 1
        try:
            thang = queue.get(timeout=2)
        except q.Empty as e:
            continue
        submitchanged(thang)
        inserted += 1
        pc = int(taskpcfactor * inserted)
        if pc != oldpc:
            Messages.PROGRESS('Compiling Variables', pc)
        oldpc = pc
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
