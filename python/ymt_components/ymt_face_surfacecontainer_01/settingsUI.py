# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'settingsUI.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(419, 555)
        self.verticalLayout = QVBoxLayout(Form)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.groupBox_3 = QGroupBox(Form)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.gridLayout_4 = QGridLayout(self.groupBox_3)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.isSlidingSurface = QCheckBox(self.groupBox_3)
        self.isSlidingSurface.setObjectName(u"isSlidingSurface")
        self.isSlidingSurface.setChecked(True)
        self.isSlidingSurface.setTristate(False)

        self.gridLayout_4.addWidget(self.isSlidingSurface, 0, 0, 1, 1)

        self.surfaceReference_groupBox = QGroupBox(self.groupBox_3)
        self.surfaceReference_groupBox.setObjectName(u"surfaceReference_groupBox")
        self.surfaceReference_groupBox.setEnabled(True)
        self.surfaceReference_groupBox.setFlat(False)
        self.gridLayout_7 = QGridLayout(self.surfaceReference_groupBox)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.surfaceReference_horizontalLayout_4 = QHBoxLayout()
        self.surfaceReference_horizontalLayout_4.setObjectName(u"surfaceReference_horizontalLayout_4")
        self.surfaceReference_verticalLayout_7 = QVBoxLayout()
        self.surfaceReference_verticalLayout_7.setObjectName(u"surfaceReference_verticalLayout_7")
        self.surfaceReference_listWidget_4 = QListWidget(self.surfaceReference_groupBox)
        self.surfaceReference_listWidget_4.setObjectName(u"surfaceReference_listWidget_4")
        self.surfaceReference_listWidget_4.setAutoScroll(False)
        self.surfaceReference_listWidget_4.setProperty("showDropIndicator", False)
        self.surfaceReference_listWidget_4.setDragDropOverwriteMode(False)
        self.surfaceReference_listWidget_4.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.surfaceReference_listWidget_4.setDefaultDropAction(Qt.CopyAction)
        self.surfaceReference_listWidget_4.setAlternatingRowColors(True)
        self.surfaceReference_listWidget_4.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.surfaceReference_listWidget_4.setGridSize(QSize(0, 0))
        self.surfaceReference_listWidget_4.setViewMode(QListView.ListMode)
        self.surfaceReference_listWidget_4.setSelectionRectVisible(False)

        self.surfaceReference_verticalLayout_7.addWidget(self.surfaceReference_listWidget_4)


        self.surfaceReference_horizontalLayout_4.addLayout(self.surfaceReference_verticalLayout_7)

        self.surfaceReference_verticalLayout_8 = QVBoxLayout()
        self.surfaceReference_verticalLayout_8.setSpacing(3)
        self.surfaceReference_verticalLayout_8.setObjectName(u"surfaceReference_verticalLayout_8")
        self.surfaceReferenceAdd_pushButton_4 = QPushButton(self.surfaceReference_groupBox)
        self.surfaceReferenceAdd_pushButton_4.setObjectName(u"surfaceReferenceAdd_pushButton_4")

        self.surfaceReference_verticalLayout_8.addWidget(self.surfaceReferenceAdd_pushButton_4)

        self.surfaceReferenceRemove_pushButton_4 = QPushButton(self.surfaceReference_groupBox)
        self.surfaceReferenceRemove_pushButton_4.setObjectName(u"surfaceReferenceRemove_pushButton_4")

        self.surfaceReference_verticalLayout_8.addWidget(self.surfaceReferenceRemove_pushButton_4)

        self.surfaceReference_verticalSpacer_4 = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.surfaceReference_verticalLayout_8.addItem(self.surfaceReference_verticalSpacer_4)


        self.surfaceReference_horizontalLayout_4.addLayout(self.surfaceReference_verticalLayout_8)


        self.gridLayout_7.addLayout(self.surfaceReference_horizontalLayout_4, 0, 0, 1, 1)


        self.gridLayout_4.addWidget(self.surfaceReference_groupBox, 1, 0, 1, 1)


        self.verticalLayout.addWidget(self.groupBox_3)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")

        self.verticalLayout.addLayout(self.horizontalLayout)

        self.groupBox = QGroupBox(Form)
        self.groupBox.setObjectName(u"groupBox")
        self.horizontalLayout_2 = QHBoxLayout(self.groupBox)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.overrideNegate_checkBox = QCheckBox(self.groupBox)
        self.overrideNegate_checkBox.setObjectName(u"overrideNegate_checkBox")
        self.overrideNegate_checkBox.setText(u"Override Negate Axis Direction For \"R\" Side")

        self.verticalLayout_3.addWidget(self.overrideNegate_checkBox)

        self.addJoints_checkBox = QCheckBox(self.groupBox)
        self.addJoints_checkBox.setObjectName(u"addJoints_checkBox")
        self.addJoints_checkBox.setText(u"Add Joints")
        self.addJoints_checkBox.setChecked(True)

        self.verticalLayout_3.addWidget(self.addJoints_checkBox)


        self.horizontalLayout_2.addLayout(self.verticalLayout_3)


        self.verticalLayout.addWidget(self.groupBox)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.retranslateUi(Form)

        self.surfaceReference_listWidget_4.setCurrentRow(-1)


        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("Form", u"Surface", None))
        self.isSlidingSurface.setText(QCoreApplication.translate("Form", u"Sliding on Surface", None))
        self.surfaceReference_groupBox.setTitle("")
        self.surfaceReferenceAdd_pushButton_4.setText(QCoreApplication.translate("Form", u"<<", None))
        self.surfaceReferenceRemove_pushButton_4.setText(QCoreApplication.translate("Form", u">>", None))
        self.groupBox.setTitle(QCoreApplication.translate("Form", u"GroupBox", None))
    # retranslateUi

