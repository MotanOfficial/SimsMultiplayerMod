import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

RowLayout {
    id: sh
    property string label: ""
    property bool fill: true
    Layout.fillWidth: fill
    Text {
        text: sh.label.toUpperCase()
        color: Theme.cMuted
        font.family: Theme.fFont
        font.pixelSize: 10
        font.bold: true
        font.letterSpacing: 1.2
    }
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 1
        Layout.topMargin: 5
        Layout.bottomMargin: 5
        color: Theme.cBorder
    }
}