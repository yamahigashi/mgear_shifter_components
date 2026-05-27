"""Qt settings UI for ymt_birdtail_01."""

import mgear.core.pyqt as gqt


QtGui, QtCore, QtWidgets, wrapInstance = gqt.qt_import()


class Ui_Form:
    def setupUi(self, Form: QtWidgets.QWidget) -> None:
        Form.setObjectName("Form")
        Form.resize(520, 560)
        self.gridLayout = QtWidgets.QGridLayout(Form)
        self.groupBox = QtWidgets.QGroupBox(Form)
        self.groupBox.setTitle("")
        self.mainLayout = QtWidgets.QVBoxLayout(self.groupBox)
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)

        self.solverMode_label = QtWidgets.QLabel(self.groupBox)
        self.solverMode_comboBox = QtWidgets.QComboBox(self.groupBox)
        self.solverMode_comboBox.addItem("")
        self.solverMode_comboBox.addItem("")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.solverMode_label)
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.solverMode_comboBox)

        self.ctlSize_label = QtWidgets.QLabel(self.groupBox)
        self.ctlSize_doubleSpinBox = QtWidgets.QDoubleSpinBox(self.groupBox)
        self.ctlSize_doubleSpinBox.setMinimum(0.001)
        self.ctlSize_doubleSpinBox.setMaximum(100.0)
        self.ctlSize_doubleSpinBox.setSingleStep(0.1)
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.ctlSize_label)
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.ctlSize_doubleSpinBox)

        self.surfaceCurlMaxWeight_label = QtWidgets.QLabel(self.groupBox)
        self.surfaceCurlMaxWeight_doubleSpinBox = QtWidgets.QDoubleSpinBox(self.groupBox)
        self.surfaceCurlMaxWeight_doubleSpinBox.setMinimum(0.0)
        self.surfaceCurlMaxWeight_doubleSpinBox.setMaximum(1.0)
        self.surfaceCurlMaxWeight_doubleSpinBox.setSingleStep(0.05)
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.LabelRole, self.surfaceCurlMaxWeight_label)
        self.formLayout.setWidget(2, QtWidgets.QFormLayout.FieldRole, self.surfaceCurlMaxWeight_doubleSpinBox)

        self.surfaceCurlEdgeScale_label = QtWidgets.QLabel(self.groupBox)
        self.surfaceCurlEdgeScale_doubleSpinBox = QtWidgets.QDoubleSpinBox(self.groupBox)
        self.surfaceCurlEdgeScale_doubleSpinBox.setMinimum(0.0)
        self.surfaceCurlEdgeScale_doubleSpinBox.setMaximum(1.0)
        self.surfaceCurlEdgeScale_doubleSpinBox.setSingleStep(0.05)
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.surfaceCurlEdgeScale_label)
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.FieldRole, self.surfaceCurlEdgeScale_doubleSpinBox)

        self.detailCurlRotMults_label = QtWidgets.QLabel(self.groupBox)
        self.detailCurlRotMults_lineEdit = QtWidgets.QLineEdit(self.groupBox)
        self.formLayout.setWidget(4, QtWidgets.QFormLayout.LabelRole, self.detailCurlRotMults_label)
        self.formLayout.setWidget(4, QtWidgets.QFormLayout.FieldRole, self.detailCurlRotMults_lineEdit)

        self.addJoints_checkBox = QtWidgets.QCheckBox(self.groupBox)
        self.formLayout.setWidget(5, QtWidgets.QFormLayout.FieldRole, self.addJoints_checkBox)

        self.group_groupBox = QtWidgets.QGroupBox(self.groupBox)
        self.groupLayout = QtWidgets.QVBoxLayout(self.group_groupBox)
        self.groupTableWidget = QtWidgets.QTableWidget(self.group_groupBox)
        self.groupTableWidget.setColumnCount(8)
        self.groupTableWidget.setHorizontalHeaderLabels(
            ["Group", "Rows", "Column Depths", "Length", "Width", "Stack Y", "Main Influence", "Curl Influence"]
        )
        self.groupTableWidget.verticalHeader().setVisible(False)
        self.groupTableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.groupTableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.groupTableWidget.setMinimumHeight(220)
        self.groupTableWidget.horizontalHeader().setStretchLastSection(True)
        self.groupLayout.addWidget(self.groupTableWidget)

        self.groupButtonLayout = QtWidgets.QHBoxLayout()
        self.addGroup_pushButton = QtWidgets.QPushButton(self.group_groupBox)
        self.removeGroup_pushButton = QtWidgets.QPushButton(self.group_groupBox)
        self.generateLocators_pushButton = QtWidgets.QPushButton(self.group_groupBox)
        self.groupButtonLayout.addWidget(self.addGroup_pushButton)
        self.groupButtonLayout.addWidget(self.removeGroup_pushButton)
        self.groupButtonLayout.addStretch()
        self.groupButtonLayout.addWidget(self.generateLocators_pushButton)
        self.groupLayout.addLayout(self.groupButtonLayout)

        self.mainLayout.addLayout(self.formLayout)
        self.mainLayout.addWidget(self.group_groupBox)
        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form: QtWidgets.QWidget) -> None:
        Form.setWindowTitle(gqt.fakeTranslate("Form", "Form", None, -1))
        self.solverMode_label.setText(gqt.fakeTranslate("Form", "Solver", None, -1))
        self.solverMode_comboBox.setItemText(
            0,
            gqt.fakeTranslate("Form", "Simple Matrix Connection", None, -1),
        )
        self.solverMode_comboBox.setItemText(
            1,
            gqt.fakeTranslate("Form", "NURBS Ribbon with Curl", None, -1),
        )
        self.ctlSize_label.setText(gqt.fakeTranslate("Form", "Ctl Size", None, -1))
        self.surfaceCurlMaxWeight_label.setText(gqt.fakeTranslate("Form", "Surface Curl Max", None, -1))
        self.surfaceCurlEdgeScale_label.setText(gqt.fakeTranslate("Form", "Surface Curl Edge", None, -1))
        self.detailCurlRotMults_label.setText(gqt.fakeTranslate("Form", "Detail Curl Rot Mults", None, -1))
        self.addJoints_checkBox.setText(gqt.fakeTranslate("Form", "Add Joints", None, -1))
        self.group_groupBox.setTitle(gqt.fakeTranslate("Form", "Feather Groups", None, -1))
        self.addGroup_pushButton.setText(gqt.fakeTranslate("Form", "Add Group", None, -1))
        self.removeGroup_pushButton.setText(gqt.fakeTranslate("Form", "Remove Group", None, -1))
        self.generateLocators_pushButton.setText(gqt.fakeTranslate("Form", "Rebuild Detail Locators", None, -1))
