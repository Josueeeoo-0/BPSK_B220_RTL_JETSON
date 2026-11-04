#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: simulation_bpsk
# GNU Radio version: 3.10.12.0

from gnuradio import blocks
import pmt
from gnuradio import digital
import threading
from gnuradio import gr
from gnuradio.filter import firdes
from gnuradio.fft import window
import sys
import signal
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation




class tx_usrp(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "simulation_bpsk", catch_exceptions=True)

        ##################################################
        # Blocks
        ##################################################

        self.digital_constellation_decoder_cb_0 = digital.constellation_decoder_cb(digital.constellation_bpsk().base())
        self.digital_chunks_to_symbols_xx_0 = digital.chunks_to_symbols_bc([-1+0j, 1+0j], 1)
        self.blocks_file_source_0 = blocks.file_source(gr.sizeof_char*1, str(Path.home() / 'sdr-alertas' / 'datos' / 'bpsk_tx.u8'), False, 0, 0)
        self.blocks_file_source_0.set_begin_tag(pmt.PMT_NIL)
        self.blocks_file_sink_0 = blocks.file_sink(gr.sizeof_char*1, str(Path.home() / 'sdr-alertas' / 'datos' / 'bpsk_rx.u8'), False)
        self.blocks_file_sink_0.set_unbuffered(False)


        ##################################################
        # Connections
        ##################################################
        self.connect((self.blocks_file_source_0, 0), (self.digital_chunks_to_symbols_xx_0, 0))
        self.connect((self.digital_chunks_to_symbols_xx_0, 0), (self.digital_constellation_decoder_cb_0, 0))
        self.connect((self.digital_constellation_decoder_cb_0, 0), (self.blocks_file_sink_0, 0))





def main(top_block_cls=tx_usrp, options=None):
    tb = top_block_cls()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        sys.exit(0)

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    tb.start()

    tb.wait()


if __name__ == '__main__':
    main()
