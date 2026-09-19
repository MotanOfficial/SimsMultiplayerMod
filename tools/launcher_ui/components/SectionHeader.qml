import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

ColumnLayout {
    id: sh
    property string label: ""
    property bool fill: true
    Layout.fillWidth: fill
    spacing: 0

    Text {
        text: sh.label
        color: Theme.cFg
        font.family: Theme.fFont
        font.pixelSize: 13
        font.bold: true
        font.letterSpacing: 0.8
    }
}