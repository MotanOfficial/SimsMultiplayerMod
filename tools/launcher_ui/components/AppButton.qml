import QtQuick
import QtQuick.Controls
import ".."

Button {
    id: ctrl
    property bool ghost: ctrl.bgColor.a === 0
    property color bgColor: "transparent"
    property color bgHover: "transparent"
    property color fgColor: Theme.cAccent
    font.family: Theme.fFont
    font.pixelSize: 12
    font.bold: true
    implicitHeight: 40
    padding: 10
    leftPadding: 18
    rightPadding: 18

    contentItem: Text {
        text: ctrl.text
        color: !ctrl.enabled ? Theme.cMuted
             : (ctrl.ghost ? ctrl.fgColor : "#ffffff")
        font: ctrl.font
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        radius: 6
        color: ctrl.ghost ? "transparent"
             : (ctrl.hovered ? Qt.darker(ctrl.bgColor, 1.08) : ctrl.bgColor)
        border.width: ctrl.ghost ? 1 : 0
        border.color: !ctrl.enabled ? Theme.cBorder
                     : (ctrl.ghost && ctrl.hovered ? Theme.cAccent : Theme.cBorderSoft)
    }

    scale: ctrl.pressed ? 0.97 : 1.0
    Behavior on scale { NumberAnimation { duration: 90 } }
}