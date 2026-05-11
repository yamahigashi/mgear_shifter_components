"""Qt settings UI for ymt_feather_ribbon_01."""

import mgear.core.pyqt as gqt


QtGui, QtCore, QtWidgets, wrapInstance = gqt.qt_import()


class Ui_Form(object):
    def setupUi(self, Form: QtWidgets.QWidget) -> None:
        Form.setObjectName("Form")
        Form.resize(320, 360)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.groupBox = QtWidgets.QGroupBox(Form)
        self.groupBox.setTitle("")
        self.formLayout = QtWidgets.QFormLayout(self.groupBox)
        self.formLayout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)

        self.placementMode_label = QtWidgets.QLabel(self.groupBox)
        self.placementMode_comboBox = QtWidgets.QComboBox(self.groupBox)
        self.placementMode_comboBox.addItem("")
        self.placementMode_comboBox.addItem("")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.placementMode_label)
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.placementMode_comboBox)

        self.rowNames_label = QtWidgets.QLabel(self.groupBox)
        self.rowNames_lineEdit = QtWidgets.QLineEdit(self.groupBox)
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.rowNames_label)
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.rowNames_lineEdit)

        self.rowCounts_label = QtWidgets.QLabel(self.groupBox)
        self.rowCounts_lineEdit = QtWidgets.QLineEdit(self.groupBox)
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.rowCounts_label)
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.rowCounts_lineEdit)

        self.rowURanges_label = QtWidgets.QLabel(self.groupBox)
        self.rowURanges_lineEdit = QtWidgets.QLineEdit(self.groupBox)
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.rowURanges_label)
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.rowURanges_lineEdit)

        self.lowerEdgeOffsets_label = QtWidgets.QLabel(self.groupBox)
        self.lowerEdgeOffsets_plainTextEdit = QtWidgets.QPlainTextEdit(self.groupBox)
        self.lowerEdgeOffsets_plainTextEdit.setMinimumHeight(72)
        self.formLayout.setWidget(4, QtWidgets.QFormLayout.LabelRole, self.lowerEdgeOffsets_label)
        self.formLayout.setWidget(4, QtWidgets.QFormLayout.FieldRole, self.lowerEdgeOffsets_plainTextEdit)

        self.ctlSize_label = QtWidgets.QLabel(self.groupBox)
        self.ctlSize_doubleSpinBox = QtWidgets.QDoubleSpinBox(self.groupBox)
        self.ctlSize_doubleSpinBox.setMinimum(0.001)
        self.ctlSize_doubleSpinBox.setMaximum(100.0)
        self.ctlSize_doubleSpinBox.setSingleStep(0.1)
        self.formLayout.setWidget(5, QtWidgets.QFormLayout.LabelRole, self.ctlSize_label)
        self.formLayout.setWidget(5, QtWidgets.QFormLayout.FieldRole, self.ctlSize_doubleSpinBox)

        self.addJoints_checkBox = QtWidgets.QCheckBox(self.groupBox)
        self.formLayout.setWidget(6, QtWidgets.QFormLayout.FieldRole, self.addJoints_checkBox)

        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)
        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form: QtWidgets.QWidget) -> None:
        Form.setWindowTitle(gqt.fakeTranslate("Form", "Form", None, -1))
        self.placementMode_label.setText(gqt.fakeTranslate("Form", "Placement", None, -1))
        self.placementMode_comboBox.setItemText(0, gqt.fakeTranslate("Form", "Surface", None, -1))
        self.placementMode_comboBox.setItemText(1, gqt.fakeTranslate("Form", "Fixed", None, -1))
        self.rowNames_label.setText(gqt.fakeTranslate("Form", "Row Names", None, -1))
        self.rowCounts_label.setText(gqt.fakeTranslate("Form", "Row Counts", None, -1))
        self.rowURanges_label.setText(gqt.fakeTranslate("Form", "Row U Ranges", None, -1))
        self.lowerEdgeOffsets_label.setText(gqt.fakeTranslate("Form", "Lower Edge Offsets", None, -1))
        self.ctlSize_label.setText(gqt.fakeTranslate("Form", "Ctl Size", None, -1))
        self.addJoints_checkBox.setText(gqt.fakeTranslate("Form", "Add Joints", None, -1))
