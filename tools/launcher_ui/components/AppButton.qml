import QtQuick
import QtQuick.Controls
import ".."

Button {
    id: ctrl
    property color bgColor: Theme.cPane
    property color bgHover: Theme.cField
    property color fgColor: Theme.cFg
    font.family: Theme.fFont
    font.pixelSize: 12
    font.bold: true
    padding: 10
    topPadding: 7
    bottomPadding: 7
    leftPadding: 16
    rightPadding: 16
    contentItem: Text {
        text: ctrl.text
        color: ctrl.enabled ? ctrl.fgColor : Theme.cMuted
        font: ctrl.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }
    background: Rectangle {
        radius: 4
        color: !ctrl.enabled ? Theme.cField
             : (ctrl.pressed || ctrl.hovered ? ctrl.bgHover : ctrl.bgColor)
    }
}