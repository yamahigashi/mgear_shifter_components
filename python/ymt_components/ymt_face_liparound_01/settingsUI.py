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
        Form.resize(419, 630)
        self.gridLayout = QGridLayout(Form)
        self.gridLayout.setObjectName(u"gridLayout")
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

        self.isSlidingSurface = QCheckBox(self.groupBox)
        self.isSlidingSurface.setObjectName(u"isSlidingSurface")
        self.isSlidingSurface.setChecked(True)
        self.isSlidingSurface.setTristate(False)

        self.verticalLayout_3.addWidget(self.isSlidingSurface)


        self.horizontalLayout_2.addLayout(self.verticalLayout_3)


        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)

        self.groupBox_3 = QGroupBox(Form)
        self.groupBox_3.setObjectName(u"groupBox_3")
        self.verticalLayout = QVBoxLayout(self.groupBox_3)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.groupBox_4 = QGroupBox(self.groupBox_3)
        self.groupBox_4.setObjectName(u"groupBox_4")
        self.verticalLayout_2 = QVBoxLayout(self.groupBox_4)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.ikRefArray_horizontalLayout_4 = QHBoxLayout()
        self.ikRefArray_horizontalLayout_4.setObjectName(u"ikRefArray_horizontalLayout_4")
        self.surfaceReference_lineEdit = QLineEdit(self.groupBox_4)
        self.surfaceReference_lineEdit.setObjectName(u"surfaceReference_lineEdit")

        self.ikRefArray_horizontalLayout_4.addWidget(self.surfaceReference_lineEdit)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setSpacing(3)
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.surfaceReferenceAdd_pushButton = QPushButton(self.groupBox_4)
        self.surfaceReferenceAdd_pushButton.setObjectName(u"surfaceReferenceAdd_pushButton")
        self.surfaceReferenceAdd_pushButton.setMaximumSize(QSize(55, 16777215))

        self.horizontalLayout_4.addWidget(self.surfaceReferenceAdd_pushButton)

        self.surfaceReferenceRemove_pushButton = QPushButton(self.groupBox_4)
        self.surfaceReferenceRemove_pushButton.setObjectName(u"surfaceReferenceRemove_pushButton")
        self.surfaceReferenceRemove_pushButton.setMaximumSize(QSize(55, 16777215))

        self.horizontalLayout_4.addWidget(self.surfaceReferenceRemove_pushButton)


        self.ikRefArray_horizontalLayout_4.addLayout(self.horizontalLayout_4)


        self.verticalLayout_2.addLayout(self.ikRefArray_horizontalLayout_4)

        self.textEdit = QTextEdit(self.groupBox_4)
        self.textEdit.setObjectName(u"textEdit")
        self.textEdit.setMaximumSize(QSize(16777215, 66))
        self.textEdit.setFocusPolicy(Qt.NoFocus)
        self.textEdit.setContextMenuPolicy(Qt.NoContextMenu)
        self.textEdit.setAcceptDrops(False)
        self.textEdit.setReadOnly(True)

        self.verticalLayout_2.addWidget(self.textEdit)


        self.verticalLayout.addWidget(self.groupBox_4)

        self.groupBox_6 = QGroupBox(self.groupBox_3)
        self.groupBox_6.setObjectName(u"groupBox_6")
        self.verticalLayout_6 = QVBoxLayout(self.groupBox_6)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.ikRefArray_horizontalLayout_5 = QHBoxLayout()
        self.ikRefArray_horizontalLayout_5.setObjectName(u"ikRefArray_horizontalLayout_5")
        self.label_2 = QLabel(self.groupBox_6)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setMinimumSize(QSize(40, 0))

        self.ikRefArray_horizontalLayout_5.addWidget(self.label_2)

        self.cheekLeft_lineEdit = QLineEdit(self.groupBox_6)
        self.cheekLeft_lineEdit.setObjectName(u"cheekLeft_lineEdit")

        self.ikRefArray_horizontalLayout_5.addWidget(self.cheekLeft_lineEdit)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setSpacing(3)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.cheekLeftAdd_pushButton = QPushButton(self.groupBox_6)
        self.cheekLeftAdd_pushButton.setObjectName(u"cheekLeftAdd_pushButton")
        self.cheekLeftAdd_pushButton.setMaximumSize(QSize(55, 16777215))

        self.horizontalLayout.addWidget(self.cheekLeftAdd_pushButton)

        self.cheekLeftRemove_pushButton = QPushButton(self.groupBox_6)
        self.cheekLeftRemove_pushButton.setObjectName(u"cheekLeftRemove_pushButton")
        self.cheekLeftRemove_pushButton.setMaximumSize(QSize(55, 16777215))

        self.horizontalLayout.addWidget(self.cheekLeftRemove_pushButton)


        self.ikRefArray_horizontalLayout_5.addLayout(self.horizontalLayout)


        self.verticalLayout_6.addLayout(self.ikRefArray_horizontalLayout_5)

        self.verticalLayout_7 = QVBoxLayout()
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.cheekRight_horizontalLayout_6 = QHBoxLayout()
        self.cheekRight_horizontalLayout_6.setObjectName(u"cheekRight_horizontalLayout_6")
        self.label_3 = QLabel(self.groupBox_6)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setMinimumSize(QSize(40, 0))

        self.cheekRight_horizontalLayout_6.addWidget(self.label_3)

        self.cheekRight_lineEdit = QLineEdit(self.groupBox_6)
        self.cheekRight_lineEdit.setObjectName(u"cheekRight_lineEdit")

        self.cheekRight_horizontalLayout_6.addWidget(self.cheekRight_lineEdit)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setSpacing(3)
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.cheekRightAdd_pushButton = QPushButton(self.groupBox_6)
        self.cheekRightAdd_pushButton.setObjectName(u"cheekRightAdd_pushButton")
        self.cheekRightAdd_pushButton.setMaximumSize(QSize(55, 16777215))

        self.horizontalLayout_5.addWidget(self.cheekRightAdd_pushButton)

        self.cheekRightRemove_pushButton = QPushButton(self.groupBox_6)
        self.cheekRightRemove_pushButton.setObjectName(u"cheekRightRemove_pushButton")
        self.cheekRightRemove_pushButton.setMaximumSize(QSize(55, 16777215))

        self.horizontalLayout_5.addWidget(self.cheekRightRemove_pushButton)


        self.cheekRight_horizontalLayout_6.addLayout(self.horizontalLayout_5)


        self.verticalLayout_7.addLayout(self.cheekRight_horizontalLayout_6)


        self.verticalLayout_6.addLayout(self.verticalLayout_7)


        self.verticalLayout.addWidget(self.groupBox_6)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.gridLayout.addWidget(self.groupBox_3, 1, 0, 1, 1)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.groupBox.setTitle(QCoreApplication.translate("Form", u"GroupBox", None))
        self.isSlidingSurface.setText(QCoreApplication.translate("Form", u"Sliding Surface", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("Form", u"Reference", None))
        self.groupBox_4.setTitle(QCoreApplication.translate("Form", u"Surface", None))
        self.surfaceReferenceAdd_pushButton.setText(QCoreApplication.translate("Form", u"<<", None))
        self.surfaceReferenceRemove_pushButton.setText(QCoreApplication.translate("Form", u">>", None))
#if QT_CONFIG(tooltip)
        self.textEdit.setToolTip("")
#endif // QT_CONFIG(tooltip)
        self.textEdit.setHtml(QCoreApplication.translate("Form", u"<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Segoe UI'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Reference to the &quot;surface&quot; of another component. When setting this value, please ensure that the component comes before this component in the order on the outliner.</p></body></html>", None))
        self.groupBox_6.setTitle(QCoreApplication.translate("Form", u"Cheek Connection", None))
        self.label_2.setText(QCoreApplication.translate("Form", u"Left: ", None))
        self.cheekLeft_lineEdit.setText(QCoreApplication.translate("Form", u"cheekCorner_L0_root", None))
        self.cheekLeftAdd_pushButton.setText(QCoreApplication.translate("Form", u"<<", None))
        self.cheekLeftRemove_pushButton.setText(QCoreApplication.translate("Form", u">>", None))
        self.label_3.setText(QCoreApplication.translate("Form", u"Right: ", None))
        self.cheekRight_lineEdit.setText(QCoreApplication.translate("Form", u"cheekCorner_R0_root", None))
        self.cheekRightAdd_pushButton.setText(QCoreApplication.translate("Form", u"<<", None))
        self.cheekRightRemove_pushButton.setText(QCoreApplication.translate("Form", u">>", None))
    # retranslateUi

