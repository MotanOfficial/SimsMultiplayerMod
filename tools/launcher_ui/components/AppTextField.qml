import QtQuick
import QtQuick.Controls
import ".."

TextField {
    id: field
    color: Theme.cFg
    font.family: Theme.fFont
    font.pixelSize: 12
    padding: 8
    selectionColor: Theme.cAccent
    selectedTextColor: "#ffffff"
    placeholderTextColor: Theme.cMuted
    background: Rectangle {
        radius: 4
        color: Theme.cField
        border.color: field.activeFocus ? Theme.cAccent : Theme.cBorder
        border.width: 1
    }
}