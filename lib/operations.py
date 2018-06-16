def operator(key, operation):
    import numpy as np
    from collections import Counter
    if operation == 'avg':
        def avg(x, key, dbs):
            if key + 'avg' in x:
                return (x, [])
            nums = []
            for ID in x['IDs']:
                nums.append(float(dbs['core'][str(ID)][key]))
            try:
                x[key + 'avg'] = np.average(np.array(nums))
            except Exception:
                pass
            return (x, [])
        func = lambda dbs, t: avg(t, key, dbs)
    elif operation == 'rmsd':
        def rmsd(x, key, dbs):
            if key + 'rmsd' in x:
                return (x, [])
            array = np.array([])
            nums = []
            for ID in x['IDs']:
                nums.append(float(dbs['core'][str(ID)][key]))
            array = np.append(array, nums)
            try:
                x[key + 'rmsd'] = np.std(array)
            except Exception:
                pass
            return (x, [])
        func = lambda dbs, t: rmsd(t, key, dbs)
    elif operation == 'mode':
        def mode(x, key, dbs):
            if key + 'mode' in x:
                return (x, [])
            stuff = [dbs['core'][str(ID)][key] for ID in x['IDs']]
            x[key + 'mode'] = Counter(stuff).most_common(1)[0][0]
            return (x, [])
        func = lambda dbs, t: mode(t, key, dbs)
    elif operation == 'rng':
        def rng(x, key, dbs):
            if key + 'rng' in x:
                return (x, [])
            stuff = [dbs['core'][str(ID)][key] for ID in x['IDs']]
            x[key + 'rng'] = max(stuff) - min(stuff)
            return (x, [])
        func = lambda dbs, t: rng(t, key, dbs)
    elif operation == 'med':
        def med(x, key, dbs):
            try:
                if key + 'med' in x:
                    return (x, [])
                nums = []
                for ID in x['IDs']:
                    nums.append(float(dbs['core'][str(ID)][key]))
                try:
                    x[key + 'med'] = np.median(np.array(nums))
                except Exception:
                    pass
            except Exception:
                pass
            return (x, [])
        func = lambda dbs, t: med(t, key, dbs)
    return func
