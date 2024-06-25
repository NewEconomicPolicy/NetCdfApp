#-------------------------------------------------------------------------------
# Name:        NetCdfUtilsGUI.py
# Purpose:     Creates a GUI to run limited data files for Ecosse
# Author:      Mike Martin
# Created:     16/05/2020
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

__prog__ = 'NetCdfUtilsGUI.py'
__version__ = '0.0.1'
__author__ = 's03mm5'

from os.path import normpath, split, join, isfile, isdir
import sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QLabel, QWidget, QApplication, QHBoxLayout, QVBoxLayout, QGridLayout, \
                                QPushButton, QCheckBox, QFileDialog, QComboBox

from initialise_netcdf_utils import initiation, read_config_file, write_config_file, report_nc_files
from weather_aggregation import wthr_aggreg
from eclips_reorg import make_empty_eclips_dsets, populate_eclips_dsets
from jinfeng_reorg import concat_jinfeng_dsets
from grazing_reorg import integrate_grazing_dsets
from post_process_funcs import subtract_turkey

from make_chess_lookup_fns import make_chess_lookup_table

WDGT_SIZE_60 = 60
WDGT_SIZE_90 = 90
WDGT_SIZE_135 = 135
WDGT_SIZE_150 = 150

SCENARIO_LIST = ['RCP26', 'RCP45', 'RCP60', 'RCP85']
SCENARIO_LIST = ['RCP45', 'RCP85']
GCM_LIST = ['CLMcom_CCLM', 'CLMcom_CLM', 'DMI_HIRAM','KMNI_RAMCO','MPI_CSC_REMO2009']

class Form(QWidget):

    def __init__(self, parent=None):

        super(Form, self).__init__(parent)

        # read settings
        initiation(self)

        # define two vertical boxes, in LH vertical box put the painter and in RH put the grid
        # define horizon box to put LH and RH vertical boxes in
        hbox = QHBoxLayout()
        hbox.setSpacing(10)

        # left hand vertical box consists of png image
        # ============================================
        lh_vbox = QVBoxLayout()

        # LH vertical box contains image only
        w_lbl20 = QLabel()
        pixmap = QPixmap(self.settings['fname_png'])
        w_lbl20.setPixmap(pixmap)

        lh_vbox.addWidget(w_lbl20)

        # add LH vertical box to horizontal box
        hbox.addLayout(lh_vbox)

        # right hand box consists of combo boxes, labels and buttons
        # ==========================================================
        rh_vbox = QVBoxLayout()

        # The layout is done with the QGridLayout
        grid = QGridLayout()
        grid.setSpacing(10)	# set spacing between widgets

        # display directory and report number of lines, etc.
        # =================================================
        irow = 1
        w_rslts_dir = QPushButton("Raw climate dir")
        helpText = 'Source directory containing for raw weather datasets'
        w_rslts_dir.setToolTip(helpText)
        grid.addWidget(w_rslts_dir, irow, 0)
        w_rslts_dir.clicked.connect(self.fetchRsltsDir)

        w_lbl_src = QLabel()
        grid.addWidget(w_lbl_src, irow, 1, 1, 5)
        self.w_lbl_src = w_lbl_src

        # settings check boxes
        # ====================
        irow += 1
        w_resume = QCheckBox('Resume from previous run')
        w_resume.setToolTip(helpText)
        w_resume.setEnabled(False)
        grid.addWidget(w_resume, irow, 0, 1, 2)
        self.w_resume = w_resume

        w_del_nc = QCheckBox('Delete existing NC files')
        grid.addWidget(w_del_nc, irow, 2, 1, 2)
        helpText = 'Delete existing NC file'
        w_del_nc.setToolTip(helpText)
        w_del_nc.setChecked(True)
        self.w_del_nc = w_del_nc

        w_pop_hist = QCheckBox('Populate history wthr')
        w_pop_hist.setToolTip(helpText)
        grid.addWidget(w_pop_hist, irow, 4, 1, 2)
        self.w_pop_hist = w_pop_hist

        w_pop_fut = QCheckBox('Populate future wthr')
        grid.addWidget(w_pop_fut, irow, 6, 1, 2)
        helpText = 'Delete existing NC file'
        w_pop_fut.setToolTip(helpText)
        self.w_pop_fut = w_pop_fut

        irow += 1
        w_tave_only = QCheckBox('Process temperature only')
        w_tave_only.setToolTip(helpText)
        w_tave_only.setCheckState(0)
        w_tave_only.setEnabled(False)
        grid.addWidget(w_tave_only, irow, 0, 1, 2)
        self.w_tave_only = w_tave_only

        # ==========
        irow += 1
        w_lbl10 = QLabel('Climate Scenarios: ')
        w_lbl10.setAlignment(Qt.AlignRight)
        grid.addWidget(w_lbl10, irow, 0)

        w_combo10 = QComboBox()
        for scenario in SCENARIO_LIST:
            w_combo10.addItem(str(scenario))
        w_combo10.setFixedWidth(WDGT_SIZE_60)
        grid.addWidget(w_combo10, irow, 1)
        self.w_combo10 = w_combo10

        w_lbl11 = QLabel('GCMs: ')
        helpText = 'General circulation models'
        w_lbl11.setToolTip(helpText)
        w_lbl11.setAlignment(Qt.AlignRight)
        grid.addWidget(w_lbl11, irow, 2)

        w_combo11 = QComboBox()
        for gcm in GCM_LIST:
            w_combo11.addItem(str(gcm))
        w_combo11.setFixedWidth(WDGT_SIZE_135)
        w_combo11.setToolTip(helpText)
        grid.addWidget(w_combo11, irow, 3)
        self.w_combo11 = w_combo11

        # ========== spacer
        irow += 1
        grid.addWidget(QLabel(' '), irow, 0)

        # =====================
        irow += 1
        w_fert_dir = QPushButton("Annual fert dir")
        helpText = 'Directory containing annual fertiliser NC files or other NC data'
        w_fert_dir.setToolTip(helpText)
        grid.addWidget(w_fert_dir, irow, 0)
        w_fert_dir.clicked.connect(self.fetchFertDir)

        w_lbl_fertdir = QLabel('')
        grid.addWidget(w_lbl_fertdir, irow, 1, 1, 5)
        self.w_lbl_fertdir = w_lbl_fertdir

        irow += 1
        w_lbl_fertfns = QLabel('')
        grid.addWidget(w_lbl_fertfns, irow, 1, 1, 2)
        self.w_lbl_fertfns = w_lbl_fertfns

        # ========== spacer
        irow += 1
        grid.addWidget(QLabel(' '), irow, 0)

        # output directory
        # =================
        irow += 1
        w_out_dir = QPushButton("Output dir")
        helpText = 'Directory containing the shadow projects directory structure.'
        w_out_dir.setToolTip(helpText)
        grid.addWidget(w_out_dir, irow, 0)
        w_out_dir.clicked.connect(self.fetchOutDir)

        w_lbl_outdir = QLabel('')
        grid.addWidget(w_lbl_outdir, irow, 1, 1, 5)
        self.w_lbl_outdir = w_lbl_outdir

        # ========== spacer
        irow += 1
        grid.addWidget(QLabel(' '), irow, 0)

        # ======= operations ========
        irow += 3
        w_eclips_wthr = QPushButton('Make empty ECLIPS NCs')
        helpText = 'Create empty ECLIPS datasets using HARMONIE resolution'
        w_eclips_wthr.setToolTip(helpText)
        w_eclips_wthr.setFixedWidth(WDGT_SIZE_150)
        w_eclips_wthr.clicked.connect(self.reorganiseEclips)
        grid.addWidget(w_eclips_wthr, irow, 0)

        w_aggrgt_ncs = QPushButton('Populate ECLIPS NCs')
        helpText = 'Populate empty HARMONIE resolution datasets using ECLIPS2 10 or 20 years nc files'
        w_aggrgt_ncs.setToolTip(helpText)
        w_eclips_wthr.setFixedWidth(WDGT_SIZE_150)
        w_aggrgt_ncs.clicked.connect(self.aggregateNcs)
        grid.addWidget(w_aggrgt_ncs, irow, 1)

        w_cncte_fert = QPushButton('Concat Fert')
        helpText = 'Concatenate Fertiliser NC files'
        w_cncte_fert.setFixedWidth(WDGT_SIZE_90)
        w_cncte_fert.setToolTip(helpText)
        w_cncte_fert.clicked.connect(self.concatFertClicked)
        grid.addWidget(w_cncte_fert, irow, 2)
        self.w_cncte_fert = w_cncte_fert

        w_cncte_graze = QPushButton('Concat Grazing')
        helpText = 'Concatenate Grazing NC files, namely '
        w_cncte_graze.setFixedWidth(WDGT_SIZE_90)
        w_cncte_graze.setToolTip(helpText)
        w_cncte_graze.clicked.connect(self.concatGrazeClicked)
        grid.addWidget(w_cncte_graze, irow, 3)
        self.w_cncte_graze = w_cncte_graze

        w_gthr_wthr = QPushButton('Gather Wthr')
        helpText = 'Works in context of Sylvia Vetter global soils project for each region look for A1B and A2 resources'
        w_gthr_wthr.setToolTip(helpText)
        w_gthr_wthr.clicked.connect(self.gatherWthrClicked)
        grid.addWidget(w_gthr_wthr, irow, 5)

        exit = QPushButton('Exit', self)
        grid.addWidget(exit, irow, 6)
        exit.clicked.connect(self.exitClicked)

        # ==================
        irow += 1
        w_chess_lkup = QPushButton('Make CHESS lookup')
        helpText = 'Make a lookup table based on 1km CHESS weather sets'
        w_chess_lkup.setToolTip(helpText)
        w_chess_lkup.setFixedWidth(WDGT_SIZE_150)
        w_chess_lkup.clicked.connect(self.makeChessLookup)
        grid.addWidget(w_chess_lkup, irow, 0)

        w_clip_csvs = QPushButton('Subtract Turkey')
        helpText = 'Reduce CSV files by subracting Turkish coordinates'
        w_clip_csvs.setToolTip(helpText)
        w_clip_csvs.setFixedWidth(WDGT_SIZE_150)
        w_clip_csvs.clicked.connect(self.subtractTurkey)
        grid.addWidget(w_clip_csvs, irow, 3)

        # add grid to RH vertical box
        rh_vbox.addLayout(grid)

        # vertical box goes into horizontal box
        hbox.addLayout(rh_vbox)

        # the horizontal box fits inside the window
        self.setLayout(hbox)

        # posx, posy, width, height
        # =========================
        self.setGeometry(300, 300, 650, 250)
        self.setWindowTitle('Collection of functions to restucture and/or create NetCDF files')
        read_config_file(self)

    def subtractTurkey(self):
        """

        """
        subtract_turkey(self)

    def reorganiseEclips(self):
        """

        """
        make_empty_eclips_dsets(self)

    def makeChessLookup(self):
        """

        """
        make_chess_lookup_table(self)

    def aggregateNcs(self):
        """

        """
        populate_eclips_dsets(self)

    def concatGrazeClicked(self):
        '''

        '''
        integrate_grazing_dsets(self)

    def concatFertClicked(self):
        '''

        '''
        concat_jinfeng_dsets(self)

    def gatherWthrClicked(self):
        '''
        read Excel file world_divisions.xlsx then step through each weather resource
        '''
        sims_dir = split(self.w_lbl_sims.text())[0]

        prgrm_dir = self.settings['fname_png'].split('GlobalEcosseSuite')[0]
        regions_fname = join(prgrm_dir, 'GlblEcosseSiteSpecSv\Docs', 'world_divisions.xlsx')
        if isfile(regions_fname):
            regions = wthr_aggreg(sims_dir, regions_fname)

    def fetchFertDir(self):
        '''

        '''
        dirname = self.w_lbl_fertdir.text()
        dirname = QFileDialog.getExistingDirectory(self, 'Select directory for annual fertiliser', dirname)
        if dirname != '':
            if isdir(dirname):
                self.w_lbl_fertdir.setText(normpath(dirname))
                report_nc_files(self, dirname)

    def fetchOutDir(self):
        '''
        select the directory under which the directories containing the ECOSSE simulation files are to be found
        '''
        dirname = self.w_lbl_outdir.text()
        dirname = QFileDialog.getExistingDirectory(self, 'Select directory for outputs', dirname)
        if dirname != '':
            if isdir(dirname):
                self.w_lbl_outdir.setText(normpath(dirname))

    def fetchRsltsDir(self):

        dialog = QFileDialog(self)
        dialog.ShowDirsOnly = False

        rslts_dir = self.w_lbl_src.text()
        rslts_dir = dialog.getExistingDirectory(self, 'Select directory containing the results', rslts_dir)

        if rslts_dir != '':
            rslts_dir = normpath(rslts_dir)
            self.w_lbl_src.setText(rslts_dir)
            '''
            descriptor = 'Contents: '
            self.w_lbl06.setText(descriptor)
            '''
    def exitClicked(self):
        write_config_file(self)
        self.close()

def main():

    app = QApplication(sys.argv)  # create QApplication object
    form = Form()     # instantiate form
    form.show()       # paint form
    sys.exit(app.exec_())   # start event loop

if __name__ == '__main__':
    main()
