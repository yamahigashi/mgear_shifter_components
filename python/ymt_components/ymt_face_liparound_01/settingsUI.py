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
        self.gridLayout = QGridLayout(Form)
        self.gridLayout.setObjectName(u"gridLayout")
        self.groupBox_3 = QGroupBox(Form)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.isSlidingSurface = QCheckBox(self.groupBox_3)
        self.isSlidingSurface.setObjectName(u"isSlidingSurface")
        self.isSlidingSurface.setGeometry(QRect(10, 26, 118, 20))
        self.isSlidingSurface.setChecked(True)
        self.isSlidingSurface.setTristate(False)
        self.ikRefArray_groupBox = QGroupBox(self.groupBox_3)
        self.ikRefArray_groupBox.setObjectName(u"ikRefArray_groupBox")
        self.ikRefArray_groupBox.setEnabled(True)
        self.ikRefArray_groupBox.setGeometry(QRect(10, 52, 381, 131))
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


        self.gridLayout.addWidget(self.groupBox_3, 1, 0, 1, 1)

        self.groupBox_4 = QGroupBox(Form)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.groupBox_2 = QGroupBox(self.groupBox_4)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.groupBox_2.setGeometry(QRect(10, 20, 391, 101))
        self.ikRefArray_groupBox_3 = QGroupBox(self.groupBox_2)
        self.ikRefArray_groupBox_3.setObjectName(u"ikRefArray_groupBox_3")
        self.ikRefArray_groupBox_3.setEnabled(True)
        self.ikRefArray_groupBox_3.setGeometry(QRect(0, 20, 381, 81))
        self.ikRefArray_groupBox_3.setMaximumSize(QSize(16777215, 166))
        self.ikRefArray_groupBox_3.setFlat(False)
        self.gridLayout_9 = QGridLayout(self.ikRefArray_groupBox_3)
        self.gridLayout_9.setObjectName(u"gridLayout_9")
        self.gridLayout_9.setSizeConstraint(QLayout.SetMaximumSize)
        self.ikRefArray_horizontalLayout_6 = QHBoxLayout()
        self.ikRefArray_horizontalLayout_6.setObjectName(u"ikRefArray_horizontalLayout_6")
        self.ikRefArray_verticalLayout_11 = QVBoxLayout()
        self.ikRefArray_verticalLayout_11.setObjectName(u"ikRefArray_verticalLayout_11")
        self.cheekLeftReference_listWidget = QListWidget(self.ikRefArray_groupBox_3)
        self.cheekLeftReference_listWidget.setObjectName(u"cheekLeftReference_listWidget")
        self.cheekLeftReference_listWidget.setAutoScroll(False)
        self.cheekLeftReference_listWidget.setProperty("showDropIndicator", False)
        self.cheekLeftReference_listWidget.setDragDropOverwriteMode(False)
        self.cheekLeftReference_listWidget.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.cheekLeftReference_listWidget.setDefaultDropAction(Qt.CopyAction)
        self.cheekLeftReference_listWidget.setAlternatingRowColors(True)
        self.cheekLeftReference_listWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.cheekLeftReference_listWidget.setGridSize(QSize(0, 0))
        self.cheekLeftReference_listWidget.setViewMode(QListView.ListMode)
        self.cheekLeftReference_listWidget.setSelectionRectVisible(False)

        self.ikRefArray_verticalLayout_11.addWidget(self.cheekLeftReference_listWidget)


        self.ikRefArray_horizontalLayout_6.addLayout(self.ikRefArray_verticalLayout_11)

        self.ikRefArray_verticalLayout_12 = QVBoxLayout()
        self.ikRefArray_verticalLayout_12.setSpacing(3)
        self.ikRefArray_verticalLayout_12.setObjectName(u"ikRefArray_verticalLayout_12")
        self.cheekLeftReferenceAdd_pushButton = QPushButton(self.ikRefArray_groupBox_3)
        self.cheekLeftReferenceAdd_pushButton.setObjectName(u"cheekLeftReferenceAdd_pushButton")

        self.ikRefArray_verticalLayout_12.addWidget(self.cheekLeftReferenceAdd_pushButton)

        self.cheekLeftReferenceRemove_pushButton = QPushButton(self.ikRefArray_groupBox_3)
        self.cheekLeftReferenceRemove_pushButton.setObjectName(u"cheekLeftReferenceRemove_pushButton")

        self.ikRefArray_verticalLayout_12.addWidget(self.cheekLeftReferenceRemove_pushButton)

        self.ikRefArray_verticalSpacer_6 = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.ikRefArray_verticalLayout_12.addItem(self.ikRefArray_verticalSpacer_6)


        self.ikRefArray_horizontalLayout_6.addLayout(self.ikRefArray_verticalLayout_12)


        self.gridLayout_9.addLayout(self.ikRefArray_horizontalLayout_6, 1, 0, 1, 1)

        self.ikRefArray_groupBox_4 = QGroupBox(self.groupBox_4)
        self.ikRefArray_groupBox_4.setObjectName(u"ikRefArray_groupBox_4")
        self.ikRefArray_groupBox_4.setEnabled(True)
        self.ikRefArray_groupBox_4.setGeometry(QRect(10, 120, 381, 111))
        self.ikRefArray_groupBox_4.setMaximumSize(QSize(16777215, 166))
        self.ikRefArray_groupBox_4.setFlat(False)
        self.gridLayout_10 = QGridLayout(self.ikRefArray_groupBox_4)
        self.gridLayout_10.setObjectName(u"gridLayout_10")
        self.gridLayout_10.setSizeConstraint(QLayout.SetMaximumSize)
        self.groupBox_5 = QGroupBox(self.ikRefArray_groupBox_4)
        self.groupBox_5.setObjectName(u"groupBox_5")
        self.ikRefArray_groupBox_5 = QGroupBox(self.groupBox_5)
        self.ikRefArray_groupBox_5.setObjectName(u"ikRefArray_groupBox_5")
        self.ikRefArray_groupBox_5.setEnabled(True)
        self.ikRefArray_groupBox_5.setGeometry(QRect(0, 20, 381, 81))
        self.ikRefArray_groupBox_5.setMaximumSize(QSize(16777215, 166))
        self.ikRefArray_groupBox_5.setFlat(False)
        self.gridLayout_11 = QGridLayout(self.ikRefArray_groupBox_5)
        self.gridLayout_11.setObjectName(u"gridLayout_11")
        self.gridLayout_11.setSizeConstraint(QLayout.SetMaximumSize)
        self.ikRefArray_horizontalLayout_7 = QHBoxLayout()
        self.ikRefArray_horizontalLayout_7.setObjectName(u"ikRefArray_horizontalLayout_7")
        self.ikRefArray_verticalLayout_13 = QVBoxLayout()
        self.ikRefArray_verticalLayout_13.setObjectName(u"ikRefArray_verticalLayout_13")
        self.cheekRightReference_listWidget = QListWidget(self.ikRefArray_groupBox_5)
        self.cheekRightReference_listWidget.setObjectName(u"cheekRightReference_listWidget")
        self.cheekRightReference_listWidget.setAutoScroll(False)
        self.cheekRightReference_listWidget.setProperty("showDropIndicator", False)
        self.cheekRightReference_listWidget.setDragDropOverwriteMode(False)
        self.cheekRightReference_listWidget.setDragDropMode(QAbstractItemView.NoDragDrop)
        self.cheekRightReference_listWidget.setDefaultDropAction(Qt.CopyAction)
        self.cheekRightReference_listWidget.setAlternatingRowColors(True)
        self.cheekRightReference_listWidget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.cheekRightReference_listWidget.setGridSize(QSize(0, 0))
        self.cheekRightReference_listWidget.setViewMode(QListView.ListMode)
        self.cheekRightReference_listWidget.setSelectionRectVisible(False)

        self.ikRefArray_verticalLayout_13.addWidget(self.cheekRightReference_listWidget)


        self.ikRefArray_horizontalLayout_7.addLayout(self.ikRefArray_verticalLayout_13)

        self.ikRefArray_verticalLayout_14 = QVBoxLayout()
        self.ikRefArray_verticalLayout_14.setSpacing(3)
        self.ikRefArray_verticalLayout_14.setObjectName(u"ikRefArray_verticalLayout_14")
        self.cheekRightReferenceAdd_pushButton = QPushButton(self.ikRefArray_groupBox_5)
        self.cheekRightReferenceAdd_pushButton.setObjectName(u"cheekRightReferenceAdd_pushButton")

        self.ikRefArray_verticalLayout_14.addWidget(self.cheekRightReferenceAdd_pushButton)

        self.cheekRightReferenceRemove_pushButton = QPushButton(self.ikRefArray_groupBox_5)
        self.cheekRightReferenceRemove_pushButton.setObjectName(u"cheekRightReferenceRemove_pushButton")

        self.ikRefArray_verticalLayout_14.addWidget(self.cheekRightReferenceRemove_pushButton)

        self.ikRefArray_verticalSpacer_7 = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.ikRefArray_verticalLayout_14.addItem(self.ikRefArray_verticalSpacer_7)


        self.ikRefArray_horizontalLayout_7.addLayout(self.ikRefArray_verticalLayout_14)


        self.gridLayout_11.addLayout(self.ikRefArray_horizontalLayout_7, 1, 0, 1, 1)


        self.gridLayout_10.addWidget(self.groupBox_5, 0, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBox_4, 2, 0, 1, 1)

        self.groupBox = QGroupBox(Form)
        self.groupBox.setObjectName(u"groupBox")
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox.sizePolicy().hasHeightForWidth())
        self.groupBox.setSizePolicy(sizePolicy)
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


        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)


        self.retranslateUi(Form)

        self.surfaceReference_listWidget.setCurrentRow(-1)
        self.cheekLeftReference_listWidget.setCurrentRow(-1)
        self.cheekRightReference_listWidget.setCurrentRow(-1)


        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("Form", u"Surface", None))
        self.isSlidingSurface.setText(QCoreApplication.translate("Form", u"Sliding on Surface", None))
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
        self.groupBox_4.setTitle(QCoreApplication.translate("Form", u"Reference", None))
        self.groupBox_2.setTitle(QCoreApplication.translate("Form", u"Cheek Left", None))
        self.ikRefArray_groupBox_3.setTitle("")
        self.cheekLeftReferenceAdd_pushButton.setText(QCoreApplication.translate("Form", u"<<", None))
        self.cheekLeftReferenceRemove_pushButton.setText(QCoreApplication.translate("Form", u">>", None))
        self.ikRefArray_groupBox_4.setTitle("")
        self.groupBox_5.setTitle(QCoreApplication.translate("Form", u"Cheek Right", None))
        self.ikRefArray_groupBox_5.setTitle("")
        self.cheekRightReferenceAdd_pushButton.setText(QCoreApplication.translate("Form", u"<<", None))
        self.cheekRightReferenceRemove_pushButton.setText(QCoreApplication.translate("Form", u">>", None))
        self.groupBox.setTitle(QCoreApplication.translate("Form", u"GroupBox", None))
    # retranslateUi

