import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import ".."

Rectangle {
    id: card
    implicitHeight: 64
    color: Theme.cPane
    radius: 8
    border.color: Theme.cBorder

    property string cardPhase: ""
    property string cardDetail: ""
    property color statusColor: Theme.cAccent
    property bool showBar: false
    property bool done: false
    property real progressValue: 0

    RowLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 12

        Rectangle {
            width: 3
            Layout.fillHeight: true
            radius: 1.5
            color: card.done ? Theme.cGreen : card.statusColor
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 2

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Text {
                    Layout.fillWidth: true
                    text: card.cardPhase
                    color: card.done ? Theme.cGreen : Theme.cFg
                    font.family: Theme.fFont
                    font.pixelSize: 12
                    font.bold: true
                    elide: Text.ElideRight
                }
                Text {
                    visible: card.showBar
                    text: card.done ? "100%" : Math.round(card.progressValue) + "%"
                    color: card.done ? Theme.cGreen : Theme.cMuted
                    font.family: Theme.fMono
                    font.pixelSize: 11
                }
            }

            Text {
                Layout.fillWidth: true
                visible: card.cardDetail !== ""
                text: card.cardDetail
                color: Theme.cMuted
                font.family: Theme.fFont
                font.pixelSize: 11
                elide: Text.ElideRight
            }

            ProgressBar {
                id: bar
                Layout.fillWidth: true
                Layout.preferredHeight: 4
                visible: card.showBar
                from: 0
                to: 100
                value: card.done ? 100 : card.progressValue
                background: Rectangle {
                    radius: 2
                    color: Theme.cBgDeep
                }
                contentItem: Rectangle {
                    radius: 2
                    anchors { top: parent.top; left: parent.left; bottom: parent.bottom }
                    width: (bar.visualPosition * parent.width)
                    color: card.done ? Theme.cGreen : Theme.cAccent
                }
            }
        }
    }
}