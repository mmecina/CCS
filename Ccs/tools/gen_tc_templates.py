#!/usr/bin/env python

import datetime
import sys

sys.path.append('..')

import ccs_function_lib as cfl


def export(outfile, sep):
    # project = cfl.project.split('_')[-1]
    mib = cfl.scoped_session_idb.get_bind().url.database
    date = datetime.datetime.now().strftime('%Y-%m-%d')
    vers = '{}.{}'.format(*cfl.scoped_session_idb.execute('select * from vdf').fetchall()[0][3:])

    header = '# TC templates generated from schema {} (VDF:{})\n# Date: {}\n\n'.format(mib, vers, date)

    temps = []
    for tc in cfl.get_tc_list():
        temps.append(cfl.make_tc_template(tc[1], pool_name='LIVE', add_parcfg=True))

    with open(outfile, 'w') as fd:
        fd.write(header + sep.join(temps))

    print('TC templates exported from {} to {}.'.format(mib, outfile))


if __name__ == '__main__':
    if '--breakpoints' in sys.argv:
        sep = '\n#! CCS.BREAKPOINT\n\n'
        sys.argv.remove('--breakpoints')
    else:
        sep = '\n\n'

    outfile = sys.argv[1]
    export(outfile, sep)
