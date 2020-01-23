# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:/Pipeline/rez-packages/third/github.com/yamahigashi/ymtshiftercomponents/mgear_shifter_components/python/ymt_components/ymt_neck_ik_01/settingsUI.ui',
# licensing of 'D:/Pipeline/rez-packages/third/github.com/yamahigashi/ymtshiftercomponents/mgear_shifter_components/python/ymt_components/ymt_neck_ik_01/settingsUI.ui' applies.
#
# Created: Thu Jan 23 11:56:56 2020
#      by: pyside2-uic  running on PySide2 5.12.5
#
# WARNING! All changes made in this file will be lost!

from PySide2 import QtCore, QtGui, QtWidgets

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(269, 559)
        self.upvRefArray_groupBox = QtWidgets.QGroupBox(Form)
        self.upvRefArray_groupBox.setGeometry(QtCore.QRect(10, 60, 249, 176))
        self.upvRefArray_groupBox.setObjectName("upvRefArray_groupBox")
        self.layoutWidget_2 = QtWidgets.QWidget(self.upvRefArray_groupBox)
        self.layoutWidget_2.setGeometry(QtCore.QRect(10, 20, 231, 141))
        self.layoutWidget_2.setObjectName("layoutWidget_2")
        self.upvRefArray_horizontalLayout = QtWidgets.QHBoxLayout(self.layoutWidget_2)
        self.upvRefArray_horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.upvRefArray_horizontalLayout.setObjectName("upvRefArray_horizontalLayout")
        self.upvRefArray_verticalLayout_1 = QtWidgets.QVBoxLayout()
        self.upvRefArray_verticalLayout_1.setObjectName("upvRefArray_verticalLayout_1")
        self.headRefArray_listWidget = QtWidgets.QListWidget(self.layoutWidget_2)
        self.headRefArray_listWidget.setDragDropOverwriteMode(True)
        self.headRefArray_listWidget.setDragDropMode(QtWidgets.QAbstractItemView.InternalMove)
        self.headRefArray_listWidget.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.headRefArray_listWidget.setAlternatingRowColors(True)
        self.headRefArray_listWidget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.headRefArray_listWidget.setSelectionRectVisible(False)
        self.headRefArray_listWidget.setObjectName("headRefArray_listWidget")
        self.upvRefArray_verticalLayout_1.addWidget(self.headRefArray_listWidget)
        self.headRefArray_copyRef_pushButton = QtWidgets.QPushButton(self.layoutWidget_2)
        self.headRefArray_copyRef_pushButton.setObjectName("headRefArray_copyRef_pushButton")
        self.upvRefArray_verticalLayout_1.addWidget(self.headRefArray_copyRef_pushButton)
        self.upvRefArray_horizontalLayout.addLayout(self.upvRefArray_verticalLayout_1)
        self.upvRefArray_verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.upvRefArray_verticalLayout_2.setObjectName("upvRefArray_verticalLayout_2")
        self.headRefArrayAdd_pushButton = QtWidgets.QPushButton(self.layoutWidget_2)
        self.headRefArrayAdd_pushButton.setObjectName("headRefArrayAdd_pushButton")
        self.upvRefArray_verticalLayout_2.addWidget(self.headRefArrayAdd_pushButton)
        self.headRefArrayRemove_pushButton = QtWidgets.QPushButton(self.layoutWidget_2)
        self.headRefArrayRemove_pushButton.setObjectName("headRefArrayRemove_pushButton")
        self.upvRefArray_verticalLayout_2.addWidget(self.headRefArrayRemove_pushButton)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.upvRefArray_verticalLayout_2.addItem(spacerItem)
        self.upvRefArray_horizontalLayout.addLayout(self.upvRefArray_verticalLayout_2)
        self.useExprespy_checkBox = QtWidgets.QCheckBox(Form)
        self.useExprespy_checkBox.setGeometry(QtCore.QRect(30, 20, 401, 16))
        self.useExprespy_checkBox.setText("Use Exprespy")
        self.useExprespy_checkBox.setChecked(True)
        self.useExprespy_checkBox.setObjectName("useExprespy_checkBox")

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtWidgets.QApplication.translate("Form", "Form", None, -1))
        self.upvRefArray_groupBox.setTitle(QtWidgets.QApplication.translate("Form", "Head Reference Array", None, -1))
        self.headRefArray_copyRef_pushButton.setText(QtWidgets.QApplication.translate("Form", "Copy from IK Ref", None, -1))
        self.headRefArrayAdd_pushButton.setText(QtWidgets.QApplication.translate("Form", "<<", None, -1))
        self.headRefArrayRemove_pushButton.setText(QtWidgets.QApplication.translate("Form", ">>", None, -1))

