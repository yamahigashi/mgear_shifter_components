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
        self.gridLayout_4.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.isSlidingSurface = QCheckBox(self.groupBox_3)
        self.isSlidingSurface.setObjectName(u"isSlidingSurface")
        self.isSlidingSurface.setChecked(True)
        self.isSlidingSurface.setTristate(False)

        self.gridLayout_4.addWidget(self.isSlidingSurface, 0, 0, 1, 1)

        self.ikRefArray_groupBox = QGroupBox(self.groupBox_3)
        self.ikRefArray_groupBox.setObjectName(u"ikRefArray_groupBox")
        self.ikRefArray_groupBox.setEnabled(True)
        self.ikRefArray_groupBox.setMaximumSize(QSize(16777215, 166))
        self.ikRefArray_groupBox.setFlat(False)
        self.gridLayout_7 = QGridLayout(self.ikRefArray_groupBox)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.gridLayout_7.setSizeConstraint(QLayout.SetMaximumSize)
        self.ikRefArray_horizontalLayout_4 = QHBoxLayout()
        self.ikRefArray_horizontalLayout_4.setObjectName(u"ikRefArray_horizontalLayout_4")
        self.ikRefArray_verticalLayout_7 = QVBoxLayout()
        self.ikRefArray_verticalLayout_7.setObjectName(u"ikRefArray_verticalLayout_7")
        self.surfaceReference_listWidget = QListWidget(self.ikRefArray_groupBox)
        self.surfaceReference_listWidget.setObjectName(u"surfaceReference_listWidget")
        self.surfaceReference_listWidget.setAutoScroll(False)
        self.surfaceReference_listWidget.setProperty("showDropIndicator", False)
        self.surfaceReference_listWidget.setDragDropOverwriteMode(False)
        self.surfaceReference_listWidget.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.surfaceReference_listWidget.setDefaultDropAction(Qt.CopyAction)
        self.surfaceReference_listWidget.setAlternatingRowColors(True)
        self.surfaceReference_listWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.surfaceReference_listWidget.setGridSize(QSize(0, 0))
        self.surfaceReference_listWidget.setViewMode(QListView.ListMode)
        self.surfaceReference_listWidget.setSelectionRectVisible(False)

        self.ikRefArray_verticalLayout_7.addWidget(self.surfaceReference_listWidget)


        self.ikRefArray_horizontalLayout_4.addLayout(self.ikRefArray_verticalLayout_7)

        self.ikRefArray_verticalLayout_8 = QVBoxLayout()
        self.ikRefArray_verticalLayout_8.setSpacing(3)
        self.ikRefArray_verticalLayout_8.setObjectName(u"ikRefArray_verticalLayout_8")
        self.surfaceReferenceAdd_pushButton = QPushButton(self.ikRefArray_groupBox)
        self.surfaceReferenceAdd_pushButton.setObjectName(u"surfaceReferenceAdd_pushButton")

        self.ikRefArray_verticalLayout_8.addWidget(self.surfaceReferenceAdd_pushButton)

        self.surfaceReferenceRemove_pushButton = QPushButton(self.ikRefArray_groupBox)
        self.surfaceReferenceRemove_pushButton.setObjectName(u"surfaceReferenceRemove_pushButton")

        self.ikRefArray_verticalLayout_8.addWidget(self.surfaceReferenceRemove_pushButton)

        self.ikRefArray_verticalSpacer_4 = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.ikRefArray_verticalLayout_8.addItem(self.ikRefArray_verticalSpacer_4)


        self.ikRefArray_horizontalLayout_4.addLayout(self.ikRefArray_verticalLayout_8)


        self.gridLayout_7.addLayout(self.ikRefArray_horizontalLayout_4, 1, 0, 1, 1)

        self.textEdit = QTextEdit(self.ikRefArray_groupBox)
        self.textEdit.setObjectName(u"textEdit")
        self.textEdit.setMaximumSize(QSize(16777215, 66))
        self.textEdit.setFocusPolicy(Qt.NoFocus)
        self.textEdit.setContextMenuPolicy(Qt.NoContextMenu)
        self.textEdit.setAcceptDrops(False)
        self.textEdit.setReadOnly(True)

        self.gridLayout_7.addWidget(self.textEdit, 2, 0, 1, 1)


        self.gridLayout_4.addWidget(self.ikRefArray_groupBox, 1, 0, 1, 1)


        self.verticalLayout.addWidget(self.groupBox_3)

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

        self.sourceKeyable_checkBox = QCheckBox(self.groupBox)
        self.sourceKeyable_checkBox.setObjectName(u"sourceKeyable_checkBox")
        self.sourceKeyable_checkBox.setText(u"Source Ctl Keyable")
        self.sourceKeyable_checkBox.setChecked(True)
        self.verticalLayout_3.addWidget(self.sourceKeyable_checkBox)

        self.surfaceKeyable_checkBox = QCheckBox(self.groupBox)
        self.surfaceKeyable_checkBox.setObjectName(u"surfaceKeyable_checkBox")
        self.surfaceKeyable_checkBox.setText(u"Surface Ctl Keyable")
        self.surfaceKeyable_checkBox.setChecked(True)
        self.verticalLayout_3.addWidget(self.surfaceKeyable_checkBox)


        self.horizontalLayout_2.addLayout(self.verticalLayout_3)


        self.verticalLayout.addWidget(self.groupBox)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.retranslateUi(Form)

        self.surfaceReference_listWidget.setCurrentRow(-1)


        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("Form", u"Surface", None))
        self.isSlidingSurface.setText(QCoreApplication.translate("Form", u"Riveting(off) or Sliding(on) on Surface", None))
        self.ikRefArray_groupBox.setTitle("")
        self.surfaceReferenceAdd_pushButton.setText(QCoreApplication.translate("Form", u"<<", None))
        self.surfaceReferenceRemove_pushButton.setText(QCoreApplication.translate("Form", u">>", None))
        self.textEdit.setHtml(QCoreApplication.translate("Form", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Segoe UI'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Reference to the &quot;sliding_surface&quot; of other components.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">When setting this value, please ensure that the component comes before this component in the order on the outliner.</p></body></html>", None))
        self.groupBox.setTitle(QCoreApplication.translate("Form", u"GroupBox", None))
    # retranslateUi

