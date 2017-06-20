#!/usr/bin/env python
# -*- coding: utf-8 -*-
##################################################
# GNU Radio Python Flow Graph
# Title: METEOR-M2 receiver
# Author: Giovanni Vandelannoote
# Description: Outputs demodulated bitstream of METEOR-M weathersatellite
# Generated: Sun Apr 02 00:56:48 2017
##################################################

from datetime import datetime
from gnuradio import analog
from gnuradio import blocks
from gnuradio import digital
from gnuradio import eng_notation
from gnuradio import filter
from gnuradio import gr
from gnuradio.eng_option import eng_option
from gnuradio.filter import firdes
from optparse import OptionParser
import osmosdr
import time


class METEOR_M2_v04_noGUI(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self, "METEOR-M2 receiver")

        ##################################################
        # Variables
        ##################################################
        self.symb_rate = symb_rate = 72e3
        self.samp_rate = samp_rate = 960e3
        self.decimation = decimation = 4
        self.samp_per_sym = samp_per_sym = samp_rate/decimation/symb_rate
        self.clock_alpha = clock_alpha = 30e-3
        self.bitstream_name = bitstream_name = "/home/pi/Projects/Python_projects/Meteor_receiver/Data/meteor_LRPT_" + datetime.now().strftime("%d%m%Y_%H%M") + ".s"
        self.Tuning_offset = Tuning_offset = 300e3
        self.LO_freq = LO_freq = 137.903e6
        self.BPF_width = BPF_width = 140e3

        ##################################################
        # Blocks
        ##################################################
        self.rtlsdr_source_0 = osmosdr.source( args="numchan=" + str(1) + " " + '' )
        self.rtlsdr_source_0.set_sample_rate(samp_rate)
        self.rtlsdr_source_0.set_center_freq(LO_freq-Tuning_offset, 0)
        self.rtlsdr_source_0.set_freq_corr(0, 0)
        self.rtlsdr_source_0.set_dc_offset_mode(2, 0)
        self.rtlsdr_source_0.set_iq_balance_mode(2, 0)
        self.rtlsdr_source_0.set_gain_mode(False, 0)
        self.rtlsdr_source_0.set_gain(42, 0)
        self.rtlsdr_source_0.set_if_gain(20, 0)
        self.rtlsdr_source_0.set_bb_gain(10, 0)
        self.rtlsdr_source_0.set_antenna('', 0)
        self.rtlsdr_source_0.set_bandwidth(0, 0)

        self.root_raised_cosine_filter_0 = filter.fir_filter_ccf(1, firdes.root_raised_cosine(
        	1, samp_rate/decimation, symb_rate, 0.3, 361))
        self.freq_xlating_fir_filter_xxx_0 = filter.freq_xlating_fir_filter_ccc(decimation, (firdes.low_pass(1,samp_rate,BPF_width/2,20e3)), Tuning_offset, samp_rate)
        (self.freq_xlating_fir_filter_xxx_0).set_processor_affinity([0])
        self.digital_costas_loop_cc_0 = digital.costas_loop_cc(1e-3, 4)
        (self.digital_costas_loop_cc_0).set_processor_affinity([1])
        self.digital_constellation_soft_decoder_cf_1 = digital.constellation_soft_decoder_cf(digital.constellation_calcdist(([-1-1j, -1+1j, 1+1j, 1-1j]), ([0, 1, 3, 2]), 4, 1).base())
        self.digital_clock_recovery_mm_xx_0 = digital.clock_recovery_mm_cc(samp_per_sym*(1+0.0), clock_alpha**2/4.0, 0.5, clock_alpha, 0.005)
        (self.digital_clock_recovery_mm_xx_0).set_processor_affinity([2])
        self.blocks_float_to_char_0 = blocks.float_to_char(1, 127)
        self.blocks_file_sink_0_0 = blocks.file_sink(gr.sizeof_char*1, bitstream_name, False)
        self.blocks_file_sink_0_0.set_unbuffered(False)
        self.analog_rail_ff_0 = analog.rail_ff(-1, 1)
        self.analog_agc_xx_0 = analog.agc_cc(1000e-4, 0.5, 1.0)
        self.analog_agc_xx_0.set_max_gain(4000)

        ##################################################
        # Connections
        ##################################################
        self.connect((self.analog_agc_xx_0, 0), (self.root_raised_cosine_filter_0, 0))
        self.connect((self.analog_rail_ff_0, 0), (self.blocks_float_to_char_0, 0))
        self.connect((self.blocks_float_to_char_0, 0), (self.blocks_file_sink_0_0, 0))
        self.connect((self.digital_clock_recovery_mm_xx_0, 0), (self.digital_constellation_soft_decoder_cf_1, 0))
        self.connect((self.digital_constellation_soft_decoder_cf_1, 0), (self.analog_rail_ff_0, 0))
        self.connect((self.digital_costas_loop_cc_0, 0), (self.digital_clock_recovery_mm_xx_0, 0))
        self.connect((self.freq_xlating_fir_filter_xxx_0, 0), (self.analog_agc_xx_0, 0))
        self.connect((self.root_raised_cosine_filter_0, 0), (self.digital_costas_loop_cc_0, 0))
        self.connect((self.rtlsdr_source_0, 0), (self.freq_xlating_fir_filter_xxx_0, 0))

    def get_symb_rate(self):
        return self.symb_rate

    def set_symb_rate(self, symb_rate):
        self.symb_rate = symb_rate
        self.set_samp_per_sym(self.samp_rate/self.decimation/self.symb_rate)
        self.root_raised_cosine_filter_0.set_taps(firdes.root_raised_cosine(1, self.samp_rate/self.decimation, self.symb_rate, 0.3, 361))

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.set_samp_per_sym(self.samp_rate/self.decimation/self.symb_rate)
        self.rtlsdr_source_0.set_sample_rate(self.samp_rate)
        self.root_raised_cosine_filter_0.set_taps(firdes.root_raised_cosine(1, self.samp_rate/self.decimation, self.symb_rate, 0.3, 361))
        self.freq_xlating_fir_filter_xxx_0.set_taps((firdes.low_pass(1,self.samp_rate,self.BPF_width/2,10e3)))

    def get_decimation(self):
        return self.decimation

    def set_decimation(self, decimation):
        self.decimation = decimation
        self.set_samp_per_sym(self.samp_rate/self.decimation/self.symb_rate)
        self.root_raised_cosine_filter_0.set_taps(firdes.root_raised_cosine(1, self.samp_rate/self.decimation, self.symb_rate, 0.3, 361))

    def get_samp_per_sym(self):
        return self.samp_per_sym

    def set_samp_per_sym(self, samp_per_sym):
        self.samp_per_sym = samp_per_sym
        self.digital_clock_recovery_mm_xx_0.set_omega(self.samp_per_sym*(1+0.0))

    def get_clock_alpha(self):
        return self.clock_alpha

    def set_clock_alpha(self, clock_alpha):
        self.clock_alpha = clock_alpha
        self.digital_clock_recovery_mm_xx_0.set_gain_omega(self.clock_alpha**2/4.0)
        self.digital_clock_recovery_mm_xx_0.set_gain_mu(self.clock_alpha)

    def get_bitstream_name(self):
        return self.bitstream_name

    def set_bitstream_name(self, bitstream_name):
        self.bitstream_name = bitstream_name
        self.blocks_file_sink_0_0.open(self.bitstream_name)

    def get_Tuning_offset(self):
        return self.Tuning_offset

    def set_Tuning_offset(self, Tuning_offset):
        self.Tuning_offset = Tuning_offset
        self.rtlsdr_source_0.set_center_freq(self.LO_freq-self.Tuning_offset, 0)
        self.freq_xlating_fir_filter_xxx_0.set_center_freq(self.Tuning_offset)

    def get_LO_freq(self):
        return self.LO_freq

    def set_LO_freq(self, LO_freq):
        self.LO_freq = LO_freq
        self.rtlsdr_source_0.set_center_freq(self.LO_freq-self.Tuning_offset, 0)

    def get_BPF_width(self):
        return self.BPF_width

    def set_BPF_width(self, BPF_width):
        self.BPF_width = BPF_width
        self.freq_xlating_fir_filter_xxx_0.set_taps((firdes.low_pass(1,self.samp_rate,self.BPF_width/2,10e3)))


def main(top_block_cls=METEOR_M2_v04_noGUI, options=None):

    tb = top_block_cls()
    tb.start()
    try:
        raw_input('Press Enter to quit: ')
    except EOFError:
        pass
    tb.stop()
    tb.wait()


if __name__ == '__main__':
    main()
