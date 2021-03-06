def _running(dbs, funcs, mat):
        import defaults as defs

        corechanged = []
        for func in funcs:
            mat, newchanged = func(dbs, mat)
            for changed in newchanged:
                changedkey = next(x for x, y in dbs['core'].items() if y[defs.PostCodeKey] == changed[1])
                dbs['core'][changedkey].update(changed[0])
                corechanged.append(dbs['core'][changedkey])
        return mat, corechanged


def importer(extras, testing=False):
    import lib.messages as Messages
    from lib.misc import getpostcodes
    from lib.operations import operator
    import defaults as defs
    import cProfile

    import pickle
    import multiprocess
    import numpy as np
    from os import listdir
    from functools import partial
    from tinydb import TinyDB, Query
    from tinydb.storages import JSONStorage
    from tinydb.middlewares import CachingMiddleware

    np.warnings.filterwarnings('ignore')
    np.seterr(all='raise')

    def submitchanged(thang):
        table.update(thang, doc_ids=[thang.doc_id, ])

    CachingStorage = CachingMiddleware
    CachingStorage.WRITE_CACHE_SIZE = 100
    noncore = TinyDB('./dbs/non_Core.json', storage=CachingStorage(JSONStorage))
    MATs = TinyDB('./dbs/MATS.json', storage=CachingStorage(JSONStorage))
    core = TinyDB('./dbs/Core.json', storage=CachingStorage(JSONStorage))
    district = TinyDB('./dbs/district.json', storage=CachingStorage(JSONStorage))

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
    dbs = {'noncore': noncore, 'MATs': MATs, 'core': core, 'district': district, 'table': table}
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
                    tablemap = {}
                    try:
                        with open("./dbs/urns.pickle", "rb") as f:
                            urns = pickle.load(f)
                    except Exception:
                        urns = {}
                    pr = cProfile.Profile()
                    pr.enable()
                    try:
                        for i, x in enumerate(dicts):
                            urn = x['URN']
                            if urn not in urns:
                                sid = core.insert(x)
                                if type(sid) == int:
                                    sid = [sid, ]
                                urns[urn] = sid
                            else:
                                sid = urns[urn]
                                if type(sid) == int:
                                    sid = [sid, ]
                                core.update(x, doc_ids=sid)
                            if x[defs.MatNameKey] in tablemap:
                                tablemap[x[defs.MatNameKey]]['IDs'] += sid
                            else:
                                tablemap[x[defs.MatNameKey]] = {"Trust name": x[defs.MatNameKey], "IDs": sid}
                            pc = int(((i + 1) / maxthing) * 100)
                            if pc != lastpc:
                                Messages.PROGRESS('Initialising school database', pc)
                                lastpc = pc
                    except KeyboardInterrupt:
                        pass
                    finally:
                        pr.disable()
                        pr.dump_stats('profile.out')
                    with open("./dbs/urns.pickle", "wb") as f:
                        pickle.dump(urns, f)
                    maxthing = len(tablemap)
                    for i, x in enumerate(tablemap.values()):
                        table.upsert(x, Query()["Trust name"] == x["Trust name"])
                        pc = int(((i + 1) / maxthing) * 100)
                        if pc != lastpc:
                            Messages.PROGRESS('Saving school database', pc)
                            lastpc = pc
            except UnicodeError:
                pass
            else:
                break
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
                        to_delete = set(x.keys()).difference(extras2)
                        for d in to_delete:
                            del x[d]
                        if urn in urns:
                            noncore.upsert(x, Query().URN == urn)
                            core.update(x, Query().URN == urn)
                        else:
                            core.upsert(x, Query().URN == urn)
                        pc = int(((i + 1) / maxthing) * 100)
                        if pc != lastpc:
                            Messages.PROGRESS('This', pc)
                            lastpc = pc
            except UnicodeError:
                pass
            else:
                break
        Messages.PROGRESS('This', 100)
    with open('./special/HousePrices.csv') as openfile:
        raw = csv.DictReader(openfile, delimiter=',')
        dicts = [dict(row) for row in raw]
        district.purge()
        district.insert_multiple(dicts)

    def lentest(t):
        return len(t) == 1

    table.remove(Query().IDs.test(lentest))
    Messages.PARGS()

    def pricecheck(dbs, x):

        districtlist, nums, cords, postcodes = [], [], [], []
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
            districtlist.append(y['codes']['admin_district'])
        for y in districtlist:
            z = dbs['district'][y]
            try:
                if type(z['MedianHousePrice']) is str:
                    z['MedianHousePrice'] = z['MedianHousePrice'].replace(',', '')
                nums.append(int(z['MedianHousePrice']))
            except TypeError:
                pass
        try:
            x['housepriceavg'] = np.average(np.array(nums))
        except Exception:
            pass
        return (x, corechanged)

    def sizecheck(dbs, x):
            if 'trustsize' in x:
                return x
            x['trustsize'] = len(x['IDs'])
            return (x, ())

    def PCdist(dbs, x):
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
    listofmats = dbs['table'].all()

    coredict = {str(x.doc_id): x for x in dbs['core'].all()}
    districtdict = {x['LACode']: x for x in dbs['district'].all()}
    dictdbs = {'district': districtdict, 'core': coredict}
    listofmats = dbs['table'].all()

    with multiprocess.Pool(processes=defs.threadcount) as p:
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
        thefunction = partial(_running, dictdbs, funcs)
        mapthing = p.imap_unordered(thefunction, listofmats)
        pcfactor = 100 / len(listofmats)
        oldpc = 0
        pc = 0
        Messages.PROGRESS('Compiling Variables', pc)
        for i, thang in enumerate(mapthing):
            result, corechanged = thang[0], thang[1]
            submitchanged(result)
            for changed in corechanged:
                dbs['core'].update(changed, doc_ids=[changed.doc_id, ])
            pc = round((i + 1) * pcfactor)
            if pc != oldpc:
                Messages.PROGRESS('Compiling Variables', pc)
            oldpc = pc

    for x in [noncore, MATs, core, district]:
        x.close()
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
