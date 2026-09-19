import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Rectangle {
    id: card
    height: 86
    color: Theme.cPane
    radius: 6
    border.color: Theme.cBorder

    property string cardPhase: ""
    property string cardDetail: ""
    property color statusColor: Theme.cMuted
    property bool showBar: false
    property bool done: false
    property real progressValue: 0

    Rectangle {
        width: 4
        anchors.left: parent.left
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        radius: 2
        color: card.statusColor
    }
    ColumnLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.leftMargin: 14
        anchors.rightMargin: 12
        anchors.topMargin: 8
        anchors.bottomMargin: 8
        spacing: 3
        Text {
            Layout.fillWidth: true
            id: phaseLabel
            text: card.cardPhase
            color: card.done ? Theme.cGreen : card.statusColor
            font.family: Theme.fFont
            font.pixelSize: 12
            font.bold: true
            elide: Text.ElideRight
        }
        Text {
            Layout.fillWidth: true
            text: card.cardDetail
            color: Theme.cMuted
            font.family: Theme.fFont
            font.pixelSize: 11
            wrapMode: Text.WordWrap
            maximumLineCount: 3
            elide: Text.ElideRight
            clip: true
        }
        RowLayout {
            Layout.fillWidth: true
            visible: card.showBar
            spacing: 10
            ProgressBar {
                id: bar
                Layout.fillWidth: true
                Layout.preferredHeight: 8
                from: 0
                to: 100
                value: card.done ? 100 : card.progressValue
                background: Rectangle {
                    radius: 4
                    color: Theme.cField
                }
                contentItem: Rectangle {
                    radius: 4
                    color: card.done ? Theme.cGreen : Theme.cAccent
                    anchors.verticalCenter: parent.verticalCenter
                    anchors.left: parent.left
                    anchors.leftMargin: 1
                    width: (bar.visualPosition * (parent.width - 2))
                    height: parent.height ? parent.height : 8
                }
            }
            Text {
                text: card.done ? "100%" : Math.round(card.progressValue) + "%"
                color: card.done ? Theme.cGreen : Theme.cMuted
                font.family: Theme.fMono
                font.pixelSize: 11
            }
        }
    }
}