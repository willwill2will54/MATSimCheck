# Python modules, built-in
import sys
import random
import csv
import os
import itertools
import multiprocessing
from shlex import split as shlexsplit
from itertools import product
from collections import Counter
from functools import partial
# Python modules, install with pip
from tinydb import TinyDB
from gooey import Gooey, GooeyParser
# My stuff, included in package
import defaults as defs
import lib.messages as msg
from lib.testing import tester
from lib.importing import importer, MATList
from lib.misc import ensure_dir

_1 = sys.argv[0]
_2 = os.path.dirname(_1)
if _2 is not '':
    os.chdir(_2)

sys.setrecursionlimit(1500)

# Gooey automatically generates a GUI
@Gooey(program_name='MATSimCheck', image_dir='lib/img', monospace_display=True, progress_regex=r"^.+ is (\d+)% done$")
def main():
    # Open the databases
    noncore = TinyDB('./dbs/non_Core.json')
    MATs = TinyDB('./dbs/MATS.json')
    core = TinyDB('./dbs/Core.json')
    counties = TinyDB('./dbs/Counties.json')

    parser = GooeyParser(description='Find similar MATs.')
    subparsers = parser.add_subparsers(dest='action')

    similar = subparsers.add_parser('Similar', help='''\
        Finds the most similar MAT to the specified MATs''')

    req = similar.add_argument_group('Required')

    can = similar.add_argument_group('Can be left alone')

    whichmats = req.add_mutually_exclusive_group(required=True)

    whichmats.add_argument('-MATs', choices=MATList(), nargs='*', widget='Listbox',
                           help='Specifies MATs (hold cmd/ctrl to select multiple)')

    whichmats.add_argument('-All', action='store_true',
                           help='Analyses all MATs')

    can.add_argument('--algorithm', '-a', default='defaults', nargs='*', help='''\
        Configure the selection algorithm (optional)''',
                     gooey_options={'validator': {'test': "(user_input == 'defaults') or (all(b in ('avg', 'rmsd', 'med', 'rng', 'mode', 'size') and (c in ['wgt', 'is', 'isnot']\
 or c.endswith('gets')) for b, c in zip(user_input.split()[1::4], user_input.split()[2::4])) and len(user_input))",
                                                  'message': 'That is not a valid algorithm. See documentation.'}})

    subparsers.add_parser('Display', help='''\
        Displays datatables currently stored''')

    subparsers.add_parser('Purge', help='''\
            Purges the compiled databases.''')

    test = subparsers.add_parser('Test', help='''\
        Runs Testing Utililty''')

    can.add_argument('--multi', '-m', type=int, default=10, metavar='x', help='''\
        Displays x most similar MATs''')
    test.add_argument('--plural', '-p', type=int, default=20, metavar='x', help='''\
Splits this many of the MATs into 2.''')

    args = parser.parse_args()

    msg.SEP()
    if args.action == 'Purge':
        msg.PURGE()
        for x in [core, noncore, counties, MATs]:
            x.purge()
        MATs.purge_tables()
        msg.DONE()

    if args.action == 'Display':
        for x in MATs.tables():
            if not x == '_default':
                print(x.replace('|', ' '), flush=True)

    def doit(algorithm, tested, num, testing=False):
        if algorithm in (None, ['defaults', ], 'defaults'):
            algorithm = defs.algorithm
        if tested is not None:
            importkeys = []
            for a, b in zip(algorithm[:-3:4], algorithm[1:-2:4]):
                importkeys += [a, b]
            table = importer(importkeys, testing=testing)[0]
            retresults = []
            with multiprocessing.Pool() as pool:
                partthing = partial(tester, table, algorithm=algorithm, number=num, testing=testing)
                for result in pool.imap_unordered(partthing, tested):
                    print('{} is most similar to {}\n'.format(result[2], ' then '.join(result[0])), flush=True)
                    retresults.append((result[2], result[1]))
            if testing:
                return retresults
            else:
                with open('result.csv', 'w', encoding='utf-16') as resultsfile:
                    print('Writing results to file...', flush=True)
                    chain = itertools.chain.from_iterable
                    fields = sorted(list(chain(['Average ' + x, 'Subject ' + x] for x in defs.ProgressScoreHeaders)))
                    writer = csv.DictWriter(resultsfile, fieldnames=['MAT', ] + fields)
                    writer.writeheader()
                    rows = [{**{'MAT': x[0]}, **x[1][0], **x[1][1]} for x in retresults]
                    writer.writerows(rows)
                    msg.DONE()

    def testprep(matnum):
        for encoding in ['utf-8', 'utf-16', 'Windows-1252']:
            try:
                openfile = open(defs.CoreDirectory + '/core.csv', encoding=encoding)
                openfile.read()
                openfile.close()
                with open(defs.CoreDirectory + '/core.csv', newline='', encoding=encoding) as donor:
                    raw = csv.DictReader(donor, delimiter=',')
                    dicts = [dict(row) for row in raw]
                    break
            except UnicodeError:
                pass
        MATs = list(dicts)
        MATnames = tuple(x[defs.MatNameKey] for x in dicts)
        ValidMATS = [x for x, y in Counter(MATnames).items() if y >= 3]
        ChangeMATS = random.sample(ValidMATS, matnum)
        retChangeMATS = {}

        def MATtransform(x):
            tobe = x[defs.MatNameKey] in ChangeMATS
            mustbe = x[defs.MatNameKey] not in retChangeMATS.keys() or not retChangeMATS[x[defs.MatNameKey]][0]
            mustbe2 = x[defs.MatNameKey] not in retChangeMATS.keys() or retChangeMATS[x[defs.MatNameKey]][1] < 2
            if tobe and ((bool(random.getrandbits(1)) and not mustbe2) or mustbe):
                if x[defs.MatNameKey] in retChangeMATS:
                    retChangeMATS[x[defs.MatNameKey]][0] = True
                else:
                    retChangeMATS[x[defs.MatNameKey]] = [False, 0]
                x[defs.MatNameKey] += '1'
            elif tobe:
                retChangeMATS[x[defs.MatNameKey]][1] += 1
                x[defs.MatNameKey] += '2'
            return x

        random.shuffle(MATs)
        NewDicts = [MATtransform(x) for x in MATs]
        all_keys = set().union(*(d.keys() for d in NewDicts))
        ensure_dir('./special/test/core.csv')
        with open('./special/test/core.csv', mode='w', encoding='utf-16') as subject:
            writer = csv.DictWriter(subject, fieldnames=list(all_keys))
            writer.writeheader()
            writer.writerows(NewDicts)
        return list(x + '1' for x in retChangeMATS.keys())

    def experimentalfunc():
        testeds = testprep(args.plural)
        go = 0
        ensure_dir('special/testresults/result.csv')
        with open('special/testresults/result.csv', 'w', encoding='utf-16') as resultsfile:
            writer = csv.DictWriter(resultsfile, fieldnames=['a', 'b', 'c', 'd', 'e', 'position', 'score', 'MAT'])
            writer.writeheader()
            dictstobewritten = []
            algorithm = defs.TestAlgorithmMaker([list(x)[0] for x in defs.TestAlgorithmVariables])
            importkeys = []
            for a, b in zip(algorithm[:-3:4], algorithm[1:-2:4]):
                importkeys += [a, b]
            table = importer(importkeys, testing=True)
            if table[1]:
                MATs.purge_table(table[0])
            for var in product(*defs.TestAlgorithmVariables):
                go += 1
                algorithm = defs.TestAlgorithmMaker(var)
                results = doit(algorithm, testeds, 1, testing=True)
                msg.TRY(go)
                print(algorithm, flush=True)
                for resulthing in results:
                    done = False
                    for pos, thing in enumerate(resulthing[1]):
                        if thing[0].startswith(resulthing[0][:-1]) and thing[0].endswith('2'):
                            dicttobewritten = {'a': var[0], 'b': var[1], 'c': var[2], 'd': var[3], 'e': var[4],
                                               'position': pos, 'score': thing[1], 'MAT': thing[0]}
                            done = True
                            break
                    if done:
                        dictstobewritten.append(dicttobewritten)
            writer.writerows(dictstobewritten)

        print('\a')

    def normfunc():
        if args.All:
                args.MATs = MATList()
        elif type(args.algorithm) == str:
            args.algorithm = shlexsplit(args.algorithm)
        doit(args.algorithm, args.MATs, args.multi)

    if args.action != 'Purge':
        if args.action == 'Test':
            experimentalfunc()
        elif args.action == 'Similar':
            normfunc()


if __name__ == '__main__':
    main()
