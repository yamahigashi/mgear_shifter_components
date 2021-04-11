# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:/Projects/Pipeline/rez-packages/third/github.com/yamahigashi/ymtshiftercomponents/mgear_shifter_components/python/ymt_components/ymt_face_eyebrow_01/settingsUI.ui'
#
# Created: Sun Apr 11 12:55:04 2021
#      by: pyside2-uic  running on PySide2 2.0.0~alpha0
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(419, 737)
        self.verticalLayout = QtWidgets.QVBoxLayout(Form)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox_3 = QtWidgets.QGroupBox(Form)
        self.groupBox_3.setObjectName("groupBox_3")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.groupBox_3)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.gridLayout_4.addLayout(self.horizontalLayout_2, 0, 0, 1, 1)
        self.isSlidingSurface = QtWidgets.QCheckBox(self.groupBox_3)
        self.isSlidingSurface.setChecked(True)
        self.isSlidingSurface.setTristate(False)
        self.isSlidingSurface.setObjectName("isSlidingSurface")
        self.gridLayout_4.addWidget(self.isSlidingSurface, 1, 0, 1, 1)
        self.verticalLayout.addWidget(self.groupBox_3)
        self.overrideNegate_checkBox = QtWidgets.QCheckBox(Form)
        self.overrideNegate_checkBox.setText("Override Negate Axis Direction For \"R\" Side")
        self.overrideNegate_checkBox.setObjectName("overrideNegate_checkBox")
        self.verticalLayout.addWidget(self.overrideNegate_checkBox)
        self.addJoints_checkBox = QtWidgets.QCheckBox(Form)
        self.addJoints_checkBox.setText("Add Joints")
        self.addJoints_checkBox.setChecked(True)
        self.addJoints_checkBox.setObjectName("addJoints_checkBox")
        self.verticalLayout.addWidget(self.addJoints_checkBox)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout.addItem(spacerItem)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtWidgets.QApplication.translate("Form", "Form", None, -1))
        self.groupBox_3.setTitle(QtWidgets.QApplication.translate("Form", "Surface", None, -1))
        self.isSlidingSurface.setText(QtWidgets.QApplication.translate("Form", "Sliding on Surface", None, -1))

