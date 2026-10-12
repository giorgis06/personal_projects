from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from femstudio.core.mesh.quality import quality
from femstudio.core.project.document import Document
from femstudio.core.scene.validation import Finding, validate
from femstudio.physics import registry
from femstudio.ui.theme import tokens as t
from femstudio.ui.theme import zoom


def collect_findings(document: Document | None) -> list[Finding]:
    """The generic scene checks plus the problem type's own."""
    if document is None or document.scene is None:
        return []
    scene = document.scene
    findings = validate(scene)
    try:
        findings += registry.get(scene.problem_type).validate(scene)
    except KeyError as error:
        findings.append(Finding("error", "problem-type", "scene", str(error.args[0])))
    unexplained = document.mesh_error and not any(f.severity == "error" for f in findings)
    if unexplained:
        findings.append(
            Finding("error", "mesh", "scene", f"cannot be meshed: {document.mesh_error}")
        )
    return findings


def summarise(findings: list[Finding]) -> tuple[str, str]:
    """Text and level (ok, warning or error) for the validation summary."""
    errors = sum(f.severity == "error" for f in findings)
    warnings = len(findings) - errors
    text = f"Validation: {errors} error{'s' if errors != 1 else ''}, "
    text += f"{warnings} warning{'s' if warnings != 1 else ''}"
    return text, "error" if errors else "warning" if warnings else "ok"


class FindingsDialog(QDialog):
    """The list of findings, each with the name of what it is about."""

    def __init__(self, findings: list[Finding], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Validation")
        layout = QVBoxLayout(self)
        self._list = QListWidget()
        for finding in findings:
            self._list.addItem(f"{finding.severity}: {finding.subject}: {finding.message}")
        if not findings:
            self._list.addItem("No findings.")
        layout.addWidget(self._list)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.clicked.connect(self.accept)
        layout.addWidget(buttons)
        self.resize(zoom.px(t.DIALOG_WIDTH), zoom.px(t.DIALOG_HEIGHT))

    def lines(self) -> list[str]:
        return [self._list.item(i).text() for i in range(self._list.count())]


class StatusPanel(QStatusBar):
    """Validation summary, node and triangle counts, and the element size."""

    def __init__(self) -> None:
        super().__init__()
        self.setSizeGripEnabled(False)
        self._validation = QPushButton()
        self._validation.setObjectName("validation")
        self._validation.setFlat(True)
        self._validation.clicked.connect(self.show_findings)
        self._nodes = QLabel()
        self._triangles = QLabel()
        self._size = QLabel()
        for widget in (self._validation, self._nodes, self._triangles, self._size):
            self.addWidget(widget)
        self._zoom = QLabel()
        self.addPermanentWidget(self._zoom)
        self._findings: list[Finding] = []
        self.set_document(None)

    def set_document(self, document: Document | None) -> None:
        self._findings = collect_findings(document)
        text, level = summarise(self._findings)
        self._validation.setText(text)
        self._validation.setProperty("level", level)
        self._validation.style().unpolish(self._validation)
        self._validation.style().polish(self._validation)
        if document is None or document.mesh is None:
            self._nodes.setText("")
            self._triangles.setText("")
            self._size.setText("" if document is None else "not meshed")
            return
        stats = quality(document.mesh)
        self._nodes.setText(f"{stats.n_nodes:,} nodes".replace(",", " "))
        self._triangles.setText(f"{stats.n_triangles:,} triangles".replace(",", " "))
        size = document.size if document.size is not None else stats.max_edge
        self._size.setText(f"h = {size:.3g}")

    def set_zoom(self, factor: float) -> None:
        self._zoom.setText(f"Zoom {zoom.percent(factor)}")

    def zoom_text(self) -> str:
        return self._zoom.text()

    def findings(self) -> list[Finding]:
        return list(self._findings)

    def texts(self) -> list[str]:
        return [w.text() for w in (self._validation, self._nodes, self._triangles, self._size)]

    def show_findings(self) -> FindingsDialog:
        dialog = FindingsDialog(self._findings, self.window())
        dialog.open()
        return dialog
