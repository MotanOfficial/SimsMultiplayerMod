import QtQuick
import QtQuick.Controls
import ".."

TextField {
    id: field
    implicitHeight: 40
    color: Theme.cFgDark
    font.family: Theme.fFont
    font.pixelSize: 12
    padding: 12
    selectionColor: Theme.cAccent
    selectedTextColor: "#ffffff"
    placeholderTextColor: "#999999"
    background: Rectangle {
        radius: 6
        color: Theme.cField
        border.width: 1
        border.color: !field.enabled ? "#e0e0e0"
                     : (field.activeFocus ? Theme.cAccent : Theme.cFieldBorder)
    }
}