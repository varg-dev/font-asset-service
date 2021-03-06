import os
import hashlib


RESULT_DIR=os.environ.get('RESULT_DIR', '/data/results')

def results_dir():
    directory = RESULT_DIR

    if not os.path.exists(directory):
        os.mkdir(directory)
    
    return directory


def fonts_dir():
    directory = os.path.join(results_dir(), 'fonts')

    if not os.path.exists(directory):
        os.mkdir(directory)
    
    return directory


def make_hash_sha256(o):
    hasher = hashlib.sha256()
    hasher.update(repr(make_hashable(o)).encode())
    return hasher.hexdigest()


def make_hashable(o):
    if isinstance(o, (tuple, list)):
        return tuple((make_hashable(e) for e in o))

    if isinstance(o, dict):
        return tuple(sorted((k,make_hashable(v)) for k,v in o.items()))

    if isinstance(o, (set, frozenset)):
        return tuple(sorted(make_hashable(e) for e in o))

    return o

