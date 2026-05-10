
################################################################################
## Form generated from reading UI file 'settingsUI.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from Qt.QtCore import *
from Qt.QtGui import *
from Qt.QtWidgets import *


class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName("Form")
        Form.resize(419, 555)
        self.verticalLayout = QVBoxLayout(Form)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox_3 = QGroupBox(Form)
        self.groupBox_3.setObjectName("groupBox_3")
        self.gridLayout_4 = QGridLayout(self.groupBox_3)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.gridLayout_4.setSizeConstraint(QLayout.SetDefaultConstraint)
        self.isSlidingSurface = QCheckBox(self.groupBox_3)
        self.isSlidingSurface.setObjectName("isSlidingSurface")
        self.isSlidingSurface.setChecked(True)
        self.isSlidingSurface.setTristate(False)

        self.gridLayout_4.addWidget(self.isSlidingSurface, 0, 0, 1, 1)

        self.ikRefArray_groupBox = QGroupBox(self.groupBox_3)
        self.ikRefArray_groupBox.setObjectName("ikRefArray_groupBox")
        self.ikRefArray_groupBox.setEnabled(True)
        self.ikRefArray_groupBox.setMaximumSize(QSize(16777215, 166))
        self.ikRefArray_groupBox.setFlat(False)
        self.gridLayout_7 = QGridLayout(self.ikRefArray_groupBox)
        self.gridLayout_7.setObjectName("gridLayout_7")
        self.gridLayout_7.setSizeConstraint(QLayout.SetMaximumSize)
        self.ikRefArray_horizontalLayout_4 = QHBoxLayout()
        self.ikRefArray_horizontalLayout_4.setObjectName("ikRefArray_horizontalLayout_4")
        self.ikRefArray_verticalLayout_7 = QVBoxLayout()
        self.ikRefArray_verticalLayout_7.setObjectName("ikRefArray_verticalLayout_7")
        self.surfaceReference_listWidget = QListWidget(self.ikRefArray_groupBox)
        self.surfaceReference_listWidget.setObjectName("surfaceReference_listWidget")
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
        self.ikRefArray_verticalLayout_8.setObjectName("ikRefArray_verticalLayout_8")
        self.surfaceReferenceAdd_pushButton = QPushButton(self.ikRefArray_groupBox)
        self.surfaceReferenceAdd_pushButton.setObjectName("surfaceReferenceAdd_pushButton")

        self.ikRefArray_verticalLayout_8.addWidget(self.surfaceReferenceAdd_pushButton)

        self.surfaceReferenceRemove_pushButton = QPushButton(self.ikRefArray_groupBox)
        self.surfaceReferenceRemove_pushButton.setObjectName("surfaceReferenceRemove_pushButton")

        self.ikRefArray_verticalLayout_8.addWidget(self.surfaceReferenceRemove_pushButton)

        self.ikRefArray_verticalSpacer_4 = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.ikRefArray_verticalLayout_8.addItem(self.ikRefArray_verticalSpacer_4)


        self.ikRefArray_horizontalLayout_4.addLayout(self.ikRefArray_verticalLayout_8)


        self.gridLayout_7.addLayout(self.ikRefArray_horizontalLayout_4, 1, 0, 1, 1)

        self.textEdit = QTextEdit(self.ikRefArray_groupBox)
        self.textEdit.setObjectName("textEdit")
        self.textEdit.setMaximumSize(QSize(16777215, 66))
        self.textEdit.setFocusPolicy(Qt.NoFocus)
        self.textEdit.setContextMenuPolicy(Qt.NoContextMenu)
        self.textEdit.setAcceptDrops(False)
        self.textEdit.setReadOnly(True)

        self.gridLayout_7.addWidget(self.textEdit, 2, 0, 1, 1)


        self.gridLayout_4.addWidget(self.ikRefArray_groupBox, 1, 0, 1, 1)


        self.verticalLayout.addWidget(self.groupBox_3)

        self.groupBox = QGroupBox(Form)
        self.groupBox.setObjectName("groupBox")
        self.horizontalLayout_2 = QHBoxLayout(self.groupBox)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.overrideNegate_checkBox = QCheckBox(self.groupBox)
        self.overrideNegate_checkBox.setObjectName("overrideNegate_checkBox")
        self.overrideNegate_checkBox.setText("Override Negate Axis Direction For \"R\" Side")

        self.verticalLayout_3.addWidget(self.overrideNegate_checkBox)

        self.addJoints_checkBox = QCheckBox(self.groupBox)
        self.addJoints_checkBox.setObjectName("addJoints_checkBox")
        self.addJoints_checkBox.setText("Add Joints")
        self.addJoints_checkBox.setChecked(True)

        self.verticalLayout_3.addWidget(self.addJoints_checkBox)


        self.horizontalLayout_2.addLayout(self.verticalLayout_3)


        self.verticalLayout.addWidget(self.groupBox)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.retranslateUi(Form)

        self.surfaceReference_listWidget.setCurrentRow(-1)


        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", "Form", None))
        self.groupBox_3.setTitle(QCoreApplication.translate("Form", "Surface", None))
        self.isSlidingSurface.setText(QCoreApplication.translate("Form", "Sliding on Surface", None))
        self.ikRefArray_groupBox.setTitle("")
        self.surfaceReferenceAdd_pushButton.setText(QCoreApplication.translate("Form", "<<", None))
        self.surfaceReferenceRemove_pushButton.setText(QCoreApplication.translate("Form", ">>", None))
        self.textEdit.setHtml(QCoreApplication.translate("Form", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><meta charset=\"utf-8\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"hr { height: 1px; border-width: 0; }\n"
"li.unchecked::marker { content: \"\\2610\"; }\n"
"li.checked::marker { content: \"\\2612\"; }\n"
"</style></head><body style=\" font-family:'Segoe UI'; font-size:9pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Reference to the &quot;sliding_surface&quot; of other components.</p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">When setting this value, please ensure that the component comes before this component in the order on the outliner.</p></body></html>", None))
        self.groupBox.setTitle(QCoreApplication.translate("Form", "GroupBox", None))
    # retranslateUi

