#!/usr/bin/env python

import argparse
import subprocess
from subprocess import check_call
import re
import os
from threading import Thread, Lock
from os.path import relpath
from timeit import default_timer as timer
import collections

import sys
is_py2 = sys.version[0] == '2'
if is_py2:
    import Queue as queue
else:
    import queue as queue


p = argparse.ArgumentParser()
p.add_argument('-t', '--threads', type=int, default=2)
arg = p.parse_args()

models = ('JC69',)
datasets = ('DS1', 'DS2', 'DS3', 'DS3s', 'DS4', 'DS5')
rootdir = os.getcwd()
bindir = os.path.join(rootdir, 'bin')
templatedir = os.path.join(rootdir, 'templates')
datadir = os.path.join(rootdir, 'data')

physher = 'physher'

pattern_time = re.compile(r'Time: (\d+\.\d+)')

# fast methods
fast = {'map', 'ml', 'vbis', 'vb', 'laplace-gamma', 'laplace-beta', 'laplace-lognormal', 'laplacis', 'nmc'}


def convert_trees(dpath, dataset, outputpath):
    count = 0
    srf = []
    with open(os.path.join(outputpath, dataset + '.trees'), 'w') as writer:
        with open(os.path.join(dpath, 'JC_no_gamma_credible_set_' + dataset.lower()), 'r') as fp:
            for line in fp:
                line = line.rstrip('\n').rstrip('\r')
                if line == '':
                    continue
                pp, tree = re.split(r'\s', line)
                srf.append(pp)
                writer.write(tree + '\n')
                count += 1

    with open(os.path.join(outputpath, 'data.csv'), 'w') as writer:
        writer.write('tree\tSRF\n')
        for idx, pp in enumerate(srf):
            writer.write('{}\t{}\n'.format(idx, pp))


def parse_ml(file_path):
    pattern = re.compile(r'treelikelihood: (-\d+\.\d+)')
    with open(file_path, 'r') as fp:
        for line in fp:
            line = line.rstrip('\n').rstrip('\r')
            m = pattern.match(line)
            mt = pattern_time.match(line)
            if m:
                result = {'LL': m.group(1), 'method': 'ML'}
            elif mt:
                result['time'] = mt.group(1)
    return result


def parse_map(file_path):
    pattern = re.compile(r'posterior: (-\d+\.\d+)')
    with open(file_path, 'r') as fp:
        for line in fp:
            line = line.rstrip('\n').rstrip('\r')
            m = pattern.match(line)
            mt = pattern_time.match(line)
            if m:
                result = {'LL': m.group(1), 'method': 'MAP'}
            elif mt:
                result['time'] = mt.group(1)
    return result


def parse_vb(file_path):
    pattern_elbo = re.compile(r'\d+ ELBO: (-\d+\.\d+)')
    pattern_is = re.compile(r'Marginal likelihood using (?:VB|IS): (-\d+\.\d+)')  # VB IS
    with open(file_path, 'r') as fp:
        for line in fp:
            line = line.rstrip('\n').rstrip('\r')
            melbo = pattern_elbo.match(line)
            mvbis = pattern_is.match(line)
            mt = pattern_time.match(line)
            if melbo:
                result = {'LL': melbo.group(1), 'method': 'ELBO'}
            if mvbis:
                result = {'LL': mvbis.group(1), 'method': 'VBIS'}
            elif mt:
                result['time'] = mt.group(1)
    return result


def parse_laplace_is(file_path):
    pattern_laplace = re.compile(r"(\w+'?\sLaplace): (-\d+\.\d+)")
    pattern_is = re.compile(r'Marginal likelihood using (?:VB|IS): (-\d+\.\d+)')  # IS
    with open(file_path, 'r') as fp:
        for line in fp:
            line = line.rstrip('\n').rstrip('\r')
            mlaplace = pattern_laplace.match(line)
            mlaplacis = pattern_is.match(line)
            mt = pattern_time.match(line)
            if mlaplace:
                first_letter = mlaplace.group(1)[0]
            if mlaplacis:
                result = {'LL': mlaplacis.group(1), 'method': first_letter + 'LIS'}
            elif mt:
                result['time'] = mt.group(1)
    return result


def parse_pred(filepath):
    pattern_llpd = re.compile(r'l[lp]pd: (-\d+\.\d+)')
    pattern_cpo = re.compile(r'logCPO: (-\d+\.\d+)')
    with open(filepath, 'r') as fp:
        for line in fp:
            line = line.rstrip('\n').rstrip('\r')
            mcpo = pattern_cpo.match(line)
            mllpd = pattern_llpd.match(line)
            mt = pattern_time.match(line)
            if mcpo:
                result = {'LL': mcpo.group(1), 'method': 'CPO'}
            elif mllpd:
                result = {'LL': mllpd.group(1), 'method': 'LPPD'}
            elif mt:
                result['time'] = mt.group(1)
    return result


def parse_nested(filepath):
    pattern_nested = re.compile(r'logZ: (-\d+\.\d+)')
    with open(filepath, 'r') as fp:
        for line in fp:
            line = line.rstrip('\n').rstrip('\r')
            mlogz = pattern_nested.match(line)
            if mlogz:
                result = {'LL': mlogz.group(1), 'method': 'NS'}
        result['time'] = line.split(' ')[1]
    return result


def parsers(filepath):
    pattern_shm = re.compile(r'Smoothed harmonic mean: (-\d+\.\d+)')
    pattern_hm = re.compile(r'Harmonic mean: (-\d+\.\d+)')
    pattern_ss = re.compile(r'Stepping stone marginal likelihood: (-\d+\.\d+)')
    pattern_ps = re.compile(r'Path sampling marginal likelihood: (-\d+\.\d+)')
    pattern_ps2 = re.compile(r'Modified Path sampling marginal likelihood: (-\d+\.\d+)')
    pattern_bridge = re.compile(r'Bridge sampling: (-\d+\.\d+)')
    pattern_naive = re.compile(r'Naive arithmetic mean: (-\d+\.\d+)')  # sample from prior
    pattern_gss = re.compile(r'^Generalized stepping stone marginal likelihood: (-\d+\.\d+)')
    pattern_laplace = re.compile(r"(\w+'?\sLaplace): (-\d+\.\d+|nan)")
    pattern_mc = re.compile(r"Monte Carlo: (-\d+\.\d+)")

    with open(filepath, 'r') as fp:
        for line in fp:
            line = line.rstrip('\n').rstrip('\r')
            mhm = pattern_hm.match(line)
            mshm = pattern_shm.match(line)
            mn = pattern_naive.match(line)
            mss = pattern_ss.match(line)
            mps = pattern_ps.match(line)
            mps2 = pattern_ps2.match(line)
            mbs = pattern_bridge.match(line)
            mgss = pattern_gss.match(line)
            mlaplace = pattern_laplace.match(line)
            mmc = pattern_mc.match(line)
            mt = pattern_time.match(line)

            if mhm:
                result = {'LL': mhm.group(1), 'method': 'HM'}
            elif mshm:
                result = {'LL': mshm.group(1), 'method': 'SHM'}
            elif mn:
                result = {'LL': mn.group(1), 'method': 'MN'}
            elif mss:
                result = {'LL': mss.group(1), 'method': 'SS'}
            elif mps:
                result = {'LL': mps.group(1), 'method': 'PS'}
            elif mps2:
                result = {'LL': mps2.group(1), 'method': 'PS2'}
            elif mbs:
                result = {'LL': mbs.group(1), 'method': 'BS'}
            elif mgss:
                result = {'LL': mgss.group(1), 'method': 'GSS'}
            elif mlaplace:
                result = {'LL': mlaplace.group(2), 'method': mlaplace.group(1)[0] + 'L'}
            elif mmc:
                result = {'LL': mmc.group(1), 'method': 'NMC'}
            elif mt:
                result['time'] = mt.group(1)

    return result


analyses2 = {
    'map': {'parser': parse_map},
    'ml': {'parser': parse_ml},
    'mcmc': {'parser': None},
    'mmcmc': {'parser': None},
    'mmcmc-gss': {'parser': None},
    'vbis': {'parser': parse_vb},
    'vb': {'parser': parse_vb},
    'nested': {'parser': parse_nested},
    'bridge': {'parser': parsers, 'logfilepath': 'mcmc'},
    'hm': {'parser': parsers, 'logfilepath': 'mcmc'},
    'shm': {'parser': parsers, 'logfilepath': 'mcmc'},
    'gss': {'parser': parsers, 'logfilepath': 'mmcmc-gss'},
    'ss': {'parser': parsers, 'logfilepath': 'mmcmc'},
    'ps': {'parser': parsers, 'logfilepath': 'mmcmc'},
    'ps2': {'parser': parsers, 'logfilepath': 'mmcmc'},
    'laplace-gamma': {'parser': parsers},
    'laplace-beta': {'parser': parsers},
    'laplace-lognormal': {'parser': parsers},
    'laplacis': {'parser': parse_laplace_is},
    'cpo': {'parser': parse_pred, 'logfilepath2': 'mcmc'},
    'lppd': {'parser': parse_pred, 'logfilepath2': 'mcmc'},
    'nmc': {'parser': parsers}
}

analyses = collections.OrderedDict(sorted(analyses2.items(), key=lambda x: 'logfilepath' in x[1] or 'logfilepath2' in x[1]))


class Worker(Thread):
    def __init__(self, qq, dataset, datadir, analysis_dir):
        Thread.__init__(self)
        self.queue = qq
        self.dataset = dataset
        self.analysis_dir = analysis_dir
        self.datadir = datadir

    def run(self):
        while not self.queue.empty():

            index = self.queue.get()

            with open(os.path.join(dataset_dir, dataset + '.trees'), 'r') as fp:
                count = 0
                for tree in fp:
                    tree = tree.rstrip('\n').rstrip('\r')
                    if count == index:
                        break
                    count += 1

            json_file = 'tree' + str(index) + '.json'
            log_file = 'tree' + str(index) + '.log'
            aln_file = self.dataset + '.nex'

            json_file_path = os.path.join(self.analysis_dir, json_file)
            aln_file_path = os.path.join(self.datadir, aln_file)
            aln_file_rel_path = relpath(aln_file_path, analysis_dir)

            if 'logfilepath' in analyses[analysis]:
                log_file = os.path.join('..', analyses[analysis]['logfilepath'], log_file)
            elif 'logfilepath2' in analyses[analysis]:
                log_file = os.path.join('..', analyses[analysis]['logfilepath2'], 'pll-' + log_file)

            # write json file (e.g. tree0.json)
            with open(json_file_path, 'w') as jsonf:
                json_local = json_template.replace('TREE_TEMPLATE', tree).replace('LOG_TEMPLATE', log_file).replace(
                    'DATA_TEMPLATE', aln_file_rel_path).replace('SEED', str(index))
                jsonf.write(json_local)

            outfile = os.path.join(analysis_dir, "tree" + str(index) + '.txt')
            start = timer()
            try:
                f = open(outfile, 'w')
                # err = open("tree" + str(count) + '.err.txt', 'w')
                print(' '.join([physher, json_file]))
                check_call([physher, json_file], stdout=f, cwd=analysis_dir)
            except subprocess.CalledProcessError as e:
                pass
            end = timer()
            total_time = end - start
#            print('Time: {}'.format(total_time))
            with open(outfile, 'a') as pp:
                pp.write('Time: {}'.format(total_time))

            if analyses[analysis]['parser'] is not None:
                results = analyses[analysis]['parser'](outfile)
                lock.acquire()
                print(results)
                result_file.write(str(index) + '\t' + results['method'] + '\t' + results['LL'] + '\t' + results['time'] + '\n')
                master_file.write(str(index) + '\t' + results['method'] + '\t' + results['LL'] + '\t' + results['time'] + '\n')
                lock.release()
            else:
                lock.acquire()
                with open(outfile, 'r') as fp:
                    for line in fp:
                        pass
                    time = line.rstrip('\n').rstrip('\r').split(' ')[1]
                    result_file.write(str(index) + '\t' + analysis + '\tNA\t' + time + '\n')
                    master_file.write(str(index) + '\t' + analysis + '\tNA\t' + time + '\n')
                lock.release()

            self.queue.task_done()


for dataset in datasets:
    dataset_dir = os.path.join(rootdir, dataset)

    if not os.path.lexists(dataset_dir):
        os.mkdir(dataset_dir)

    # Save trees in dataset folder and create SRF file
    convert_trees(datadir, dataset, dataset_dir)

    master_file = open(os.path.join(dataset_dir, dataset) + '.csv', 'w')
    master_file.write('tree\talgorithm\tmarginal\ttime\n')

    for model in models:

        for analysis in analyses:
            print(analysis)
            start = timer()
            analysis_dir = os.path.join(dataset_dir, analysis)
            if not os.path.lexists(analysis_dir):
                os.mkdir(analysis_dir)

            lock = Lock()

            result_file = open(os.path.join(analysis_dir, 'data.csv'), 'w')

            result_file.write('tree\talgorithm\tmarginal\ttime\n')

            # read template (e.g JC69-mcmc.json)
            with open(os.path.join(templatedir, model + '-' + analysis + '.json'), 'r') as f:
                json_template = f.read()

            qq = queue.Queue()

            maximum = float('inf')
            if dataset == 'DS5':
                maximum = 1000
                if analysis in fast:
                    maximum = 10000

            total = 0
            with open(os.path.join(dataset_dir, dataset + '.trees'), 'r') as f:
                for i, l in enumerate(f):
                    qq.put(i)
                    total += 1
                    if total == maximum:
                        break

            for _ in range(min(total, arg.threads)):
                worker = Worker(qq, dataset, datadir, analysis_dir)
                worker.daemon = True
                worker.start()

            qq.join()

            end = timer()
            total_time = end - start
            print('Time: {}'.format(total_time))

            result_file.close()
    master_file.close()
