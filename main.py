#!/usr/bin/env python3
import sys
import random
import csv
from shlex import split as shlexsplit
import os
from itertools import product
from collections import Counter
from tinydb import TinyDB
from pprint import pprint
import defaults as defs
from lib.testing import tester
from lib.importing import importer, MATList
from lib.misc import ensure_dir
import time
from gooey import Gooey, GooeyParser
import itertools

_1 = sys.argv[0]
_2 = os.path.dirname(_1)
if _2 is not '':
    os.chdir(_2)


@Gooey(program_name='MATSimCheck', image_dir='lib', monospace_display=True)
def main():
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

    if args.action == 'Purge':
        print("Purging all databases...")
        for x in [core, noncore, counties, MATs]:
            x.purge()
        MATs.purge_tables()
        time.sleep(1)
        print('Done!')

    if args.action == 'Display':
        for x in MATs.tables():
            if not x == '_default':
                print(x.replace('|', ' '))

    def doit(algorithm, tested, num, testing=False):
        if algorithm in (None, ['defaults', ], 'defaults'):
            algorithm = defs.algorithm
        if tested is not None:
            importkeys = []
            for a, b in zip(algorithm[:-3:4], algorithm[1:-2:4]):
                importkeys += [a, b]
            table = importer(importkeys, testing=testing)[0]
            results = []
            print(table)
            for x in tested:
                result = tester(x, table, algorithm=algorithm, number=num, testing=testing)
                print('{} is most similar to {}'.format(x, ' then '.join(result[0])))
                results.append((x, result[1]))
            if testing:
                return results
            else:
                with open('result.csv', 'w', encoding='utf-16') as resultsfile:
                    print('Writing results to file...')
                    writer = csv.DictWriter(resultsfile,
                    fieldnames=['MAT', ] + sorted(list(itertools.chain.from_iterable(['Average ' + x, 'Subject ' + x] for x in defs.ProgressScoreHeaders))))
                    writer.writeheader()
                    writer.writerows([{**{'MAT': x[0]}, **x[1][0], **x[1][1]} for x in results])
                    print('Done!')

    def testprep(matnum):
        for encoding in ['utf-8', 'utf-16', 'Windows-1252']:
            try:
                openfile = open(defs.CoreDirectory + '/Core.csv', encoding=encoding)
                openfile.read()
                openfile.close()
                with open(defs.CoreDirectory + '/Core.csv', newline='', encoding=encoding) as donor:
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

    if args.action != 'Purge':
        if args.action == 'Test':
            testeds = testprep(args.plural)
            go = 0
            ensure_dir('special/testresults/result.csv')
            with open('special/testresults/result.csv', 'w', encoding='utf-16') as resultsfile:
                writer = csv.DictWriter(resultsfile, fieldnames=['a', 'b', 'c', 'd', 'e', 'position', 'score', 'MAT'])
                writer.writeheader()
                dictstobewritten = []
                algorithm = defs.TestAlgorithmMaker((tuple(x)[0] for x in defs.TestAlgorithmVariables))
                importkeys = []
                for a, b in zip(algorithm[:-3:4], algorithm[1:-2:4]):
                    importkeys += [a, b]
                table = importer(importkeys, testing=True)
                if table[1]:
                    MATs.purge_table(table[0])
                for var in product(defs.TestAlgorithmVariables):
                    go += 1
                    algorithm = defs.TestAlgorithmMaker(var)
                    results = doit(algorithm, testeds, 1, testing=True)
                    print('\nTry {}'.format(go))
                    print(algorithm)
                    for resulthing in results:
                        pprint(resulthing[0])
                        done = False
                        for pos, thing in enumerate(resulthing[1]):
                            if thing[0].startswith(resulthing[0][:-1]) and thing[0].endswith('2'):
                                dicttobewritten = {'a': var[0], 'b': var[1], 'c': var[2], 'd': var[3], 'e': var[4],
                                                   'position': pos, 'score': thing[1], 'MAT': thing[0]}
                                done = True
                                break
                        if done:
                            print(dicttobewritten)
                            dictstobewritten.append(dicttobewritten)
                writer.writerows(dictstobewritten)

            print('\a')
        elif args.action == 'Similar':
            if args.All:
                args.MATs = MATList()
            if type(args.algorithm) == str:
                args.algorithm = shlexsplit(args.algorithm)
            doit(args.algorithm, args.MATs, args.multi)


main()