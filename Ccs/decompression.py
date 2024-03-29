import logging
import numpy as np
import os
import subprocess
import threading
import time
import astropy.io.fits as pyfits

import confignator
import ccs_function_lib as cfl

cfg = confignator.get_config(check_interpolation=False)
logger = cfl.start_logging('Decompression')
# logger.setLevel(getattr(logging, cfg.get('ccs-logging', 'level').upper()))

CE_COLLECT_TIMEOUT = 1
LDT_MINIMUM_CE_GAP = 0.001

ce_decompressors = {}


def create_fits(header=None, filename=None):
    hdulist = pyfits.HDUList()
    hdu = pyfits.PrimaryHDU()
    hdu.header = header
    hdulist.append(hdu)

    imagette_hdu = pyfits.ImageHDU()
    stack_hdu = pyfits.ImageHDU()
    margins = pyfits.ImageHDU()

    hdulist.append(imagette_hdu)
    hdulist.append(stack_hdu)
    hdulist.append(margins)

    if filename:
        with open(filename, "wb") as fd:
            hdulist.writeto(fd)

    return hdulist


def build_fits(basefits, newfits):
    base = pyfits.open(basefits)
    new = pyfits.open(newfits)
    for hdu in range(len(base)):
        base[hdu].data = np.concatenate([base[hdu].data, new[hdu].data])
    base.writeto(basefits, overwrite=True)


def convert_fullframe_to_cheopssim(fname):
    """
    Convert a fullframe (1076x1033) FITS to CHEOPS-SIM format
    @param fname: Input FITS file
    """
    d = pyfits.open(fname)
    full = np.array(np.round(d[0].data), dtype=np.uint16)
    win_dict = {"SubArray": full[:, :1024, 28:28+1024],
                "OverscanLeftImage": full[:, :1024, :4],
                "BlankLeftImage": full[:, :1024, 4:4+8],
                "DarkLeftImage": full[:, :1024, 12:28],
                "DarkRightImage": full[:, :1024, 1052:1052+16],
                "BlankRightImage": full[:, :1024, 1068:],
                "DarkTopImage": full[:, 1024:-6, 28:-24],
                "OverscanTopImage": full[:, -6:, 28:-24]}

    hdulist = pyfits.HDUList()
    hdulist.append(pyfits.PrimaryHDU())

    for win in win_dict:
        hdu = pyfits.ImageHDU(data=win_dict[win], name=win)
        hdulist.append(hdu)

    hdulist.append(pyfits.BinTableHDU(name="ImageMetaData"))

    hdulist.writeto(fname[:-5] + '_CHEOPSSIM.fits')


def ce_decompress(pool_name, outdir, sdu=None, starttime=None, endtime=None, startidx=None, endidx=None,
                  ce_exec=None, check_s13_consistency=True):
    decomp = CeDecompress(pool_name, outdir, sdu=sdu, starttime=starttime, endtime=endtime, startidx=startidx,
                          endidx=endidx, ce_exec=ce_exec, check_s13_consistency=check_s13_consistency)
    decomp.start()


def ce_decompress_stop(name=None):

    if name is not None:
        ce_decompressors[name].stop()
    else:
        for p in ce_decompressors:
            ce_decompressors[p].stop()


class CeDecompress:

    def __init__(self, pool_name, outdir, sdu=None, starttime=None, endtime=None, startidx=None, endidx=None,
                 ce_exec=None, check_s13_consistency=True, verbose=True):
        self.outdir = outdir
        self.pool_name = pool_name
        self.sdu = sdu
        self.starttime = starttime
        self.endtime = endtime
        self.startidx = startidx
        self.endidx = endidx
        self.check_s13_consistency = check_s13_consistency
        self.verbose = verbose

        self.init_time = int(time.time())

        if ce_exec is None:
            try:
                self.ce_exec = cfg.get('ccs-misc', 'ce_exec')
            except (ValueError, confignator.config.configparser.NoOptionError) as err:
                raise err
        else:
            self.ce_exec = ce_exec

        # check if decompression is executable
        if not os.access(self.ce_exec, os.X_OK):
            raise PermissionError('"{}" is not executable.'.format(self.ce_exec))

        self.ce_decompression_on = False
        self.ce_thread = None
        self.last_ce_time = 0
        self.ce_collect_timeout = CE_COLLECT_TIMEOUT
        self.ldt_minimum_ce_gap = LDT_MINIMUM_CE_GAP

    def _ce_decompress(self):
        checkdir = os.path.abspath(self.outdir)
        if not os.path.isdir(checkdir):  # and checkdir != "":
            # os.mkdir(checkdir)
            raise NotADirectoryError('{} is not a directory/does not exist.'.format(checkdir))

        self.ce_thread = threading.Thread(target=self._ce_decompress_worker, name="CeDecompression_{}".format(self.init_time))
        self.ce_thread.daemon = True
        if self.starttime is not None:
            self.last_ce_time = self.starttime
        self.ce_decompression_on = True

        try:
            self.ce_thread.start()
            logger.info('Started CeDecompress [{}]...'.format(self.init_time))
        except Exception as err:
            logger.error(err)
            self.ce_decompression_on = False
            raise err

    def _ce_decompress_worker(self):

        def decompress(cefile):
            logger.info("Decompressing {}".format(cefile))
            fitspath = cefile[:-2] + 'fits'
            if os.path.isfile(fitspath):
                subprocess.run(["rm", fitspath])
            with open(cefile[:-2] + 'log', 'w') as logfd:
                subprocess.run([self.ce_exec, cefile, fitspath], stdout=logfd, stderr=logfd)

        # first, get all TM13s already complete in pool
        try:
            filedict = cfl.dump_large_data(pool_name=self.pool_name, starttime=self.last_ce_time, endtime=self.endtime,
                                           outdir=self.outdir, dump_all=True, sdu=self.sdu, startidx=self.startidx,
                                           endidx=self.endidx, consistency_check=self.check_s13_consistency,
                                           verbose=self.verbose)
            for ce in filedict:
                decompress(filedict[ce])
                self.last_ce_time = ce

            self.last_ce_time += self.ldt_minimum_ce_gap

        except (ValueError, TypeError, AttributeError) as err:
            ce_decompressors.pop(self.init_time)
            raise err

        while self.ce_decompression_on:
            filedict = cfl.dump_large_data(pool_name=self.pool_name, starttime=self.last_ce_time, endtime=self.endtime,
                                           outdir=self.outdir, dump_all=True, sdu=self.sdu, startidx=self.startidx,
                                           endidx=self.endidx, consistency_check=self.check_s13_consistency,
                                           verbose=self.verbose)
            if len(filedict) == 0:
                time.sleep(self.ce_collect_timeout)
                continue

            for ce in filedict:
                self.last_ce_time, cefile = ce, filedict[ce]
                decompress(cefile)

                if not self.ce_decompression_on:
                    break

            # self.last_ce_time, cefile = list(filedict.items())[0]
            # decompress(cefile)
            self.last_ce_time += self.ldt_minimum_ce_gap
            time.sleep(self.ce_collect_timeout)
        logger.info('CeDecompress stopped [{}].'.format(self.init_time))
        ce_decompressors.pop(self.init_time)

    def start(self):
        self._ce_decompress()

        global ce_decompressors
        ce_decompressors[self.init_time] = self

    def stop(self):
        self.ce_decompression_on = False

    def reset(self, timestamp=0):
        self.last_ce_time = timestamp
